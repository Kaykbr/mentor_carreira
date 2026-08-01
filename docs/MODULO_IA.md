# Módulo de IA — como funciona

Documentação da camada de inteligência artificial do **Mentor de Carreira**: como o
sistema conversa com o Claude (Anthropic), como cada saída é gerada e como o fluxo é
mantido robusto e tolerante a falhas.

> Código: [`app/services/claude_client.py`](../app/services/claude_client.py) (camada de
> IA) e [`app/services/profile_service.py`](../app/services/profile_service.py) (orquestra
> a triagem). Diagramas de sequência em [`diagramas/`](../diagramas/).

---

## 1. Visão geral

Todo contato com a API da Anthropic passa por **um único módulo**: `claude_client.py`.
Nenhuma outra parte do código importa o SDK `anthropic` diretamente. Isso concentra em um
só lugar: o modelo usado, o timeout, a política de retry, o logging de custo e o tratamento
de respostas. Os *services* de domínio (perfil, PDI, currículo) chamam funções desse módulo
e cuidam de ler/gravar no banco.

```
Rota (HTTP)        →  Service de domínio       →  claude_client            →  Anthropic API
 triage.py             profile_service             conversar_triagem            (Claude)
 (finalizar)           profile_service             gerar_perfil_estruturado
 pdi.py                pdi_service                 gerar_pdi
 curriculum.py         curriculum_service          gerar_curriculo
 curriculo_vaga_web    analise_vaga_service        extrair_requisitos_vaga
 curriculo_vaga_web    curriculum_vaga_service     gerar_recomendacoes_vaga
```

---

## 2. As sete operações de IA

Cada operação é uma função pública de `claude_client.py`. Duas técnicas são usadas:

| Função | Quando | Técnica | Saída | Modelo |
|--------|--------|---------|-------|--------|
| `conversar_triagem(historico, nome_aluno?, curso?, periodo?)` | a cada mensagem do chat | texto livre | próxima fala do mentor (str) | `CLAUDE_MODEL` |
| `gerar_perfil_estruturado(historico)` | ao finalizar a triagem | **tool use forçado** (`salvar_perfil_aluno`) | `profile_json` (dict) | `CLAUDE_MODEL_ANALISE` (fallback `CLAUDE_MODEL`) |
| `gerar_pdi(profile_json, contexto_aluno?)` | gerar/regenerar PDI | **tool use forçado** (`salvar_pdi`) | `pdi_json` (dict) | `CLAUDE_MODEL_GERACAO` (fallback `CLAUDE_MODEL`) |
| `gerar_curriculo(profile_json, pdi_json?, contexto_aluno?)` | gerar/regenerar currículo (geral ou **por vaga**, via `contexto["vaga"]`) | texto livre | currículo em texto (str) | `CLAUDE_MODEL_GERACAO` (fallback `CLAUDE_MODEL`) |
| `extrair_requisitos_vaga(jd_text)` | analisar uma vaga (JD) | **tool use forçado** (`salvar_requisitos_vaga`) | requisitos da vaga (dict) | `CLAUDE_MODEL_ANALISE` (fallback `CLAUDE_MODEL`) |
| `gerar_recomendacoes_vaga(profile_json, analise)` | currículo por vaga | **tool use forçado** (`salvar_recomendacoes_vaga`) | recomendações (dict: resumo, pontos fortes, melhorias, projetos, dicas) | `CLAUDE_MODEL_GERACAO` (fallback `CLAUDE_MODEL`) |
| `analisar_curriculo(curriculum_text, profile_json, diagnostico)` | dicas de melhoria do currículo base | **tool use forçado** (`salvar_analise_curriculo`) | análise (dict: resumo, pontos fortes, melhorias com exemplo reescrito, seções a reforçar) | `CLAUDE_MODEL_GERACAO` (fallback `CLAUDE_MODEL`) |

Ver §6 para o racional da escolha de modelo por operação.

