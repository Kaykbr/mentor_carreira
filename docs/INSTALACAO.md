# Guia de instalação e execução

Guia completo, passo a passo, para rodar o **Mentor de Carreira** do zero — pensado para
quem nunca viu o projeto. Para a visão geral, veja o [README](../README.md); para a
arquitetura interna, o [CLAUDE.md](../CLAUDE.md).

---

## 1. Pré-requisitos

| Ferramenta | Versão | Obrigatória? | Para quê |
|------------|--------|--------------|----------|
| **Python** | 3.12 ou superior | **Sim** | Rodar a aplicação e os testes |
| **pip** | (vem com o Python) | **Sim** | Instalar dependências |
| **Git** | qualquer recente | Recomendada | Clonar o repositório |
| **Chave da API Anthropic** | — | Sim, para uso real* | Conversar com o Claude |
| **GNU Make** | qualquer | Opcional | Atalhos (`make run`, `make test`); no Windows use **Git Bash** ou **WSL** |
| **Node.js + npm** | 18+ | Opcional | Apenas para **regerar os diagramas** (`make diagrams`) |

\* Os **testes não exigem** chave válida — todas as chamadas ao Claude são *mockadas*.
A chave só é necessária para usar a triagem/PDI/currículo de verdade.
Obtenha em <https://console.anthropic.com>.

---

## 2. O que cada dependência faz

### Produção — `requirements.txt`

| Pacote | Para quê |
|--------|----------|
| `fastapi` | Framework web (rotas, validação, `/docs` automático) |
| `uvicorn[standard]` | Servidor ASGI que executa a aplicação |
| `sqlalchemy` | ORM — mapeia as tabelas para classes Python |
| `pydantic` / `pydantic[email]` | Validação de entrada/saída (e validação de e-mail) |
| `pydantic-settings` | Lê as configurações do `.env` |
| `anthropic` | SDK oficial da Claude (Anthropic) |
| `python-dotenv` | Carrega o arquivo `.env` |
| `jinja2` | Renderiza os templates HTML (frontend) |
| `python-multipart` | Processa formulários HTML (login/cadastro) |
| `tenacity` | Retentativas com backoff nas chamadas ao Claude |
| `passlib[bcrypt]` | Hash e verificação de senhas (bcrypt) |
| `bcrypt` | Backend de hashing (fixado em `>=4.0.1,<4.1`) |
| `itsdangerous` | Assina o cookie de sessão (exigido pelo `SessionMiddleware`) |

> **Por que `bcrypt` aparece separado e fixado em `<4.1`?**
> O `passlib` 1.7.4 é incompatível com o `bcrypt` 4.1+ (dispara um erro interno de detecção
> de backend, do tipo *"password cannot be longer than 72 bytes"*, mesmo com senhas curtas).
> Por isso o `bcrypt` é fixado explicitamente em uma versão compatível.

### Desenvolvimento — `requirements-dev.txt`

| Pacote | Para quê |
|--------|----------|
| `pytest` | Executa a suíte de testes |
| `pytest-cov` | Relatório de cobertura (`make coverage`) |
| `httpx` | Cliente HTTP usado pelo `TestClient` do FastAPI nos testes |

`requirements-dev.txt` já inclui o `requirements.txt` (primeira linha `-r requirements.txt`),
então instalar o de dev instala tudo.

---

## 3. Instalação

### Opção A — com Make (recomendada)

```bash
git clone <url-do-repositorio>
cd Projeto-TCC
make install      # cria o venv e instala requirements-dev.txt
```

### Opção B — manual

**Windows (PowerShell):**
```powershell
git clone <url-do-repositorio>
cd Projeto-TCC
python -m venv venv
venv\Scripts\pip install --upgrade pip
venv\Scripts\pip install -r requirements-dev.txt
```

**Linux / macOS:**
```bash
git clone <url-do-repositorio>
cd Projeto-TCC
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements-dev.txt
```

> Se for só rodar (sem testar), pode usar `requirements.txt` no lugar de
> `requirements-dev.txt`.

---

## 4. Configuração (`.env`)

Copie o exemplo e preencha a chave:

```bash
# Windows:  copy .env.example .env
# Linux/macOS:
cp .env.example .env
```

