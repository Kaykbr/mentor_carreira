"""Correspondência (matching) de competências — base compartilhada da Análise de Vaga
e do RAG.

Centraliza `_normalizar`/`_presente` usados pela análise de vaga e pelo
`rag_service`. Mantém o comportamento original (substring bidirecional
case-insensitive) e adiciona expansão por sinônimos (`app/data/sinonimos.py`), de modo que
"JS" passe a casar com "JavaScript" e "nodejs" com "Node.js".

É 100% determinístico, sem dependências de ML. Se um dia o projeto adotar embeddings,
basta reimplementar `corresponder`/`pontuar_match` aqui — os chamadores não mudam.
"""

from app.data.sinonimos import SINONIMOS


def normalizar(texto: str) -> str:
    """Minúsculas + sem espaços nas pontas (forma canônica para comparação)."""
    return (texto or "").strip().lower()


def _variantes(termo_norm: str) -> set[str]:
    """Retorna `termo_norm` somado às variantes do seu grupo de sinônimos, se houver.

    Procura o termo tanto como chave canônica quanto como variante (busca bidirecional no
    mapa). Termos sem sinônimos retornam apenas o próprio termo.
    """
    variantes = {termo_norm}
    for canonico, sins in SINONIMOS.items():
        grupo = {canonico, *(s.lower() for s in sins)}
        if termo_norm in grupo:
            variantes |= grupo
    return variantes


def _substring_em_algum(termo: str, candidatos: set[str]) -> bool:
    return any(termo in c or c in termo for c in candidatos if c)


def corresponder(a: str, b: str) -> bool:
    """True se `a` e `b` se referem à mesma competência.

    Combina substring bidirecional (comportamento histórico) com equivalência por
    sinônimos. Ex.: corresponder("React.js", "react") e corresponder("JS", "JavaScript")
    retornam True.
    """
    na, nb = normalizar(a), normalizar(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    # Equivalência via sinônimos: alguma variante de um casa (por substring) com o outro.
    if _substring_em_algum(nb, _variantes(na)):
        return True
    if _substring_em_algum(na, _variantes(nb)):
        return True
    return False


def presente(competencia: str, candidatos: list[str]) -> bool:
    """True se `competencia` corresponde a algum item de `candidatos` (lista do aluno)."""
    return any(corresponder(competencia, candidato) for candidato in candidatos)


def pontuar_match(competencia: str, chave: str) -> int:
    """Pontua a aderência entre uma competência e uma chave do corpus (maior = melhor).

    4 = igualdade exata; 3 = equivalência por sinônimo exato; 2 = substring direta;
    1 = substring via sinônimo; 0 = sem correspondência. Usado pelo `rag_service` para
    escolher a chave mais relevante quando uma competência casa com várias.
    """
    nc, nk = normalizar(competencia), normalizar(chave)
    if not nc or not nk:
        return 0
    if nc == nk:
        return 4
    var_c, var_k = _variantes(nc), _variantes(nk)
    if nk in var_c or nc in var_k:
        return 3
    if nc in nk or nk in nc:
        return 2
    if _substring_em_algum(nk, var_c) or _substring_em_algum(nc, var_k):
        return 1
    return 0
