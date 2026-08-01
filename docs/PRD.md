# PRD — Mentor de Carreira para Estudantes de Sistemas de Informação

| Campo | Valor |
|---|---|
| **Produto** | Mentor de Carreira — orientação de carreira em TI assistida por IA |
| **Status** | Em evolução · MVP entregue, com roadmap ativo |
| **Versão do documento** | 2.0 |
| **Data** | Junho/2026 |
| **Autor** | Kayky Brito (TCC — Sistemas de Informação) |
| **Documentos relacionados** | [`CLAUDE.md`](../CLAUDE.md) (arquitetura) · [`MODULO_IA.md`](MODULO_IA.md) (módulo de IA) · [`REVISAO.md`](REVISAO.md) (qualidade) · [`diagramas/`](../diagramas/) (UML + ER, v1.2) |

> ⚠️ **Nota da v2.1 (jul/2026) — trilhas removidas.** Após os testes, o **catálogo de 24
> trilhas**, o **recomendador determinístico** e o **Radar de Competências** foram
> **removidos** (o recomendador por substring errava com frequência, ex.: "quero dados/IA"
> recomendava "full-stack"). No lugar, a IA passou a gerar **`areas_afinidade`** no perfil —
> de 2 a 4 áreas que combinam com o aluno, cada uma com um "porque", como possibilidades a
> explorar. O PDI e o currículo continuam, ancorados no perfil (stack + áreas), sem RAG por
> lacuna. **As seções abaixo que descrevem trilhas/radar como entregues (ex.: escopo A/C/D,
> requisitos A1–A3, C1–C2, E3) devem ser lidas como SUPERSEDIDAS** — o RAG e o
> `competencias.py` permanecem, usados apenas pela Análise de Vaga. Esta nota substitui a
> reescrita completa das tabelas (pendente).
>
> **Changelog**
> - **v2.0 (jun/2026)** — Reestruturação completa seguindo modelos de PRD reconhecidos
>   (Atlassian/Cagan, Lenny Rachitsky, Product School). Principal mudança: separação clara
>   entre **escopo entregue (as-is)** e **roadmap (proposto)**. Várias funcionalidades que a
>   v1 listava como "propostas" já estão **entregues** (catálogo + recomendador de trilhas,
>   radar de competências, recursos RAG no PDI, análise de vaga) e foram movidas para o
>   escopo entregue. Adicionados objetivos/não-objetivos, requisitos funcionais priorizados
>   com critérios de aceite e requisitos não-funcionais.
> - **v1.0** — Documento de visão e proposta de evolução (preservado no histórico do repositório).

---

## 1. TL;DR (resumo executivo)

O **Mentor de Carreira** é uma aplicação web que ajuda estudantes de Sistemas de Informação a
**entender, escolher e trilhar** caminhos de carreira em tecnologia. Por meio de uma triagem
conversacional com IA (Claude), o sistema extrai um **perfil estruturado**, recomenda uma
**trilha de carreira**, mede o **gap de competências** (radar) e gera artefatos acionáveis —
um **PDI** (Plano de Desenvolvimento Individual) com quadro Kanban e recursos de estudo, e um
**currículo** otimizado para ATS — além de **analisar vagas reais** contra o perfil do aluno.
Tudo com login por aluno e um **painel administrativo** com métricas para a coordenação do
curso. Este PRD descreve o que já está entregue e prioriza a evolução seguinte.

---

## 2. Contexto e problema

"Sistemas de Informação" — e tecnologia em geral — **não é uma carreira**, e sim dezenas de
trilhas (desenvolvimento web, mobile, dados, IA, infraestrutura/cloud, segurança, QA, design
de produto, suporte, gestão…) com rotinas, requisitos e mercados muito diferentes entre si.

O público que mais precisa de orientação — alunos de 1º/2º período — frequentemente **não
conhece as opções que existem**. Perguntar "qual seu objetivo de carreira?" para quem ainda
não sabe que essas opções existem produz respostas vazias e, na ausência de apoio, artefatos
genéricos. O problema central que o produto ataca é: **transformar indefinição em direção** —
primeiro ajudando o aluno a descobrir e comparar trilhas, depois gerando um plano concreto e
acompanhando sua evolução ao longo do curso.

A coordenação do curso, por sua vez, carece de visão agregada sobre **para onde a turma quer
ir** e **onde estão as lacunas de competência mais comuns**, informação útil para ajustar
disciplinas, oficinas e parcerias.

---

## 3. Objetivos e não-objetivos

### 3.1 Objetivos (o que o produto busca)
- **O1.** Reduzir a indefinição de carreira: levar o aluno de "não sei o que quero" a uma
  **trilha de interesse** identificada.