Edite o `.env`:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...          # sua chave (obrigatória para uso real)
DATABASE_URL=sqlite:///./mentor.db    # padrão; troque para outro banco se quiser
CLAUDE_MODEL=claude-haiku-4-5         # modelo Claude
SECRET_KEY=troque-por-um-valor-forte  # assina o cookie de sessão
SESSION_MAX_AGE=28800                 # duração da sessão em segundos (8h)
```

| Variável | Padrão | Obrigatória | Descrição |
|----------|--------|-------------|-----------|
| `ANTHROPIC_API_KEY` | — | **Sim** (uso real) | Chave da API Anthropic |
| `DATABASE_URL` | `sqlite:///./mentor.db` | Não | URL de conexão SQLAlchemy |
| `CLAUDE_MODEL` | `claude-haiku-4-5` | Não | Modelo Claude padrão (triagem; e fallback das duas variáveis abaixo) |
| `CLAUDE_MODEL_ANALISE` | *(vazio → usa `CLAUDE_MODEL`)* | Não | Modelo para extrair o perfil ao final da triagem (análise determinística); pode ser um modelo mais barato (ex.: `claude-haiku-4-5`) |
| `CLAUDE_MODEL_GERACAO` | *(vazio → usa `CLAUDE_MODEL`)* | Não | Modelo para gerar PDI e currículo (textos completos) |
| `APP_ENV` | `development` | Não | `development` ou `production`; em produção a config é validada com mais rigor |
| `SECRET_KEY` | `dev-insecure-secret-change-me` | Não (troque em produção) | Assina o cookie de sessão |
| `SESSION_MAX_AGE` | `28800` (8h) | Não | Duração da sessão, em segundos |
| `SESSION_HTTPS_ONLY` | `false` | Não | Cookie só por HTTPS (Secure); vira `true` em `production` por padrão |
| `ADMIN_EMAILS` | *(vazio)* | Não | E-mails (separados por vírgula) com acesso ao painel `/admin` |

> Em **produção** (`APP_ENV=production`): a aplicação **recusa subir** se a `SECRET_KEY`
> ainda for o valor padrão inseguro, e o cookie de sessão passa a exigir HTTPS
> (`SESSION_HTTPS_ONLY=true`) automaticamente.

> Em produção, gere uma `SECRET_KEY` forte:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

## 5. Banco de dados

Não há passo manual: o SQLite é criado automaticamente na primeira vez que o servidor sobe
(o `lifespan` em `app/main.py` chama `Base.metadata.create_all`). O arquivo `mentor.db`
aparece na raiz do projeto.

> **Atualizou de uma versão antiga (sem login)?** A coluna `password_hash` é `NOT NULL`. Se
> você tinha um `mentor.db` anterior, apague-o antes de subir o servidor — ele será recriado
> com o esquema novo. (O `mentor.db` está no `.gitignore`, então não é versionado.)

---

## 6. Rodar o servidor

```bash
make run
# ou, manualmente:
#   Windows:      venv\Scripts\python -m uvicorn app.main:app --reload
#   Linux/macOS:  venv/bin/python -m uvicorn app.main:app --reload
```

Você deve ver algo como `Uvicorn running on http://0.0.0.0:8000`. Acesse:

- **Aplicação (web):** <http://localhost:8000/login>
- **Documentação da API (Swagger):** <http://localhost:8000/docs>
- **Health check:** <http://localhost:8000/health>

---

## 7. Primeiro uso (criar uma conta)

1. Abra <http://localhost:8000/login>.
2. Clique em **Cadastrar**.
3. Preencha **nome**, **e-mail**, **senha** (mínimo 8 caracteres) e **período** (1–12).
4. Ao enviar, você é **logado automaticamente** e cai no seu painel.
5. No painel, siga o fluxo:
   **Triagem** (converse com o mentor) → **Finalizar** (gera o perfil) →
   **Gerar PDI** → **Gerar currículo**.
6. Tudo que a IA gera é **editável**: use **Editar perfil** / **Editar PDI** (formulários) e
   **Editar** no currículo (texto). No PDI, as ações viram um **quadro Kanban** —
   arraste os cards entre *A Fazer*, *Em Progresso* e *Concluído* (as mudanças são salvas
   automaticamente). Não é preciso gastar a IA para ajustar: a edição grava direto no banco.

Cada aluno só enxerga os próprios dados. Tentar acessar `/alunos/{id}` de outro aluno
retorna **403**; sem sessão, as páginas redirecionam para `/login`.

### Painel de administração (`/admin`)

Para acessar o painel de administração, adicione o seu e-mail em `ADMIN_EMAILS` no `.env`
(ex.: `ADMIN_EMAILS=seu@email.com`), reinicie o servidor e faça login com essa conta —
o link **Admin** aparece na navegação. O painel mostra:

