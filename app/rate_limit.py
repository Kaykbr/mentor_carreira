"""Limitação de requisições por sessão (aluno) ou IP (rotas anônimas).

Objetivo: impedir que um bot (ou um loop acidental) crie contas em massa e consuma a cota
da API Anthropic, SEM travar a turma inteira quando os alunos compartilham NAT (wifi da
faculdade). A chave de limitação é escolhida em runtime:

- Rotas autenticadas (triagem, gerações): `session:{student_id}` — cada aluno tem sua cota,
  independente do IP compartilhado.
- Rotas anônimas (cadastro, login): `get_remote_address` — protege contra bot fora da
  sessão.

Desligável por configuração (`RATE_LIMIT_ATIVO=false`) para não interferir nos testes nem
no desenvolvimento local.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _chave_sessao_ou_ip(request: Request) -> str:
    """Prefere `student_id` da sessão; cai para IP quando o aluno não está logado.

    Assim, um cadastro no lab (todos no mesmo NAT) usa IP, mas uma vez logado cada
    aluno tem sua cota individual — não trava mais os colegas.
    """
    try:
        sid = request.session.get("student_id") if hasattr(request, "session") else None
    except Exception:
        sid = None
    if sid:
        return f"sess:{sid}"
    return get_remote_address(request)


# `key_func` global usa o helper acima. Atrás do proxy do Render, o IP real chega em
# X-Forwarded-For — uvicorn com --proxy-headers resolve isso antes de chegar aqui.
limiter = Limiter(
    key_func=_chave_sessao_ou_ip,
    enabled=get_settings().rate_limit_ativo,
    default_limits=[],
)

# Limites por operação sensível. Strings no formato do slowapi ("N/período").
# CADASTRO/LOGIN sempre por IP (sem sessão ainda). Números folgados para turma em NAT.
LIMITE_CADASTRO = "30/hour"
LIMITE_LOGIN = "60/hour"
# TRIAGEM/GERACAO ficam por sessão (aluno). Uma triagem real tem ~10-15 mensagens e o
# aluno mal chega a 1 geração de cada tipo — os limites abaixo são folgadíssimos.
LIMITE_TRIAGEM = "60/hour"
LIMITE_GERACAO = "20/hour"
