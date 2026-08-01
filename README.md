# Mentor de Carreira para Estudantes de Sistemas de Informação

Sistema de mentoria de carreira em TI baseado em IA. Conduz uma **triagem conversacional**
com o aluno, extrai um **perfil estruturado**, recomenda uma **trilha de carreira** (com
**radar de competências**) e gera um **Plano de Desenvolvimento Individual (PDI)** — com
quadro Kanban e recursos de estudo — e um **currículo** otimizado para ATS, além de
**analisar vagas reais** contra o perfil. Tudo com login por aluno, em que cada um só acessa
os próprios dados, e um **painel administrativo** para a coordenação.

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Cadastro + login por aluno | E-mail/senha (bcrypt), sessão por cookie assinado; isolamento de dados |
| Triagem conversacional | Chat guiado pelo Claude, histórico salvo no banco |
| Perfil estruturado | Extraído via *tool use* ao final da triagem; editável |
| Trilhas + radar de competências | Trilha de carreira recomendada pelo perfil; radar mostra o que o aluno tem e o que falta |
| PDI gerado por IA | Plano com cronograma, quadro Kanban e recursos de estudo (RAG), direcionado à trilha |
| Currículo ATS | Texto otimizado para rastreadores de candidatos, alinhado à trilha |
| Análise de vaga (JD) | Cola uma vaga e vê aderência, lacunas e recursos de estudo |
| Painel de administração | KPIs, funil e gráficos, gestão de alunos e diagnóstico automático em `/admin` |
| Web + API REST | Frontend Jinja2 e os mesmos recursos expostos como JSON (`/docs`) |

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · SQLite · Pydantic v2 · Anthropic Claude SDK ·
Tenacity · Jinja2 · Passlib/bcrypt · itsdangerous · Pytest (193 testes).

## Quick start

```bash
git clone <url-do-repositorio>
cd Projeto-TCC
make install                 # cria o venv e instala as dependências
cp .env.example .env         # preencha ANTHROPIC_API_KEY (Windows: copy)
make run                     # sobe o servidor em http://localhost:8000
```

Depois acesse <http://localhost:8000/login>, clique em **Cadastrar** e siga o fluxo
**Triagem → Perfil → PDI → Currículo**. Sem `make`, veja os comandos manuais no guia de
instalação.

> Os testes (`make test`, **193 passando**) não exigem chave da Anthropic — o Claude é
> mockado.

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [`docs/INSTALACAO.md`](docs/INSTALACAO.md) | Guia completo: pré-requisitos, o que cada dependência faz, instalação passo a passo, configuração, banco, execução, primeiro uso, testes, endpoints e *troubleshooting* |
| [`docs/MODULO_IA.md`](docs/MODULO_IA.md) | Como funciona o módulo de IA (5 operações: triagem, perfil, PDI, currículo, análise de vaga) + camada determinística (trilhas, radar, RAG): técnicas, fluxo e robustez |
| [`docs/REVISAO.md`](docs/REVISAO.md) | Revisão de código/qualidade e anexo de segurança |
| [`docs/PRD.md`](docs/PRD.md) | PRD (v2.0): visão de produto, personas, escopo entregue e roadmap priorizado |
| [`CLAUDE.md`](CLAUDE.md) | Guia arquitetural (camadas, autenticação, decisões de design, convenções, testes) |
| [`diagramas/`](diagramas/) | Diagramas UML (casos de uso, sequência), esquema do banco (ER), arquitetura e módulo de IA — Mermaid + PNG/SVG (v1.2) |

## Estrutura do projeto

```
app/        Aplicação (main, config, database, models, schemas, routes/, services/, data/, prompts/, templates/, static/)
tests/      Suíte de testes (pytest)
docs/       Documentação (instalação, módulo de IA, PRD, revisão)
diagramas/  Diagramas (.mmd + .png/.svg) — v1.2, com histórico em v1.1/

```

A descrição detalhada de cada módulo está no [`CLAUDE.md`](CLAUDE.md).

## Fluxo principal

```
Cadastro/Login → Triagem (chat com Claude) → Finalizar (gera perfil)
              → Gerar PDI → Gerar Currículo → Painel do aluno
```

Veja os diagramas de sequência em [`diagramas/`](diagramas/) para o detalhe de cada etapa.