- **O2.** Entregar artefatos **acionáveis e direcionados à trilha** (perfil, PDI com recursos,
  currículo) — não genéricos.
- **O3.** Tornar visível o **gap** entre o que o aluno tem e o que a trilha (ou uma vaga real)
  exige, com caminhos concretos para fechá-lo.
- **O4.** Dar à coordenação **sinais agregados** sobre interesses e lacunas da turma.
- **O5.** Manter **baixo custo e baixo risco** de operação/manutenção (IA econômica, sem
  migrações de banco, código testável).

### 3.2 Não-objetivos (fora de escopo, ao menos por ora)
- **N1.** Não é uma plataforma de vagas/recrutamento nem intermedia contratações.
- **N2.** Não substitui orientação humana (coordenação, mentores) — complementa.
- **N3.** Não promete dados de mercado em tempo real (salários/demanda são referências
  curadas, não um feed ao vivo).
- **N4.** Não é uma rede social; interações aluno↔aluno estão fora do núcleo atual.

---

## 4. Métricas de sucesso (KPIs)

| Métrica | Hoje | Meta |
|---|---|---|
| % de alunos que completam o funil (triagem → perfil → PDI → currículo) | medido em `/admin` | aumentar, sobretudo nos períodos iniciais |
| % de alunos do 1º–3º período com `trilha_interesse` definida | medido (campo existe) | aumentar — proxy direto de "saiu da indefinição" |
| Cards do Kanban movidos para "concluído" por aluno/mês | medido (Kanban) | aumentar — proxy de engajamento contínuo |
| Nº de análises de vaga por aluno | medido (uso) | aumentar — proxy de preparação para o mercado |
| % de alunos que **regeneram** o PDI ao longo do curso | não medido como evolução | aumentar (depende do histórico — ver Roadmap) |

---

## 5. Personas

### 5.1 Aluno indeciso — 1º ao 3º período
Escolheu o curso sem saber bem o que esperar; ainda não sabe se quer "programar", "trabalhar
com dados", "cuidar de infraestrutura". **Precisa**: conhecer as opções em linguagem simples,
com exemplos de dia a dia e requisitos, **antes** de ter que escolher um objetivo.

### 5.2 Aluno em transição para o mercado — 5º ao 8º período
Já tem direção (ex.: "quero back-end"), busca estágio/primeiro emprego. **Precisa**: saber
exatamente o que falta para a trilha, um currículo afiado para ela e leitura de vagas reais.

### 5.3 Coordenação do curso (admin)
**Precisa**: visão agregada de quais trilhas a turma busca e onde estão as lacunas mais
comuns, para embasar ajustes em disciplinas, oficinas e parcerias.

---

## 6. Escopo entregue (as-is)

O produto **já em produção** cobre o ciclo ponta a ponta. Itens marcados ⭐ eram listados como
"proposta" na v1 deste PRD e **já estão entregues**.

| Área | O que faz hoje | Onde no código |
|---|---|---|
| **Autenticação** | Cadastro/login/logout (e-mail+senha bcrypt), sessão por cookie assinado, isolamento de dados por aluno, papel `is_admin` (+ `ADMIN_EMAILS`), headers de segurança | `auth_service`, `_deps.py`, `main.py` |
| **Triagem** | Chat guiado por IA (7 pontos), calibrado por `contexto_aluno` (nome/curso/período), nota de progresso determinística, histórico sanitizado, limites e tratamento de erro (503) | `profile_service`, `prompts/triagem.py`, `claude_client.conversar_triagem` |
| **Perfil** | JSON estruturado via *tool use* forçado; campos ricos (experiências com resultados, formação, certificações, links); editável | `gerar_perfil_estruturado`, `StudentProfile`, `perfil_web` |
| ⭐ **Trilhas de carreira** | Catálogo de **24 trilhas** + **recomendador determinístico por perfil** (atribui `trilha_interesse` ao finalizar a triagem; origem `escolhida`/`recomendada`) | `data/trilhas_carreira.py`, `trilhas_service.recomendar_por_perfil` |
| ⭐ **Radar de competências** | Compara o perfil/PDI com as competências-chave da trilha → possui / em desenvolvimento / lacuna + % de aderência; exibido no perfil e no painel | `trilhas_service.calcular_radar`, `competencias.py` |
| **PDI** | Objetivo, metas curto/médio, competências, ações, cronograma e **quadro Kanban** (drag-drop, editável); **direcionado à trilha** (prioriza lacunas) | `gerar_pdi`, `pdi_service`, `prompts/pdi.py` |
| ⭐ **Recursos de aprendizagem (RAG)** | Para as lacunas do radar, recupera recursos de um **corpus curado** (Naive RAG, matching por sinônimos); usado no PDI e na análise de vaga | `rag_service`, `data/recursos_aprendizado.py` |
| **Currículo** | Texto otimizado para ATS, **direcionado à trilha**, enriquecido pelas ações Kanban concluídas; edição inline, copiar/exportar | `gerar_curriculo`, `curriculo_web` |
| ⭐ **Currículo por Vaga (JD Analyzer)** | Aluno cola uma vaga → IA extrai requisitos → score de aderência, lacunas, recursos + **recomendações de competitividade** (como melhorar, projetos de portfólio sugeridos) + **currículo otimizado com as palavras-chave da vaga**; N por aluno, com ver/editar/excluir | `curriculum_vaga_service`, `analise_vaga_service`, `prompts/recomendacoes_vaga.py` |
| **Edição de artefatos** | Perfil, PDI (incl. Kanban) e currículo totalmente editáveis e persistidos | `*_editar.html`, `atualizar_*`, `editor.js`, `kanban.js` |
| **Painel admin** | KPIs, funil de conclusão, gestão de alunos (excluir/promover), diagnóstico de configuração | `admin_service`, `/admin/*` |
| **Frontend** | Jinja2 + **HTMX** (chat parcial) + **Alpine.js** (toasts/flash, modal de confirmação), design system com tokens de cor/tipografia | `templates/`, `static/` |
| **API REST** | Os mesmos recursos expostos como JSON em `/docs` | `routes/*.py` |

