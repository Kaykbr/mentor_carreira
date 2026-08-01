"""Limitação de requisições por IP (proteção do link público durante a coleta).

Objetivo: impedir que um bot (ou um loop acidental) crie contas em massa e consuma a cota
da API Anthropic. Os limites são folgados o bastante para não atrapalhar o uso legítimo de
um aluno real — a triagem, por exemplo, permite ~1 mensagem a cada 2 minutos por hora.

Desligável por configuração (`RATE_LIMIT_ATIVO=false`) para não interferir nos testes nem
no desenvolvimento local.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

# `key_func` usa o IP de origem. Atrás do proxy do Render, o cliente real vem em
# X-Forwarded-For — uvicorn com --proxy-headers resolve isso antes de chegar aqui.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=get_settings().rate_limit_ativo,
    default_limits=[],
)

# Limites por operação sensível. Strings no formato do slowapi ("N/período").
LIMITE_CADASTRO = "10/hour"     # criação de conta por IP (turma em laboratório partilha IP)
LIMITE_LOGIN = "30/hour"        # tentativas de login por IP
LIMITE_TRIAGEM = "60/hour"      # mensagens no chat (uso real fica bem abaixo disso)
LIMITE_GERACAO = "40/hour"      # gerar/regenerar perfil, PDI, currículo e análises