### Tool use forçado (saídas estruturadas)
Para o **perfil** e o **PDI**, o sistema precisa de um JSON com um formato exato. Em vez de
pedir "responda em JSON" (frágil), define-se uma *ferramenta* com `input_schema` (o schema
do JSON) e força-se o Claude a chamá-la:

```python
tool_choice={"type": "tool", "name": "salvar_pdi"}
```

A Anthropic garante que a resposta seja uma chamada dessa ferramenta com argumentos
aderentes ao schema — então `bloco.input` já é o dict válido. Essas chamadas usam
`temperature=0.0` para máxima consistência.

### Texto livre
A **triagem** (conversa) e o **currículo** (texto ATS) usam saída de texto comum, com a
temperatura padrão do modelo (mais natural). O texto é extraído concatenando os blocos
`type == "text"` da resposta.

**Decisão arquitetural — currículo como texto livre**: mesmo com `profile_json`,
`pdi_json` e `contexto_aluno` cada vez mais ricos, o currículo continua sendo texto livre
(`Curriculum.curriculum_text`), não um `curriculum_json` estruturado — o esforço de
qualidade está nos *dados de entrada* e no `PROMPT_GERAR_CURRICULO`, não no formato de
saída. Vale revisitar essa decisão se, no futuro, os dados de entrada já estiverem ricos o
suficiente e ainda faltar controle de formatação (ex.: exportar para um template visual
fixo em PDF).

### Quadro Kanban: materializado fora da IA
O schema da ferramenta `salvar_pdi` **não inclui** o quadro Kanban. Após a IA gerar o PDI,
`pdi_service` acrescenta a chave `quadro_kanban` ao `pdi_json` a partir das
`acoes_recomendadas` (`_montar_quadro`) — isto é responsabilidade da **camada de serviço**,
não do modelo. Consequência: **regenerar o PDI reseta o quadro** (conteúdo novo da IA →
quadro novo), e a edição do quadro pelo aluno (mover/adicionar cards) é independente da IA.
A edição manual de perfil/PDI/currículo também não passa pela IA — sobrescreve o registro no
banco diretamente.

Cards com `coluna == "concluido"` também alimentam o **currículo**: `gerar_curriculo` lê
`pdi_json.quadro_kanban`, extrai os textos dos cards concluídos e os envia ao Claude como
"ações de desenvolvimento já concluídas" — evidência recente de trabalho prático que pode
enriquecer as seções PROJETOS e SKILLS TÉCNICAS do currículo gerado.

### Contexto do aluno (`contexto_aluno.py`)
`profile_json` guarda o que o aluno contou na triagem, mas alguns dados já existem no
cadastro (`Student.nome`, `email`, `curso`, `periodo`) e não fazem sentido duplicar ali.
`app/services/contexto_aluno.py::montar_contexto(db, student_id)` monta um `ContextoAluno`
(nome, e-mail, curso, período) a partir do `Student` — ponto único de acesso a esses dados
para a camada de IA.

- `pdi_service.gerar_pdi` repassa `{"curso": ..., "periodo_atual": ...}` para
  `gerar_pdi(profile_json, contexto_aluno=...)`, usado pelo `PROMPT_GERAR_PDI` para
  calibrar o cronograma à fase do curso (ver §3, "Humanização").
- `curriculum_service.gerar_curriculo` repassa
  `{"nome": ..., "email": ..., "curso": ..., "periodo_atual": ...}` para
  `gerar_curriculo(profile_json, pdi_json?, contexto_aluno=...)`, usado pelo
  `PROMPT_GERAR_CURRICULO` para montar o cabeçalho de contato e a seção FORMAÇÃO.

Em ambos os casos, `contexto_aluno` é **opcional** (`None` por padrão): se o aluno não for
encontrado, a chamada segue sem esse bloco extra no prompt. O `profile_json` completo — que
inclui a `stack_tecnica` e as `areas_afinidade` (ver §2b) — é passado como base, e os prompts
orientam o Claude a direcionar PDI e currículo às áreas de afinidade e à stack real do aluno.