Para os fluxos detalhados, ver os diagramas em [`diagramas/`](../diagramas/) (v1.2): casos de
uso, sequências (cadastro/login, triagem/perfil, PDI/currículo, **análise de vaga**),
arquitetura, **módulo de IA** e esquema do banco.

---

## 7. Requisitos funcionais (priorizados)

Legenda — Status: ✅ entregue · 🔜 proposto (ver Roadmap, §10). Prioridade: P0 (essencial) ·
P1 (importante) · P2 (desejável).

### Épico A — Descoberta de carreira
| ID | História do usuário | Critério de aceite | Status | Pri |
|---|---|---|---|---|
| A1 | Como aluno, quero que o sistema **sugira uma trilha** a partir da minha conversa, para sair da indefinição | Ao finalizar a triagem sem trilha escolhida, `trilha_interesse` é preenchida com `origem=recomendada` | ✅ | P0 |
| A2 | Como aluno, quero **explorar o catálogo de trilhas** (dia a dia, competências, mercado) mesmo sem ter feito a triagem | Página navegável lista as trilhas com seus campos; acessível sem perfil | 🔜 | P0 |
| A3 | Como aluno indeciso, quero responder a um **quiz curto** que rankeia trilhas compatíveis | Quiz determinístico retorna ranking + justificativa | 🔜 | P1 |

### Épico B — Perfil e triagem
| ID | História | Critério de aceite | Status | Pri |
|---|---|---|---|---|
| B1 | Como aluno, quero conversar com um mentor que **lembra o contexto** e não repete perguntas | Mentor usa nome/curso/período e a nota de progresso dos 7 pontos | ✅ | P0 |
| B2 | Como aluno, quero **revisar e editar** meu perfil gerado | Formulário reconstrói o JSON completo e persiste via upsert | ✅ | P0 |

### Épico C — Plano de desenvolvimento (PDI)
| ID | História | Critério de aceite | Status | Pri |
|---|---|---|---|---|
| C1 | Como aluno, quero um PDI **direcionado à minha trilha**, priorizando minhas lacunas | `gerar_pdi` recebe competências-chave + lacunas da trilha no contexto | ✅ | P0 |
| C2 | Como aluno, quero **recursos concretos** (curso/artigo/vídeo) para cada lacuna | PDI exibe recursos do corpus RAG para as lacunas do radar | ✅ | P0 |
| C3 | Como aluno, quero acompanhar minhas ações em um **quadro Kanban** | Cards movem entre A Fazer/Em Progresso/Concluído; persistido | ✅ | P0 |

### Épico D — Currículo e mercado
| ID | História | Critério de aceite | Status | Pri |
|---|---|---|---|---|
| D1 | Como aluno, quero um currículo **ATS** alinhado à trilha | `gerar_curriculo` enfatiza palavras-chave da trilha | ✅ | P0 |
| D2 | Como aluno, quero **analisar uma vaga real** e ver minha aderência, lacunas e **como ficar mais competitivo** (incl. projetos de portfólio sugeridos) | Análise retorna score, categorias, recursos e recomendações estruturadas | ✅ | P0 |
| D3 | Como aluno, quero **currículos direcionados por vaga**, salvos e editáveis (N por aluno) | Cada vaga analisada gera um currículo com as keywords dela; lista com ver/editar/excluir | ✅ | P1 |
| D4 | Como aluno, quero currículo **em inglês** e **export em PDF estilizado** | Versão EN opcional; PDF além do `window.print()` | 🔜 | P2 |

