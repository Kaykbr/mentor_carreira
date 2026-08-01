"""Prompts de sistema e ferramentas (tool use) das operações de IA.

Separa o "o que pedir ao Claude" (puro dado: textos e schemas) do "como chamar a API"
(`app/services/claude_client.py`). Cada operação tem seu módulo coeso, facilitando ajustar
prompts e schemas sem navegar a lógica de cliente/retry.
"""

from app.prompts.analise_curriculo import FERRAMENTA_ANALISE_CURRICULO, PROMPT_ANALISE_CURRICULO
from app.prompts.analise_vaga import FERRAMENTA_EXTRAIR_VAGA, PROMPT_EXTRAIR_VAGA
from app.prompts.curriculo import PROMPT_GERAR_CURRICULO
from app.prompts.pdi import FERRAMENTA_PDI, PROMPT_GERAR_PDI
from app.prompts.perfil import FERRAMENTA_PERFIL, PROMPT_GERAR_PERFIL
from app.prompts.recomendacoes_vaga import (
    FERRAMENTA_RECOMENDACOES_VAGA,
    PROMPT_RECOMENDACOES_VAGA,
)
from app.prompts.triagem import PROMPT_SISTEMA_TRIAGEM, montar_prompt_triagem

__all__ = [
    "PROMPT_SISTEMA_TRIAGEM",
    "montar_prompt_triagem",
    "PROMPT_GERAR_PERFIL",
    "FERRAMENTA_PERFIL",
    "PROMPT_GERAR_PDI",
    "FERRAMENTA_PDI",
    "PROMPT_GERAR_CURRICULO",
    "PROMPT_EXTRAIR_VAGA",
    "FERRAMENTA_EXTRAIR_VAGA",
    "PROMPT_RECOMENDACOES_VAGA",
    "FERRAMENTA_RECOMENDACOES_VAGA",
    "PROMPT_ANALISE_CURRICULO",
    "FERRAMENTA_ANALISE_CURRICULO",
]
