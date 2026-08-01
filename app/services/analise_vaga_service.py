"""Analisa a compatibilidade do perfil do aluno com uma descrição de vaga (JD Analyzer)."""

import logging

from app.services import claude_client, pdi_service, profile_service, rag_service
from app.services.competencias import presente

logger = logging.getLogger(__name__)


def _nomes_da_stack(itens) -> list[str]:
    """Extrai os nomes das tecnologias da stack do perfil.

    A stack passou a guardar `[{"nome", "nivel"}]`; perfis antigos ainda podem trazer
    `[str]`. Aceita os dois formatos para o matching de competências não quebrar.
    """
    nomes: list[str] = []
    for item in itens or []:
        nome = item.get("nome") if isinstance(item, dict) else item
        nome = str(nome or "").strip()
        if nome:
            nomes.append(nome)
    return nomes


def analisar(db, student_id: int, jd_text: str) -> dict:
    """Extrai requisitos da vaga via Claude e compara com o perfil do aluno.

    Retorna score de aderência, categorização de competências (possui / em_desenvolvimento /
    lacuna) e recursos de estudo para as lacunas (RAG).

    Levanta ValueError se o aluno não tiver perfil gerado.
    """
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        raise ValueError("Perfil não encontrado. Conclua a triagem primeiro.")

    pdi = pdi_service.obter_pdi(db, student_id)
    pj = perfil.profile_json

    stack = pj.get("stack_tecnica") or {}
    pool_tecnico = (
        _nomes_da_stack(stack.get("linguagens"))
        + _nomes_da_stack(stack.get("frameworks_ferramentas"))
        + [t for exp in pj.get("experiencias") or [] for t in exp.get("tecnologias") or []]
    )
    pool_soft = list(pj.get("soft_skills") or [])
    pool_pdi = (
        [c.get("nome", "") for c in pdi.pdi_json.get("competencias_a_desenvolver") or []]
        if pdi else []
    )

    logger.info("Analisando vaga para student_id=%d (%d chars)", student_id, len(jd_text))
    requisitos = claude_client.extrair_requisitos_vaga(jd_text)

    tec: dict[str, list[str]] = {"possui": [], "em_desenvolvimento": [], "lacuna": []}
    for comp in requisitos.get("competencias_tecnicas") or []:
        if presente(comp, pool_tecnico):
            tec["possui"].append(comp)
        elif presente(comp, pool_pdi):
            tec["em_desenvolvimento"].append(comp)
        else:
            tec["lacuna"].append(comp)

    soft: dict[str, list[str]] = {"possui": [], "lacuna": []}
    for s in requisitos.get("soft_skills") or []:
        (soft["possui"] if presente(s, pool_soft) else soft["lacuna"]).append(s)

    todas_lacunas = tec["lacuna"] + soft["lacuna"]
    total = len(requisitos.get("competencias_tecnicas") or []) + len(requisitos.get("soft_skills") or [])
    n_possui = len(tec["possui"]) + len(soft["possui"])
    score = round(100 * n_possui / total) if total > 0 else 0

    return {
        "cargo": requisitos.get("cargo", ""),
        "nivel": requisitos.get("nivel", "nao_identificado"),
        "modalidade": requisitos.get("modalidade", "nao_informado"),
        "localizacao": requisitos.get("localizacao", ""),
        "score": score,
        "tecnicas": tec,
        "soft_skills": soft,
        "diferenciais": requisitos.get("diferenciais") or [],
        "recursos_lacunas": rag_service.recuperar_recursos(todas_lacunas, top_k_por_competencia=2),
    }