### Épico E — Coordenação (admin)
| ID | História | Critério de aceite | Status | Pri |
|---|---|---|---|---|
| E1 | Como admin, quero **KPIs e funil** de conclusão da turma | Painel exibe métricas e diagnóstico | ✅ | P0 |
| E2 | Como admin, quero **gerir alunos** (excluir, promover a admin) | Ações disponíveis e protegidas por guard | ✅ | P1 |
| E3 | Como admin, quero ver **quais trilhas a turma busca** e as **lacunas comuns** | Agregação de `trilha_interesse` + radar por período | 🔜 | P1 |

### Épico F — Acompanhamento contínuo
| ID | História | Critério de aceite | Status | Pri |
|---|---|---|---|---|
| F1 | Como aluno, quero ver minha **evolução** ao longo do curso (antes × depois) | Histórico de PDI/perfil com linha do tempo | 🔜 | P1 |
| F2 | Como aluno, quero **preparo para entrevista** após o currículo | Simulador de entrevista (chat de IA) calibrado pela trilha | 🔜 | P2 |

---

## 8. Requisitos não-funcionais

- **Segurança**: senhas com bcrypt; sessão assinada (`itsdangerous`); isolamento total por
  aluno (guards em `_deps.py`, 401/403); papel admin revalidado no banco; headers
  `X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy`; recusa de subir em produção
  com `SECRET_KEY` padrão.
- **Robustez da IA**: cliente único com `timeout=60s`; retry com backoff (tenacity) para erros
  transitórios; falhas da API viram **HTTP 503** (distinto de 500); histórico de chat
  sanitizado; limite de mensagens.
- **Privacidade / LGPD**: dados pessoais e de carreira ficam restritos ao próprio aluno;
  qualquer expansão (portfólio público, mentoria) exige **opt-in explícito** e controle do que
  é exibido.
- **Performance / custo**: IA econômica por padrão (`claude-haiku-4-5`), com modelos separados
  por operação (`CLAUDE_MODEL_ANALISE`/`_GERACAO`); recomendador, radar e RAG são
  **determinísticos** (zero custo de API).
- **Manutenibilidade**: evolução por **chaves JSON aditivas** + backfill na leitura — sem
  migração de schema (preserva a decisão de não usar Alembic); arquitetura em camadas;
  cobertura de testes com IA mockada.
- **Acessibilidade / UX**: design system com contraste AA, tipografia legível, foco visível,
  estados de carregamento e feedback por toasts.

---

## 9. Visão da solução e fluxos

```
DESCOBRIR  ───────────►  COMPARAR  ───────────►  AGIR  ───────────►  EVOLUIR
Triagem +               Radar de               PDI direcionado     (Roadmap)
trilha recomendada      competências           + recursos (RAG)    histórico,
(catálogo/quiz: 🔜)     vs. trilha             Currículo ATS       reengajamento
                        Análise de vaga        por trilha
```

Os fluxos estão formalizados nos diagramas (v1.2) em [`diagramas/`](../diagramas/):
**casos de uso**, **sequências** (cadastro/login, triagem/perfil, PDI/currículo, análise de
vaga), **arquitetura de componentes**, **módulo de IA** (IA × determinístico) e **esquema do
banco**.

---

## 10. Roadmap (proposto)

Apenas o que **ainda não existe**. Cada item assume o núcleo já entregue (§6) como base.

### Fase 1 — Fechar o ciclo "descobrir"
- **R1 (P0)** — **Explorador de trilhas navegável**: página dedicada (ex.: `/trilhas`,
  acessível **sem** triagem) exibindo o catálogo já existente (dia a dia, competências,
  disciplinas, mercado, trilhas relacionadas). *Hoje o catálogo e o recomendador existem, mas
  não há UI de exploração.*
- **R2 (P1)** — **Quiz de recomendação**: questionário curto (preferências) que rankeia
  trilhas; v1 determinístico, v2 com justificativa escrita por IA.

### Fase 2 — Aprofundar a ação e o mercado
- **R3 (P2)** — **Currículo multi-idioma/PDF**: versão em inglês e **export em PDF
  estilizado** (hoje é `window.print()` sobre texto). *As variações por vaga já foram
  entregues (D3 ✅, tabela `curriculum_vagas`) — resta idioma e formato.*
