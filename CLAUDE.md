# CLAUDE.md — Guia arquitetural do Mentor de Carreira

Este arquivo descreve a arquitetura interna, fluxo de dados, convenções de código e
instruções para extensão do sistema. Destina-se ao desenvolvedor (humano ou IA) que
precisa entender ou modificar o projeto.

> Para **instalar e rodar**, veja [`docs/INSTALACAO.md`](docs/INSTALACAO.md).
> Para **diagramas** (casos de uso, sequência, ER do banco, arquitetura), veja
> [`diagramas/`](diagramas/).
> Para o **módulo de IA** em detalhe (técnicas, fluxo e robustez), veja
> [`docs/MODULO_IA.md`](docs/MODULO_IA.md).

---

## Visão geral

```
HTTP Request
    │
    ▼
FastAPI Router  (app/routes/*.py)
    │  valida entrada (Pydantic / Form)
    │  resolve DB session via Depends(get_db)
    ▼
Service Layer  (app/services/*.py)
    │  lógica de negócio
    │  chama claude_client se necessário
    ▼
Claude Client  (app/services/claude_client.py)
    │  singleton Anthropic
    │  retry automático (tenacity)
    │  tool_use forçado para saídas estruturadas
    ▼
Anthropic API  (modelo configurável via CLAUDE_MODEL; padrão: claude-haiku-4-5)

Service Layer
    │  lê/escreve via SQLAlchemy ORM
    ▼
SQLite (mentor.db)
```

O frontend HTML (routers `*_web.py` em `app/routes/` + `app/templates/`) é uma camada
fina sobre os mesmos serviços usados pelos endpoints JSON. Não há lógica duplicada entre
os dois.

---

## Estrutura de pastas

```
app/
├── main.py              # Entrada da aplicação (inclui SessionMiddleware)
├── config.py            # Settings (pydantic-settings, lê .env)
├── database.py          # Engine + get_db()
├── models.py            # ORM: 7 tabelas (Student tem password_hash)
├── schemas.py           # Pydantic: contratos de entrada/saída
├── data/
│   ├── recursos_aprendizado.py # Corpus do RAG: recursos por competência (~115 chaves)
│   └── sinonimos.py           # Sinônimos/variantes de competências (ex.: JS↔JavaScript)
├── prompts/             # Prompts de sistema + ferramentas (tool use), sem lógica de API
│   ├── triagem.py       # PROMPT_SISTEMA_TRIAGEM + montar_prompt_triagem()
│   ├── perfil.py        # PROMPT_GERAR_PERFIL + FERRAMENTA_PERFIL
│   ├── pdi.py           # PROMPT_GERAR_PDI + FERRAMENTA_PDI
│   ├── curriculo.py     # PROMPT_GERAR_CURRICULO (+ bloco condicional de vaga-alvo)
│   ├── analise_vaga.py  # PROMPT_EXTRAIR_VAGA + FERRAMENTA_EXTRAIR_VAGA
│   ├── recomendacoes_vaga.py # PROMPT/FERRAMENTA_RECOMENDACOES_VAGA (competitividade)
│   └── analise_curriculo.py  # PROMPT/FERRAMENTA_ANALISE_CURRICULO (dicas de melhoria)
├── routes/
│   ├── _deps.py         # Guards de autenticação/autorização (ver seção dedicada)
│   ├── _web.py          # Infra compartilhada das páginas HTML (templates + helpers de form)
│   ├── auth.py          # POST /auth/login, /auth/logout, GET /auth/me
│   ├── students.py
│   ├── triage.py
│   ├── pdi.py
│   ├── curriculum.py
│   ├── admin.py         # Painel /admin (HTML, restrito a administradores)
│   ├── paginas_web.py   # HTML: login/logout/cadastro/painel/triagem (include_in_schema=False)
│   ├── perfil_web.py    # HTML: perfil (visualização + edição)
│   ├── pdi_web.py       # HTML: PDI (visualização, geração, edição, quadro Kanban)
│   ├── curriculo_web.py # HTML: currículo (visualização, geração, edição)
│   ├── curriculo_vaga_web.py # HTML: currículos por vaga (análise + currículo direcionado)
│   └── analise_vaga_web.py   # Redirects da antiga Análise de Vaga → currículos por vaga
└── services/
    ├── _base.py         # Helper upsert_registro() genérico
    ├── claude_client.py # Único ponto de contato com a API Anthropic (só lógica de cliente)
    ├── competencias.py  # Matching de competências (substring + sinônimos): usado pela análise de vaga e RAG
    ├── rag_service.py   # Naive RAG: recupera recursos do corpus para as lacunas (ranking por relevância)
    ├── auth_service.py  # Hash/verificação de senha (bcrypt) e autenticação
    ├── admin_service.py # Métricas, diagnóstico e gestão de alunos (painel admin)
    ├── student_service.py
    ├── profile_service.py
    ├── contexto_aluno.py # ContextoAluno (nome/e-mail/curso/período) + calcular_nivel_experiencia()
    ├── pdi_service.py
    ├── curriculum_service.py  # + montar_contexto_curriculo() (compartilhado com o fluxo por vaga)
    ├── analise_vaga_service.py # Motor da análise: extrai requisitos (IA) + matching + score + RAG
    ├── curriculum_vaga_service.py # Orquestra análise → recomendações → currículo por vaga (CRUD N:1)
    ├── curriculo_qualidade.py # Checklist determinístico do currículo (sem IA): pontuação 0-100
    └── curriculum_analise_service.py # Diagnóstico + dicas da IA + detecção de análise defasada
```