---

## 2b. Áreas de afinidade geradas pela IA (substituem trilhas + radar)

As **trilhas de carreira** (catálogo de 24 trilhas, recomendador determinístico e Radar de
Competências) **foram removidas**: o recomendador por substring errava com frequência (ex.:
"quero dados/IA" recomendava "full-stack"). No lugar, o **próprio `FERRAMENTA_PERFIL`** ganhou
o campo `areas_afinidade` — a IA lê **toda a triagem** e sugere de 2 a 4 áreas que combinam com
o aluno, cada uma com um `porque`. Como o modelo enxerga o contexto inteiro, o resultado é bem
mais fiel do que o casamento léxico anterior. As áreas são exibidas no perfil e no dashboard
como **possibilidades a explorar**, não um veredito.

Permanece **`app/services/competencias.py`** (`normalizar`/`corresponder`/`presente`/
`pontuar_match`): substring bidirecional case-insensitive **+ expansão por sinônimos**
(`app/data/sinonimos.py`), de modo que "JS" case com "JavaScript" e "nodejs" com "Node.js". É
usado pela **Análise de Vaga** e pelo RAG (§2c) — não mais por trilha/radar, que deixaram de
existir.

## 2c. RAG de recursos de aprendizado (`rag_service.py`)

Naive RAG **sem embeddings**, determinístico. Consulta o corpus estático
`app/data/recursos_aprendizado.py` (~115 competências → links de cursos/livros/tutoriais,
quase todos gratuitos). Para cada competência-alvo, **pontua todas as chaves candidatas** com
`competencias.pontuar_match` (exato > sinônimo > substring) e usa as mais aderentes primeiro
(sem repetir URLs). Hoje é consumido pela **Análise de Vaga** (`analise_vaga_service`), que
recupera recursos para as lacunas identificadas na comparação perfil × requisitos da vaga. O
PDI deixou de puxar recursos por-lacuna: passou a ser gerado de forma mais enxuta, ancorado no
que o aluno trouxe na triagem, e o aluno pode editar/curar o plano.

> Caminho pronto para evoluir: trocar `corresponder`/`pontuar_match` por similaridade
> vetorial (embeddings) afetaria só `competencias.py`/`rag_service.py` — os chamadores não
> mudam.

## 2e. Diagnóstico do currículo — regras primeiro, IA depois

A avaliação do currículo base é o exemplo mais claro da divisão adotada no projeto:

1. **`curriculo_qualidade.diagnosticar`** (função pura, sem IA) confere o texto contra o
   contrato que o próprio `PROMPT_GERAR_CURRICULO` impõe: 7 seções na ordem correta,
   cabeçalho com e-mail/links, bullets iniciados por verbo de ação no passado, presença de
   resultados quantificados, ausência de Markdown (que quebra ATS), tamanho e densidade das
   palavras-chave da stack do perfil. Pesos explícitos → `pontuacao` de 0 a 100 **auditável**.
2. **`claude_client.analisar_curriculo`** recebe o texto, o perfil e **apenas os itens
   problemáticos** do diagnóstico. Não repete a medição: escreve o julgamento — o que está
   mal priorizado, o que comunica a impressão errada, e um `exemplo_reescrito` de um trecho
   real do aluno.

Consequências práticas: o checklist é grátis e roda a cada exibição da página (reflete
edição manual na hora), enquanto a análise da IA custa uma chamada e é persistida. O prompt
proíbe explicitamente sugerir inventar/exagerar experiências — o risco específico aqui seria
a IA orientar o aluno a mentir no currículo; quando falta substância, ela deve orientar a
**construir** a experiência, não a fabricá-la no texto.

## 2d. Currículo por Vaga (JD Analyzer) — IA + matching + RAG

