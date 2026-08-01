# Revisão de código e qualidade

Avaliação do código do **Mentor de Carreira** (193 testes passando). Escopo: arquitetura,
qualidade, convenções e cobertura de autorização. O anexo de **segurança** ao final
registra o que foi endurecido e o que ainda fica para uma próxima etapa.

---

## Resumo

> **Qualidade geral: alta.** Arquitetura limpa em camadas, tipagem e docstrings completos,
> sem código morto, autorização aplicada em todas as rotas com `{student_id}`. Não há
> refatoração necessária no `app/`.

---

## Pontos fortes

### Arquitetura em 3 camadas, bem separada
- **Rotas** (`app/routes/`) cuidam de HTTP (validação, status, templates).
- **Serviços** (`app/services/`) concentram a lógica de negócio e a persistência.
- **`claude_client.py`** é o único ponto de contato com a Anthropic (singleton, retry com
  `tenacity`, *tool use* forçado para saídas estruturadas).
- A sessão do banco é injetada via `Depends(get_db)`, deixando as dependências explícitas.

### Autorização cobrindo 100% das rotas sensíveis
Todas as rotas com `{student_id}` passam por `verificar_proprio_aluno` (JSON) ou
`verificar_proprio_aluno_html` (HTML): **401** sem sessão, **403** se for outro aluno. Um
`id` inexistente cai no mesmo **403**, evitando enumeração. Rotas públicas (`/health`,
`/login`, `/alunos/novo`, cadastro) estão corretamente sem guarda.

### Tipagem e documentação
- Type hints completos em rotas e serviços (inclusive `| None`).
- Modelos usam o estilo moderno `Mapped[...]` do SQLAlchemy 2.0.
- Docstrings presentes e em português, coerentes com o restante do código.

### Validação de entrada
Schemas Pydantic com limites claros (`nome` 1–200, `senha` 8–128, `periodo` 1–12,
`mensagem` 1–5000) e `EmailStr` para e-mail. O FastAPI retorna 422 automaticamente.

### Convenções consistentes (conforme `CLAUDE.md`)
Rotas JSON em inglês, rotas HTML em português, serviços com verbos em português, funções
privadas com prefixo `_`. Logging por módulo (`logging.getLogger(__name__)`) com config
central em `main.py` (libs de terceiros em WARNING).

### Sem código morto / TODO / FIXME
A varredura não encontrou TODO/FIXME nem funções órfãs. O `upsert_registro` em `_base.py`
elimina duplicação entre os serviços de perfil, PDI e currículo.

### Tratamento de erros
Handler genérico de `Exception` retorna **500** com mensagem amigável e registra o traceback
nos logs (não vaza detalhes na resposta). Mensagem de login genérica
("E-mail ou senha inválidos") não distingue e-mail inexistente de senha errada.

---

## Observações menores (opcionais, não bloqueantes)

- `pdi_service.obter_pdi` faz `from sqlalchemy import select` dentro da função; os demais
  serviços importam no topo do módulo. Padronizar é cosmético.
- Sem Alembic: o esquema é criado via `create_all`. Para um banco de produção com evolução
  de schema, vale adicionar migrações no futuro (já documentado no `CLAUDE.md`).

---

## Anexo — Segurança

### Já endurecido

1. **Flags do cookie de sessão.** O `SessionMiddleware` agora recebe `https_only`
   (`SESSION_HTTPS_ONLY`), que vira `true` automaticamente em `APP_ENV=production`.
   Arquivo: `app/main.py` + `app/config.py`.
2. **`SECRET_KEY` padrão inseguro.** Em `APP_ENV=production`, a aplicação **recusa subir**
   se a `SECRET_KEY` ainda for o valor padrão. Arquivo: `app/config.py` (`model_validator`).
3. **Cabeçalhos de segurança.** Middleware adiciona `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY` e `Referrer-Policy: same-origin` a todas as respostas.
   Arquivo: `app/main.py`.
4. **E-mail case-insensitive.** `student_service.normalizar_email` evita contas duplicadas
   por capitalização e torna o login tolerante a maiúsculas/minúsculas.

### Ainda em aberto (próxima etapa)

1. **Enumeração de e-mail no cadastro.** As mensagens "Já existe um aluno com este e-mail"
   (`app/routes/students.py` e `app/routes/web.py`) ainda revelam quais e-mails já existem.
   Foi mantido por usabilidade do formulário; uma mensagem genérica reduziria o vetor.
2. **Rate limiting / proteção contra brute force** no login — não há limite de tentativas.
3. **CSRF** nos formulários HTML — hoje a proteção depende de `same_site="lax"`; um token
   CSRF seria mais robusto.
4. **Truncamento bcrypt (72 bytes).** Senhas acima de 72 bytes são truncadas pelo bcrypt;
   o `max_length=128` do schema poderia ser reduzido para 72 para deixar isso explícito.