Templates do painel ficam em `app/templates/admin/` (dashboard, alunos, aluno_detalhe,
sistema + `_subnav.html` compartilhado).

---

## Modelos de dados

### Tabelas

| Tabela | Chave | Descrição |
|--------|-------|-----------|
| `students` | `id` PK | Aluno cadastrado |
| `triage_messages` | `id` PK, `student_id` FK | Mensagens do chat de triagem |
| `student_profiles` | `id` PK, `student_id` FK UNIQUE | Perfil JSON gerado ao final da triagem |
| `pdis` | `id` PK, `student_id` FK UNIQUE | PDI JSON gerado pelo Claude |
| `curriculums` | `id` PK, `student_id` FK UNIQUE | Currículo texto (ATS) |
| `curriculum_vagas` | `id` PK, `student_id` FK (N por aluno) | Currículo direcionado por vaga: JD original, análise JSON (+recomendações) e texto |
| `curriculum_analises` | `id` PK, `student_id` FK UNIQUE | Dicas de melhoria do currículo base geradas pela IA + `texto_hash` do currículo analisado |

`StudentProfile`, `PDI` e `Curriculum` têm constraint UNIQUE em `student_id` —
cada aluno tem no máximo um de cada. A função `upsert_registro()` em `_base.py`
implementa create-or-update para essas entidades. **`CurriculumVaga` é a exceção**:
N registros por aluno (sem UNIQUE), gerenciados por CRUD plano em
`curriculum_vaga_service` (não usar `upsert_registro`, que assume `student_id` único).

`Student` também armazena `password_hash` (bcrypt, via `passlib`) — cada aluno é
também uma conta de login (e-mail + senha) — e `is_admin` (acesso ao painel `/admin`).

#### Quadro Kanban dentro do `pdi_json`

Além dos campos gerados pela IA (`objetivo_geral`, `metas_*`, `competencias_a_desenvolver`,
`acoes_recomendadas`, `cronograma`), o `pdi_json` carrega uma chave **`quadro_kanban`**: uma
lista de cards `{id, texto, coluna, categoria}` com `coluna ∈ {a_fazer, em_progresso,
concluido}`. Por ser uma coluna JSON, isso **não exige migração de schema**. O quadro é
**materializado na camada de serviço** (`pdi_service._montar_quadro`) a partir das
`acoes_recomendadas` logo após a geração — o schema da ferramenta do Claude não muda.
`pdi_service.garantir_quadro` faz backfill em PDIs antigos (gerados antes do quadro existir)
na primeira visita à página.