O fluxo de **currículo por vaga** (`curriculum_vaga_service.gerar`) combina **IA e
determinismo** em três etapas. A primeira é a análise (`analise_vaga_service.analisar`):

1. A **IA** lê a descrição da vaga e extrai requisitos estruturados via tool use forçado
   (`salvar_requisitos_vaga`): `cargo`, `nivel`, `modalidade`, `competencias_tecnicas[]`,
   `soft_skills[]`, `diferenciais[]`. Usa `CLAUDE_MODEL_ANALISE` e `temperature=0` (extração,
   não criação), com o *system prompt* marcado como cacheável (`cache_control: ephemeral`).
2. O **matching é determinístico** (`competencias.presente`): cada requisito é classificado
   contra o perfil/PDI do aluno em `possui` / `em_desenvolvimento` / `lacuna`, e o **score de
   aderência** (%) é calculado em código — a IA nunca "dá nota".
3. As **lacunas** alimentam o **RAG** (`rag_service.recuperar_recursos`) para sugerir o que
   estudar.

Ou seja: a IA faz só o que faz bem (interpretar o texto livre da vaga); a comparação com o
aluno e a pontuação ficam num caminho auditável e testável **sem mock de IA**.

---

## 3. Fluxo da conversa de triagem (o caminho mais sensível)

A triagem é o único fluxo verdadeiramente interativo (o aluno digita várias vezes), então é
o que mais precisa de robustez. Cada envio (`POST /triage/{id}/mensagens`) faz:

1. **Validação de entrada** — o schema `TriageMensagemEnvio` faz `strip()`, rejeita vazio/só
   espaços (422) e mais de 5000 caracteres.
2. **Limite da conversa** — se o aluno já tem `LIMITE_MENSAGENS_TRIAGEM` (100) mensagens,
   o serviço levanta `ValueError` → **400**, orientando a finalizar a triagem.
3. **Persistir a mensagem do aluno** (`role="user"`) antes de chamar a IA — se a IA falhar,
   nada do que o aluno escreveu se perde.
4. **Montar o histórico para o Claude** — via `_historico_para_claude` (sanitização, ver §4),
   limitado às últimas `_JANELA_CONTEXTO_CHAT` (40) mensagens.
5. **Chamar `conversar_triagem`** (com retry).
6. **Persistir a resposta** (`role="assistant"`) e devolvê-la ao chat.

A geração do **perfil** (`finalizar_triagem`) usa o histórico **completo** (não a janela de
40), também sanitizado.

### Humanização

- **Nome do aluno**: `_prompt_triagem(nome_aluno, curso, periodo)` acrescenta ao
  `PROMPT_SISTEMA_TRIAGEM` uma instrução para o mentor usar o nome do aluno com
  naturalidade (saudação inicial e ocasionalmente ao longo da conversa).
  `profile_service.enviar_mensagem_triagem` busca o aluno no banco e repassa `nome_aluno`,
  `curso` e `periodo` a `conversar_triagem`.
- **Calibração por curso/período**: quando `nome_aluno` é informado e `curso`/`periodo`
  também estão presentes, `_prompt_triagem` acrescenta uma instrução para calibrar o tom e
  o tipo de pergunta à fase do curso — períodos iniciais (até o 3º) tendem a ter menos
  experiência profissional (foco em fundamentos), períodos avançados (a partir do 7º) já
  podem ter estágios, TCC e projetos maiores. O período nunca é mencionado explicitamente
  ao aluno.
- **Acolhimento de insegurança**: o `PROMPT_SISTEMA_TRIAGEM` instrui o mentor a, quando o
  aluno disser "não sei"/"não tenho experiência" ou demonstrar insegurança, acolher isso
  como normal e valorizar o que ele já tem antes de seguir para o próximo ponto.
- **PDI e currículo** pedem para reconhecer genuinamente os pontos fortes já presentes no
  perfil (e no PDI, no caso do currículo), sem inventar ou exagerar informações.