- **Visão geral**: KPIs, funil de conclusão (cadastro → triagem → perfil → PDI → currículo),
  alunos por período e cadastros por mês;
- **Alunos**: tabela com o status de cada etapa por aluno, promover/rebaixar admin e
  excluir aluno (com todos os dados);
- **Sistema**: diagnóstico automático (banco, esquema, chaves, ambiente, cookie, admins)
  e a configuração atual com segredos mascarados (somente leitura).

Um admin também pode promover outros alunos a admin pela própria interface
(flag `is_admin` no banco).

---

## 8. Rodar os testes

```bash
make test          # detalhado (193 testes)
make test-fast     # silencioso, mais rápido
make coverage      # gera htmlcov/index.html
```

Os testes usam SQLite **em memória** e mocam o Claude, então **não precisam** de
`ANTHROPIC_API_KEY` válida. Resultado esperado: **193 passando**.

---

## 9. Endpoints da API (referência rápida)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| `GET` | `/health` | Health check | — |
| `POST` | `/students` | Cadastrar aluno (já inicia a sessão) | — |
| `POST` | `/auth/login` | Login (e-mail + senha) | — |
| `POST` | `/auth/logout` | Logout (encerra a sessão) | Sim |
| `GET` | `/auth/me` | Dados do aluno autenticado | Sim |
| `GET` | `/students/{id}` | Obter aluno | Sim (próprio) |
| `GET` | `/students/{id}/profile` | Obter perfil estruturado | Sim (próprio) |
| `POST` | `/triage/{id}/mensagens` | Enviar mensagem na triagem | Sim (próprio) |
| `GET` | `/triage/{id}/mensagens` | Listar histórico da triagem | Sim (próprio) |
| `POST` | `/triage/{id}/finalizar` | Gerar perfil a partir da triagem | Sim (próprio) |
| `POST` | `/pdi/{id}/gerar` | Gerar PDI | Sim (próprio) |
| `GET` | `/pdi/{id}` | Obter PDI | Sim (próprio) |
| `POST` | `/curriculum/{id}/gerar` | Gerar currículo | Sim (próprio) |
| `GET` | `/curriculum/{id}` | Obter currículo | Sim (próprio) |

Rotas "Sim (próprio)" retornam **401** sem sessão e **403** se o aluno não for o dono do
`id`. Documentação interativa completa em `/docs`.

> A tabela acima lista a **API JSON**. As funcionalidades servidas só como **páginas HTML**
> — painel do aluno, triagem (HTMX), **análise de vaga**, edição de perfil/PDI/currículo e o
> painel **`/admin`** — usam `include_in_schema=False` e por isso **não aparecem no `/docs`**;
> são acessadas pela interface web.

---

## 10. Comandos de desenvolvimento

```bash
make lint        # verifica formatação/erros com ruff
make format      # formata o código com ruff
make diagrams    # regenera os diagramas (precisa de Node.js) — veja diagramas/README.md
make clean       # remove caches (__pycache__, .pytest_cache, htmlcov, etc.)
```

---

## 11. Troubleshooting

| Sintoma | Causa provável / solução |
|---------|--------------------------|
| Erro de validação de `ANTHROPIC_API_KEY` ao subir | Copie `.env.example` → `.env` e preencha a chave. Para só rodar os **testes**, a chave não é necessária. |
| HTTP 503 "mentor indisponível" na triagem/PDI/currículo | A API da Anthropic está fora/sobrecarregada ou sem conexão — transitório, tente de novo em instantes. |
| HTTP 500 ao usar triagem/PDI/currículo | Chave da Anthropic ausente/inválida ou resposta malformada. Confira o `.env` e os logs no terminal. |
| `sqlite3.OperationalError: ... no column named password_hash` (ou `is_admin`) | Banco antigo de uma versão anterior do schema. Apague o `mentor.db` e suba o servidor de novo. |
| `database is locked` | Outro processo está usando o `mentor.db`. Feche-o (ou pare o servidor) e tente de novo. |
| Porta 8000 em uso | Rode em outra porta: `uvicorn app.main:app --reload --port 8001`. |
| `make: command not found` (Windows) | Instale o Git Bash/WSL, ou use os comandos manuais (seções 3 e 6). |
| `make diagrams` falha baixando o Chromium | A 1ª execução do mermaid-cli baixa o Chromium do Puppeteer. Sem internet/permissão, edite os `.mmd` no <https://mermaid.live> ou aponte o Puppeteer para um Chrome instalado (`PUPPETEER_EXECUTABLE_PATH`). |