#### Campos adicionais em `profile_json` (formação, certificações, links, resultados)

Seguindo o mesmo padrão aditivo do quadro Kanban, `profile_json` ganhou 4 chaves novas sem
exigir migração de schema:

- **`formacao`**: objeto `{instituicao, previsao_conclusao, destaques_academicos}` —
  formação acadêmica complementar (instituição de ensino, previsão de conclusão, destaques
  acadêmicos). `Student.curso`/`periodo` continuam vindo direto do `Student`, não
  duplicados aqui.
- **`certificacoes`**: lista de `{nome, instituicao, ano}`.
- **`links`**: objeto `{github, linkedin, portfolio, outro}`.
- **`experiencias[].resultados`**: string livre com resultado/impacto quantificável de
  cada experiência (ex.: "usado por ~10 colegas, reduziu o tempo de cadastro em 30%").

Todas são `required` em `FERRAMENTA_PERFIL` (tool use forçado garante que o Claude sempre
preencha, usando `""`/`[]` quando não houver informação). Para perfis gerados **antes**
dessas chaves existirem, `profile_service._aplicar_defaults_perfil` faz backfill — em
memória, sem `db.commit()` — dentro de `obter_perfil`, mesmo espírito de
`pdi_service.garantir_quadro` mas sem persistir.

#### Áreas de afinidade em `profile_json`

`profile_json["areas_afinidade"]` é uma quinta chave aditiva, seguindo o mesmo padrão:

```json
[{"area": "Ciência de Dados", "porque": "Você citou Python e pandas em análise."}]
```

- **Gerada pela IA**: diferente do antigo campo de trilha (removido), `areas_afinidade` é
  um campo `required` de `FERRAMENTA_PERFIL` — a IA lê **toda a triagem** e sugere de 2 a 4
  áreas que combinam com o aluno, cada uma com um `porque`. Isso substitui o antigo
  recomendador determinístico por substring (que errava, ex.: "dados/IA" → "full-stack") por
  um julgamento que enxerga o contexto inteiro.