- **Texto sem Markdown**: o front exibe as respostas como texto puro, então os prompts
  proíbem Markdown e, como defesa em profundidade, `app/services/texto.limpar_markdown`
  remove ênfase (`**`/`*`/`_`), marcadores de lista (`- `) e `#` das saídas da IA (resposta
  da triagem, `resumo_geral`/`areas_afinidade` do perfil e textos livres do PDI) antes de
  persistir/exibir.

---

## 4. Robustez e tolerância a falhas

### Histórico sanitizado — evita o chat "quebrar para sempre"
A API exige mensagens com papéis **alternados** (`user` → `assistant` → `user`…). Se a
chamada ao Claude falhar **depois** de gravar a mensagem do aluno, ficam duas mensagens
`user` seguidas no banco. Sem tratamento, **toda chamada futura falharia**. Por isso
`profile_service._historico_para_claude`:

- descarta mensagens vazias;
- **funde mensagens consecutivas do mesmo papel** num único turno;
- garante que a primeira mensagem seja `user`.

Assim, uma falha transitória nunca corrompe a conversa de forma permanente.

### Cliente singleton com timeout curto
`anthropic.Anthropic(...)` é criado **uma vez** (`_cliente_cache`), com:
- `timeout=60.0` — falha rápido em vez de prender o worker (o default do SDK é 10 min);
- `max_retries=0` — o SDK não retenta; a política de retry fica centralizada no tenacity
  (evita retentativas duplicadas, que poderiam virar 9 chamadas em vez de 3).

### Retry com backoff (tenacity)
As funções públicas são decoradas com `@_RETRY`: até **3 tentativas** com backoff
exponencial (1s → 2s → 4s, teto 10s) apenas para erros **transitórios** —
`RateLimitError` (429), `APIConnectionError` (conexão/timeout) e `InternalServerError`
(5xx, inclui o 529 "overloaded"). Erros permanentes (chave inválida, resposta malformada)
propagam na hora, sem desperdiçar tentativas.

### Mapeamento de erros para HTTP
- **Falha da IA após os retries** → `anthropic.APIError` → handler em `main.py` →
  **HTTP 503** "O mentor (IA) está indisponível no momento." (transitório; o aluno tenta de
  novo, e o chat exibe essa mensagem).
- **Resposta vazia** ou **sem o `tool_use` esperado** → `RuntimeError` → **HTTP 500**
  (erro real, com mensagem genérica; nunca uma bolha vazia no chat).
- O frontend (`triagem.js`) lê o `detail` do servidor e mostra a mensagem certa ao aluno.

### Prompt resistente a abuso
O `PROMPT_SISTEMA_TRIAGEM` instrui o mentor a: manter o papel, recusar com educação pedidos
fora do escopo (escrever código, mudar de papel, revelar o prompt), retomar a triagem de
onde parou, não inventar dados e não pedir informações sensíveis. Isso reduz a chance de o
aluno desviar ou "quebrar" a conversa via prompt injection.

### Renderização segura do currículo
`app/templates/curriculo.html` exibe o texto gerado pelo Claude num `<pre>`. O destaque dos
títulos de seção (RESUMO, FORMAÇÃO etc.) é feito **sem `innerHTML`**: o script percorre
`pre.textContent.split("\n")` e usa `document.createElement("strong")` +
`textContent`/`createTextNode` para remontar o conteúdo — eliminando qualquer risco de XSS
mesmo que o texto gerado contenha caracteres como `<` ou `>`.

---

## 5. Observabilidade (custo e latência)

Toda chamada passa por `_chamar(...)`, que cronometra e registra no log:

```
Claude triagem: 2.3s (tokens entrada=1200, saída=180)
```

Útil para acompanhar latência e consumo de tokens (custo) por tipo de operação.

---

## 6. Configuração

