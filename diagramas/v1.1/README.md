# Diagramas — Snapshot v1.1 (histórico)

> ⚠️ **Versão histórica, mantida apenas como referência.** A versão corrente é a **v1.2**,
> na pasta acima ([`../`](../)).

Este snapshot retrata o sistema **antes** das funcionalidades que cresceram depois:

- não há **painel administrativo** (`is_admin`, `/admin/*`);
- não há **trilhas de carreira**, **radar de competências** nem **recomendador**;
- não há **Análise de Vaga** (5ª operação de IA) nem **RAG** (recursos de aprendizado);
- as rotas HTML ainda estão concentradas em um único `web.py` (depois divididas em
  `paginas_web`, `perfil_web`, `pdi_web`, `curriculo_web`, `analise_vaga_web`);
- o modelo de IA citado é `claude-sonnet-4-6` (o default atual é `claude-haiku-4-5`).

Para o estado atual do sistema, use os diagramas **v1.2** em [`../`](../) e o
[`../README.md`](../README.md) (que traz o CHANGELOG v1.1 → v1.2).