- **Tom**: possibilidades a explorar, não um veredito. Exibidas no perfil ("Áreas que
  combinam com seu perfil") e no dashboard (chips).
- **Backfill**: incluída em `_DEFAULTS_PERFIL_V2` → `_aplicar_defaults_perfil` garante
  `[]` em perfis antigos. `salvar_perfil_web` **preserva** as áreas ao editar o perfil (não
  são editadas no formulário, como `disciplinas_relevantes`).
- **Impacto nos artefatos**: o `profile_json` completo (com `areas_afinidade` e a stack) é
  passado para `pdi_service.gerar_pdi` e `curriculum_service.gerar_curriculo`, orientando o
  Claude a direcionar PDI e currículo às áreas de afinidade e à stack real do aluno — sem
  trilha, radar ou RAG-por-lacuna. O RAG (`rag_service` + corpus) permanece, usado apenas
  pela **Análise de Vaga**.

> **Sobre a remoção das trilhas**: o catálogo de 24 trilhas, o recomendador determinístico e
> o Radar de Competências foram removidos (erravam com frequência). `competencias.py`,
> `rag_service.py`, `recursos_aprendizado.py` e `sinonimos.py` **permanecem** — são usados
> pela Análise de Vaga, que não depende de trilhas.

### Edição dos artefatos (Perfil, PDI, Currículo)

Os três artefatos gerados pela IA são **editáveis pelo aluno**, com persistência no banco
(sobrescreve via `upsert_registro`):

- **Perfil** e **PDI**: páginas de formulário próprias (`/alunos/{id}/perfil/editar`,
  `/alunos/{id}/pdi/editar`) que reconstroem o JSON completo a partir do form e validam com
  os schemas `PerfilUpdate`/`PDIUpdate` antes de salvar (`profile_service.atualizar_perfil`,
  `pdi_service.atualizar_pdi`). Listas repetíveis (experiências, disciplinas, competências,
  blocos do cronograma) usam arrays paralelos no form + `app/static/editor.js`.
- **Quadro Kanban**: editado no próprio quadro; cada mover/adicionar/editar/excluir card faz
  `fetch POST /alunos/{id}/pdi/quadro` (JSON validado por `QuadroUpdate` →
  `pdi_service.atualizar_quadro`). Lógica em `app/static/kanban.js` (drag-and-drop HTML5 +
  botões de seta, com o DOM como fonte da verdade).
- **Currículo**: edição inline (textarea) em `/alunos/{id}/curriculo`, salva em
  `POST /alunos/{id}/curriculo/editar` (`curriculum_service.atualizar_curriculo`).

### Tutorial guiado (onboarding — IHC)

Na primeira visita a cada página, um *tour* guiado destaca os elementos e explica o que
fazer. Implementado em [`app/static/tutorial.js`](app/static/tutorial.js) (vanilla, sem
dependência) — **não há estado no servidor nem no banco**.

- **Ligar numa página**: definir o bloco `{% block tut_pagina %}painel{% endblock %}` no
  template (vira `data-tut-pagina` no `<main>`, em `base.html`). Sem esse bloco, nada é
  injetado na página.
- **Declarar um passo**: em qualquer elemento, `data-tut="1"` (ordem) +
  `data-tut-titulo="…"` + `data-tut-texto="…"`. Passos invisíveis (blocos `{% if %}` não
  renderizados) são ignorados automaticamente — por isso a mesma página funciona com o PDI
  gerado ou não.
- **Estado** (`localStorage`, por aluno — `data-aluno-id` no `<body>`):
  `tut:<aluno>:<pagina>` marca a página como apresentada; `tut:<aluno>:desativado` desliga
  o tutorial em todo o app. O botão flutuante **"?"** reexibe o tour da página (e reativa,
  se estiver desligado). Falhas de `localStorage` (modo privado) degradam sem quebrar.
- **Controles**: `Próximo`/`Concluir`, `Pular` (encerra só esta página), `Não mostrar mais`
  (global), `Esc` (encerra), `←`/`→` (navega).

### Relacionamentos

```
Student ──< TriageMessage   (1:N)
Student ──  StudentProfile  (1:0..1)
Student ──  PDI             (1:0..1)
Student ──  Curriculum      (1:0..1)
Student ──< CurriculumVaga  (1:N)  — currículos direcionados por vaga
Student ──  CurriculumAnalise (1:0..1) — dicas de melhoria do currículo base
```

### Diagnóstico de qualidade do currículo

A aba de currículo mostra uma avaliação do currículo base em duas camadas, seguindo a
mesma divisão IA × determinístico usada na análise de vaga:

- **Determinístico** (`app/services/curriculo_qualidade.py`): função pura `diagnosticar()`
  confere o texto contra o contrato imposto por `PROMPT_GERAR_CURRICULO` — 7 seções na
  ordem certa, cabeçalho com e-mail/links, bullets com verbo de ação no passado,
  quantificação de resultados, ausência de Markdown (ATS), tamanho e densidade de
  palavras-chave da stack do perfil. Retorna `{pontuacao 0-100, itens[], contagens}` com pesos
  explícitos. **Sem IA e sem banco** → recalculado a cada visita, refletindo edições
  manuais na hora. A detecção de seções é tolerante a markdown/acentuação para diagnosticar
  bem currículos editados à mão.
- **Qualitativo** (`claude_client.analisar_curriculo`, 7ª operação): recebe o texto, o
  perfil e **o diagnóstico já calculado** (só os itens problemáticos), evitando gastar
  tokens redetectando o que o código mediu. Devolve resumo, pontos fortes, melhorias
  priorizadas (cada uma com `exemplo_reescrito` — um trecho real do aluno melhorado) e
  seções a reforçar. Persistido em `curriculum_analises` porque custa uma chamada.

`texto_hash` (SHA-256 do currículo analisado) permite a
`curriculum_analise_service.esta_desatualizada` avisar na interface quando o aluno editou o
currículo depois da análise — em vez de exibir dicas obsoletas silenciosamente.

---

## Autenticação e autorização

O sistema usa **login por aluno**: cada `Student` é também uma conta (e-mail + senha
com hash bcrypt) e só enxerga os próprios dados (triagem, perfil, PDI, currículo).

### Sessão via cookie assinado

`app/main.py` registra `SessionMiddleware` (Starlette + `itsdangerous`), configurado
com `secret_key` e `session_max_age` de `app/config.py` (`SECRET_KEY`,
`SESSION_MAX_AGE`). O cookie de sessão guarda apenas `{"student_id": <id>}` e é
enviado automaticamente pelo navegador (e pelo `TestClient`) em toda requisição
subsequente.

- `POST /students` (cadastro) e `POST /alunos/novo` (HTML) já chamam
  `request.session["student_id"] = aluno.id` — o aluno fica logado imediatamente
  após criar a conta.
- `POST /auth/login` / `POST /login` autenticam via `auth_service.autenticar_aluno`
  e setam a mesma chave de sessão.
- `POST /auth/logout` / `POST /logout` chamam `request.session.clear()`.

O cookie usa `same_site="lax"` e `https_only=SESSION_HTTPS_ONLY` (ativado por padrão quando
`APP_ENV=production`). Em produção, `app/config.py` também recusa subir com a `SECRET_KEY`
padrão. E-mails são normalizados (`student_service.normalizar_email`), tornando o login
case-insensitive. Um middleware em `main.py` adiciona cabeçalhos de segurança básicos
(`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).

### Guards em `app/routes/_deps.py`

| Função | Uso | Comportamento sem sessão | Comportamento se for outro aluno |
|--------|-----|---------------------------|-----------------------------------|
| `obter_aluno_logado` | rotas JSON | `401` | — |
| `obter_aluno_logado_html` | rotas HTML | levanta `RedirectParaLogin` (→ 303 `/login`) | — |
| `verificar_proprio_aluno` | rotas JSON com `{student_id}` | `401` | `403` |
| `verificar_proprio_aluno_html` | rotas HTML com `{student_id}` | redireciona para `/login` | `403` |
| `verificar_admin_html` | rotas `/admin/*` | redireciona para `/login` | `403` se não for admin |

**Papel de administrador**: `eh_admin(aluno)` retorna True se `Student.is_admin` estiver
ativo no banco **ou** se o e-mail estiver em `ADMIN_EMAILS` (config) — este último serve
de bootstrap do primeiro admin. No login/cadastro a sessão guarda também
`is_admin` (apenas para exibir o link "Admin" na nav; o guard sempre revalida no banco).
Admins promovem/rebaixam outros alunos pela própria interface (`admin_service.definir_admin`).

`RedirectParaLogin` é tratada por um `@app.exception_handler` em `main.py` que
converte a exceção em `RedirectResponse("/login", status_code=303)`. Um `id`
inexistente nunca retorna `404` nessas rotas — ele cai no mesmo `403` de "não é seu",
para não revelar quais ids existem (evita enumeração).

Use `verificar_proprio_aluno`/`verificar_proprio_aluno_html` como `Depends(...)` no
parâmetro da função (`_aluno: Student = Depends(verificar_proprio_aluno)` se o objeto
não for usado, ou `aluno: Student = Depends(...)` se for usado no template/lógica).

### auth_service.py

```python
def gerar_hash_senha(senha: str) -> str: ...          # bcrypt hash
def verificar_senha(senha: str, password_hash: str) -> bool: ...
def autenticar_aluno(db, email: str, senha: str) -> Student | None: ...
```

---

## Claude client — decisões de design

> Os textos de prompt e os schemas de ferramenta (`PROMPT_*`, `FERRAMENTA_*`,
> `montar_prompt_triagem`) vivem em `app/prompts/` (um módulo por operação). O
> `claude_client.py` os importa e os **reexporta** (retrocompatibilidade: referências como
> `claude_client.PROMPT_GERAR_PDI` seguem válidas), ficando responsável apenas pela lógica
> de cliente: singleton, retry, construção da requisição e leitura da resposta.

### Saídas estruturadas via tool use

Para `gerar_perfil_estruturado` e `gerar_pdi`, o sistema força o Claude a responder
chamando uma ferramenta específica (`tool_choice={"type": "tool", "name": ...}`). Isso
garante que a resposta seja JSON válido com o schema pré-definido.

```python
resposta = _cliente().messages.create(
    ...
    tools=[FERRAMENTA_PDI],
    tool_choice={"type": "tool", "name": "salvar_pdi"},
)
# O bloco tool_use SEMPRE estará presente (erro de API se não vier)
for bloco in resposta.content:
    if bloco.type == "tool_use":
        return bloco.input
raise RuntimeError("Claude não retornou o bloco 'tool_use' esperado...")
```

Para `gerar_curriculo`, a saída é texto livre — não usa tool use.

### Retry com tenacity

Erros transitórios (`RateLimitError`, `APIConnectionError` — inclui timeout — e
`InternalServerError`, que cobre 5xx/529 "overloaded") fazem o sistema tentar
novamente até 3 vezes com backoff exponencial (1s → 2s → 4s, máx 10s):

```python
_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError)
    ),
    reraise=True,
)
```

Erros permanentes (chave inválida, resposta malformada) propagam imediatamente.
Esgotados os retries, o erro vira **HTTP 503** com mensagem amigável (ver
"Tratamento de erros").

### Singleton do cliente

O `anthropic.Anthropic(...)` é criado uma única vez em `_cliente_cache`, com
`timeout=60.0` (falha rápido em vez de prender o worker — o default do SDK é 10 min)
e `max_retries=0` (as retentativas ficam centralizadas no tenacity, evitando retry
duplicado). Isso também evita criar um novo cliente HTTP a cada requisição e mantém
o pool de conexões vivo.

### Robustez do chat de triagem

A conversa aluno ↔ mentor foi desenhada para não quebrar com uso fora do feliz:

- **Histórico sanitizado** (`profile_service._historico_para_claude`): descarta
  mensagens vazias, funde mensagens consecutivas do mesmo papel em um único turno
  (a API exige papéis alternados — sem isso, uma falha entre gravar a mensagem do
  aluno e obter a resposta corromperia o histórico para sempre) e garante que a
  primeira mensagem seja `user`.
- **Histórico completo**: o chat envia **todo** o histórico armazenado ao Claude (sem
  limite de janela); a geração do perfil também usa o histórico completo. Custo
  desprezível com Haiku mesmo no pior caso (100 msgs × 150 tokens ≈ $0,004/turno).
- **Nota de progresso** (`profile_service._montar_nota_progresso`): a partir do 5º
  turno, uma nota determinística (sem chamada extra ao Claude) é injetada no final do
  system prompt, indicando quais dos 7 pontos da triagem já foram iniciados. Impede
  que o mentor re-pergunte sobre tópicos já cobertos mesmo em conversas longas.
- **Limite da conversa**: `LIMITE_MENSAGENS_TRIAGEM` (100 mensagens user+assistant);
  ao atingir, `ValueError` → 400 orientando o aluno a finalizar a triagem.
- **Validação de entrada**: o schema rejeita mensagens vazias/só de espaços (422) e
  acima de 5000 caracteres; o serviço revalida (defesa em profundidade).
- **Resposta vazia do Claude** → `RuntimeError` (500), nunca uma bolha vazia no chat.
- **Prompt da triagem** (`PROMPT_SISTEMA_TRIAGEM`): uma pergunta por vez, tom
  acolhedor, pt-BR, respostas curtas, e instruções explícitas para recusar pedidos
  fora do escopo (escrever código, mudar de papel, revelar o prompt) e retomar a
  conversa de onde parou.

---

## Tratamento de erros

### Falhas da API Anthropic → 503

`app/main.py` registra `@app.exception_handler(anthropic.APIError)`: qualquer falha
da API do Claude (rate limit, conexão/timeout, 5xx) que sobreviver aos retries vira
**HTTP 503** com `{"detail": "O mentor (IA) está indisponível no momento. ..."}` —
distinguindo indisponibilidade transitória (o aluno pode tentar de novo; o chat
exibe a mensagem) de erros internos reais (500 abaixo).

### Handler genérico de 500

`app/main.py` registra um `@app.exception_handler(Exception)` que captura qualquer
exceção não tratada, loga com `logger.exception(...)` e retorna HTTP 500 com:

```json
{"detail": "Erro interno do servidor. Tente novamente ou contate o suporte."}
```

### Comportamento no TestClient (Starlette)

O `ServerErrorMiddleware` do Starlette **sempre re-levanta** exceções após enviar a
resposta, mesmo quando um handler de 500 está registrado. Para testar respostas 500,
use o fixture `error_client`:

```python
# tests/conftest.py
@pytest.fixture
def error_client(db_session):
    ...
    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as c:
        yield c
```

Use `error_client` em vez de `client` apenas nos testes que precisam checar o status
HTTP de exceções não tratadas.

---

## Convenções de código

### Nomenclatura

- **Rotas JSON**: verbos em inglês (`/students`, `/triage`, `/pdi`, `/curriculum`,
  `/auth/login`, `/auth/logout`, `/auth/me`)
- **Rotas HTML**: substantivos em português (`/alunos`, `/alunos/{id}/triagem`,
  `/login`, `/alunos/novo`)
- **Serviços**: verbos em português (`criar_aluno`, `gerar_pdi`, `finalizar_triagem`,
  `autenticar_aluno`, `gerar_hash_senha`)
- **Funções privadas**: prefixo `_` (`_cliente`, `_upsert`, `_aluno_da_sessao`)

### Logging

Cada módulo tem seu próprio logger:

```python
import logging
logger = logging.getLogger(__name__)
```

Configuração centralizada em `main.py` via `logging.config.dictConfig`. SQLAlchemy,
httpx e anthropic têm nível WARNING para reduzir ruído.

### Validação de entrada

- Schemas Pydantic em `schemas.py` com `Field(ge=1, le=12)`, `Field(min_length=1)` etc.
- Formulários HTML com `Form(..., ge=1, le=12)` no próprio handler
- FastAPI retorna 422 automaticamente para qualquer campo inválido

---

## Como adicionar um novo endpoint JSON

1. **Crie ou atualize o schema** em `app/schemas.py`:
   ```python
   class MinhaSaidaRead(BaseModel):
       model_config = ConfigDict(from_attributes=True)
       id: int
       ...
   ```

2. **Implemente a lógica** em `app/services/meu_service.py`:
   ```python
   import logging
   from app.services._base import upsert_registro
   logger = logging.getLogger(__name__)

   def minha_funcao(db, student_id): ...
   ```

3. **Crie o router** em `app/routes/meu_router.py`:
   ```python
   from fastapi import APIRouter, Depends
   from app.database import get_db
   from app.models import Student
   from app.routes._deps import verificar_proprio_aluno

   router = APIRouter(prefix="/meu-recurso", tags=["meu-recurso"])

   @router.post("/{student_id}/gerar")
   def gerar(
       student_id: int,
       db = Depends(get_db),
       _aluno: Student = Depends(verificar_proprio_aluno),
   ):
       ...
   ```
   `verificar_proprio_aluno` garante 401 (sem sessão) / 403 (outro aluno) antes de
   qualquer lógica rodar. Para rotas HTML, use `verificar_proprio_aluno_html`
   (redireciona para `/login` em vez de 401).

4. **Registre o router** em `app/main.py`:
   ```python
   from app.routes import meu_router
   app.include_router(meu_router.router)
   ```

5. **Escreva os testes** em `tests/test_meu_router.py`. Use o fixture `client` para
   happy paths e `error_client` para cenários que testam HTTP 500.

---

## Como adicionar uma rota HTML

1. Adicione o handler no router de domínio adequado em `app/routes/` (`paginas_web.py`,
   `perfil_web.py`, `pdi_web.py` ou `curriculo_web.py`) com `response_class=HTMLResponse`
   (o `include_in_schema=False` é herdado do router). Use o objeto `templates` e os
   helpers (`linhas`/`itens_csv`/`primeiro_erro`) de `app/routes/_web.py`.
2. Crie o template em `app/templates/minha_pagina.html` estendendo `base.html`.
3. Se criar um router novo, registre-o em `app/main.py` (os existentes já estão incluídos).

---

## Banco de dados

O SQLite é gerado automaticamente no `lifespan` de `main.py`:

```python
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    yield
```

Para alterar o banco (ex.: PostgreSQL), basta mudar `DATABASE_URL` no `.env`. O código
usa SQLAlchemy padrão sem dialeto específico, então a migração é transparente para a
maioria dos casos. Para bancos com migração de schema, adicione Alembic.

---

## Testes

```
tests/
├── conftest.py             # Fixtures: db_session, client, error_client, aluno_logado
├── test_auth.py            # auth_service, /auth/*, autorização cruzada entre alunos
├── test_students.py        # CRUD de alunos + validação de campos
├── test_triage.py          # Chat de triagem + finalização
├── test_pdi.py             # Geração e consulta de PDI
├── test_curriculum.py      # Geração e consulta de currículo
├── test_web.py             # Frontend HTML end-to-end (login/logout incluídos)
├── test_services.py        # Testes unitários da camada de serviço
├── test_melhorias.py       # Headers de segurança, config de produção, e-mail normalizado
├── test_admin.py           # Painel /admin: autorização, métricas, diagnóstico e gestão
└── test_claude_failures.py # Falhas de API (usa error_client)
```

### Fixtures principais

| Fixture | Uso |
|---------|-----|
| `db_session` | Sessão SQLite em memória com `StaticPool` (sem estado entre testes) |
| `client` | TestClient normal (re-levanta exceções para facilitar debug) |
| `error_client` | TestClient com `raise_server_exceptions=False` (para testar HTTP 500) |
| `aluno_logado` | Cadastra um aluno via `POST /students` (já autentica o `client` via cookie de sessão) e retorna o JSON do aluno |

Como `POST /students` inicia a sessão automaticamente, o `client` (ou `error_client`)
usado para criar um aluno fica autenticado como esse aluno para as chamadas
seguintes. Para cenários de autorização cruzada (aluno A acessando dados de B), use
dois `TestClient`s separados compartilhando o mesmo `db_session` via
`app.dependency_overrides[get_db]` — veja `tests/test_auth.py`.

### Mocking do Claude

Todos os testes que exercitam código que chama Claude usam `unittest.mock.patch`:

```python
from unittest.mock import patch
from tests.conftest import PERFIL_FAKE

with patch("app.services.claude_client.gerar_perfil_estruturado", return_value=PERFIL_FAKE):
    r = client.post(f"/triage/{sid}/finalizar")
```

Os objetos `PERFIL_FAKE`, `PDI_FAKE` e `CURRICULO_FAKE` estão definidos em
`tests/conftest.py` e reproduzem fielmente o schema real retornado pelo Claude.

---

## Variáveis de configuração

Definidas em `app/config.py` via `pydantic-settings`. A lista completa (nomes, padrões e
descrições) está em [`docs/INSTALACAO.md`](docs/INSTALACAO.md#4-configuração-env) e no
[`.env.example`](.env.example).

Detalhe arquitetural: `get_settings()` usa `@lru_cache` — é chamada uma única vez por
processo. Para forçar releitura (ex.: nos testes), chame `get_settings.cache_clear()`.