- **R4 (P1)** — **Painel da coordenação orientado a trilhas**: agrega `trilha_interesse` e
  lacunas do radar por período → sinais de ação para a coordenação.

### Fase 3 — Acompanhamento contínuo
- **R5 (P1)** — **Linha do tempo / histórico**: snapshots de perfil/PDI a cada regeneração
  (tabelas novas `*_history`, cobertas por `create_all`, sem Alembic) → "antes × depois".
- **R6 (P2)** — **Gamificação leve**: contadores de progresso pessoal (ações concluídas no
  mês, sequência de semanas ativas), sem rankings públicos.

### Fase 4 — Diferenciação
- **R7 (P2)** — **Simulador de entrevistas**: 6ª operação de IA (`simular_entrevista`),
  calibrada pela trilha e pelo PDI, reaproveitando a infraestrutura de robustez do chat.
- **R8 (P2)** — **Portfólio público compartilhável** (`/p/{slug}`), com opt-in e controle de
  visibilidade.
- **R9 (P2)** — **Notificações / reengajamento** (e-mail por semestre) e **mentoria entre
  pares** (alunos avançados como referência por trilha).

---

## 11. Impacto no modelo de dados (resumo)

| Item do roadmap | Mudança necessária |
|---|---|
| Explorador de trilhas / quiz (R1, R2) | Reusa `data/trilhas_carreira.py` + `trilhas_service` — **sem mudança no banco** |
| Currículo multi-idioma/PDF (R3) | Reusa `curriculum_vagas`/`Curriculum` — **sem mudança no banco** |
| Painel coordenação por trilha (R4) | Leitura agregada do que já existe — **sem mudança no banco** |
| Histórico / linha do tempo (R5) | **Tabelas novas** (`*_history`) — cobertas por `create_all`, sem Alembic |
| Gamificação (R6) | Chave aditiva em `pdi_json`/`profile_json` — **sem migração** |
| Simulador de entrevista (R7) | Reusa `TriageMessage` ou nova tabela de sessão de entrevista |
| Portfólio (R8) | Campo (`slug`, visibilidade) em `profile_json` — **sem migração** |
| Notificações / mentoria (R9) | Dependência de e-mail + job; campo aditivo "disponível como referência" |

> Nenhum item das Fases 1–2 exige Alembic — preservando, por mais tempo, a decisão
> arquitetural atual (ver [`CLAUDE.md`](../CLAUDE.md)).

---

## 12. Riscos, premissas e questões em aberto

**Riscos**
- **Curadoria de conteúdo é trabalho contínuo**: catálogo de trilhas e corpus de recursos
  ficam desatualizados sem manutenção — vale um campo "última revisão" por trilha.
- **Custo de API**: simulador de entrevista (R7) e quiz v2 (R2) adicionam chamadas ao Claude —
  controlar via `CLAUDE_MODEL_ANALISE`/`_GERACAO`.
- **LGPD**: qualquer dado pessoal novo exige opt-in explícito (portfólio, mentoria).

**Premissas**
- O catálogo de trilhas reflete o mercado-alvo (Brasil, início de carreira em TI).
- A IA econômica (`claude-haiku-4-5`) é suficiente para a qualidade desejada nas operações
  atuais; operações mais sensíveis podem usar `CLAUDE_MODEL_GERACAO`.

**Questões em aberto**
- O recomendador deve continuar **automático** (por perfil) ou passar a oferecer também a
  escolha explícita via Explorador (R1)? (Recomendado: ambos.)
- Vale exibir dados de mercado (salário/demanda) na UI das trilhas, dado o risco de
  desatualização? (Sugestão: exibir como referência datada.)

---

## 13. Referências

**Modelos de PRD usados nesta reestruturação**
- [Atlassian — What is a Product Requirements Document?](https://www.atlassian.com/agile/product-management/requirements)
- [Product School — The Only PRD Template You Need](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd)
- [Aha! — What to include in a good PRD](https://www.aha.io/roadmapping/guide/requirements-management/what-is-a-good-product-requirements-document-template)

**Pesquisa de apoio (taxonomia de trilhas e mercado no Brasil)**
- [roadmap.sh — Developer Roadmaps](https://roadmap.sh/)
- [Salário de Programador Júnior — Glassdoor Brasil](https://www.glassdoor.com.br/Sal%C3%A1rios/programador-junior-sal%C3%A1rio-SRCH_KO0,18.htm)
- [Salário de Estagiário de TI — Indeed Brasil](https://br.indeed.com/career/estagi%C3%A1rio-de-ti/salaries)