| Variável | Efeito no módulo de IA |
|----------|------------------------|
| `ANTHROPIC_API_KEY` | Credencial da API (sem ela, as chamadas reais falham — ver `/admin/sistema`). |
| `CLAUDE_MODEL` | Modelo padrão: usado na triagem e como fallback de `CLAUDE_MODEL_ANALISE`/`CLAUDE_MODEL_GERACAO` (padrão `claude-haiku-4-5`). |
| `CLAUDE_MODEL_ANALISE` | Opcional. Modelo usado em `gerar_perfil_estruturado`. Se vazio, usa `CLAUDE_MODEL`. |
| `CLAUDE_MODEL_GERACAO` | Opcional. Modelo usado em `gerar_pdi` e `gerar_curriculo`. Se vazio, usa `CLAUDE_MODEL`. |

Trocar de modelo é só mudar a variável no `.env` e reiniciar — nenhum código muda. Os
valores efetivos (incluindo o fallback quando não configurados) aparecem em
`/admin/sistema`.

Constantes internas em `claude_client.py`: `_MAX_TOKENS_CHAT` (1024), `_MAX_TOKENS_ESTRUTURADO`
(4096) e `_TEMPERATURA_EXTRACAO` (0.0).

### Modelo por operação (otimização de custo)

`_resolver_modelo(override) -> override or get_settings().claude_model` decide o modelo de
cada chamada. Cada função pública passa o override apropriado para `_chamar(..., modelo=...)`:

- **`conversar_triagem`**: sempre `CLAUDE_MODEL` — é o fluxo mais sensível à qualidade
  conversacional e à humanização (tom, empatia, personalização com o nome do aluno), então
  não vale a pena arriscar um modelo mais fraco aqui.
- **`gerar_perfil_estruturado`**: `CLAUDE_MODEL_ANALISE` (fallback `CLAUDE_MODEL`). É uma
  tarefa de **análise determinística** — extrair campos de um JSON a partir da conversa,
  com `temperature=0` e tool use forçado — boa candidata a um modelo mais barato/rápido
  (ex.: `claude-haiku-4-5`), já que o schema rígido compensa a menor capacidade do modelo.
- **`gerar_pdi`** e **`gerar_curriculo`**: `CLAUDE_MODEL_GERACAO` (fallback `CLAUDE_MODEL`).
  São textos **completos e de qualidade** (recomendações de carreira, currículo ATS), onde
  vale manter (ou configurar explicitamente) um modelo mais robusto.

Por decisão arquitetural, a otimização fica **dentro da família Claude** — sem introduzir
um segundo provedor (ex.: Gemini), nova dependência, nova chave de API ou camada de
abstração extra. Isso preserva o princípio de "Claude Client — único ponto de contato com a
API Anthropic" (ver [`CLAUDE.md`](../CLAUDE.md)). Como os dois campos são opcionais e
default para `None`, `.env` existentes continuam funcionando sem nenhuma mudança
(retrocompatível).

---

## 7. Como é testado (sem gastar API)

Nenhum teste chama a API real: o Claude é **mockado** com `unittest.mock.patch`.

```python
from unittest.mock import patch
with patch("app.services.claude_client.conversar_triagem", return_value="Olá!"):
    client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
```

Cenários cobertos (ver `tests/test_triage.py`, `tests/test_claude_failures.py`,
`tests/test_services.py`): recuperação após falha (fusão de papéis), limite → 400, vazio →
422, rate limit/conexão → 503, resposta sem `tool_use` → 500 e os unitários do sanitizador
de histórico.

---

## 8. Próximos passos (sugestões)

- **Prompt caching**: marcar o prompt de sistema/ferramentas como cacheáveis reduz custo e
  latência na triagem (o system prompt é reenviado a cada turno).
- **Streaming** da resposta do mentor (efeito "digitando"), para um chat mais fluido.
- **Rate limiting por minuto** no envio de mensagens (hoje o limite é por conversa).
- **Resumo de contexto**: ao se aproximar do limite, resumir o histórico antigo em vez de
  apenas cortar a janela.
