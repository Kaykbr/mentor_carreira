"""Recuperação de recursos de aprendizado para lacunas de competência (Naive RAG).

Para cada competência (tipicamente uma lacuna identificada na Análise de Vaga), encontra
as chaves mais relevantes do corpus `RECURSOS_POR_COMPETENCIA` e retorna os recursos.

O matching usa `app/services/competencias.py` (substring bidirecional + sinônimos),
o mesmo módulo que a Análise de Vaga usa — assim "JS" casa com
"JavaScript" e "nodejs" com "Node.js". Em vez de parar no primeiro acerto, pontua todas
as chaves candidatas (`pontuar_match`) e usa as mais aderentes primeiro, resolvendo o
caso em que uma competência casa com várias chaves. Sem dependências de ML — o corpus é
estático e pequeno (~80 chaves).
"""

import logging

from app.data.recursos_aprendizado import RECURSOS_POR_COMPETENCIA
from app.services.competencias import pontuar_match

logger = logging.getLogger(__name__)


def _chaves_ordenadas_por_relevancia(competencia: str) -> list[str]:
    """Retorna as chaves do corpus que casam com `competencia`, da mais à menos aderente."""
    pontuadas = (
        (chave, pontuar_match(competencia, chave)) for chave in RECURSOS_POR_COMPETENCIA
    )
    casadas = [(chave, pontos) for chave, pontos in pontuadas if pontos > 0]
    casadas.sort(key=lambda item: item[1], reverse=True)
    return [chave for chave, _ in casadas]


def recuperar_recursos(competencias: list[str], top_k_por_competencia: int = 2) -> list[dict]:
    """Retorna recursos de aprendizado para as competências fornecidas.

    Para cada competência, percorre as chaves do corpus em ordem de relevância e coleta
    até `top_k_por_competencia` recursos, sem repetir URLs. Retorna lista vazia se nenhuma
    competência tiver correspondência no corpus.
    """
    if not competencias:
        return []

    resultados: list[dict] = []
    vistos: set[str] = set()

    for comp in competencias:
        if not comp or not comp.strip():
            continue

        adicionados = 0
        for chave in _chaves_ordenadas_por_relevancia(comp):
            if adicionados >= top_k_por_competencia:
                break
            for recurso in RECURSOS_POR_COMPETENCIA[chave]:
                if adicionados >= top_k_por_competencia:
                    break
                if recurso["url"] not in vistos:
                    vistos.add(recurso["url"])
                    resultados.append({**recurso, "competencia": comp})
                    adicionados += 1

    logger.debug(
        "RAG: %d competências → %d recursos encontrados (corpus=%d entradas)",
        len(competencias),
        len(resultados),
        len(RECURSOS_POR_COMPETENCIA),
    )
    return resultados
