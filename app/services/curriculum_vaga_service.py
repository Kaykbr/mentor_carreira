"""Currículos direcionados por vaga: análise + recomendações + currículo otimizado.

Orquestra três operações a partir da descrição de uma vaga colada pelo aluno:
1. `analise_vaga_service.analisar` — extrai requisitos (IA) e calcula aderência
   (matching determinístico + recursos RAG);
2. `claude_client.gerar_recomendacoes_vaga` — como melhorar e projetos de portfólio;
3. `claude_client.gerar_curriculo` com `contexto["vaga"]` — currículo com as
   palavras-chave da vaga.

Diferente dos demais artefatos (1 por aluno via `upsert_registro`), aqui são N
registros por aluno — CRUD plano com posse verificada por (`id`, `student_id`).
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CurriculumVaga
from app.services import analise_vaga_service, claude_client, curriculum_service, pdi_service, profile_service

logger = logging.getLogger(__name__)


def gerar(db: Session, student_id: int, jd_text: str) -> CurriculumVaga:
    """Analisa a vaga, gera recomendações e o currículo direcionado, e persiste tudo.

    Levanta ValueError se o aluno não tiver perfil gerado. Persistência única ao
    final — se qualquer chamada de IA falhar, nada é gravado.
    """
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        raise ValueError("Perfil não encontrado. Conclua a triagem primeiro.")

    logger.info("Gerando currículo por vaga para student_id=%d (%d chars)", student_id, len(jd_text))

    # 1) Análise de aderência (IA extrai requisitos + matching determinístico + RAG)
    analise = analise_vaga_service.analisar(db, student_id, jd_text)

    # 2) Recomendações de competitividade (como melhorar, projetos de portfólio)
    recomendacoes = claude_client.gerar_recomendacoes_vaga(perfil.profile_json, analise)

    # 3) Currículo direcionado: contexto padrão + bloco `vaga` (estrutura categorizada,
    #    preservando o sinal possui/em_desenvolvimento/lacuna — anti-alucinação no prompt)
    pdi = pdi_service.obter_pdi(db, student_id)
    contexto = curriculum_service.montar_contexto_curriculo(db, student_id, perfil)
    contexto["vaga"] = {
        "cargo": analise["cargo"],
        "nivel": analise["nivel"],
        "modalidade": analise["modalidade"],
        "tecnicas": analise["tecnicas"],
        "soft_skills": analise["soft_skills"],
        "diferenciais": analise["diferenciais"],
    }
    texto = claude_client.gerar_curriculo(
        perfil.profile_json,
        pdi.pdi_json if pdi is not None else None,
        contexto_aluno=contexto,
    )

    registro = CurriculumVaga(
        student_id=student_id,
        cargo=(analise["cargo"] or "Vaga sem título")[:255],
        jd_text=jd_text,
        analise_json={**analise, "recomendacoes": recomendacoes},
        curriculum_text=texto,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    logger.info("Currículo por vaga salvo: id=%d student_id=%d cargo=%s", registro.id, student_id, registro.cargo)
    return registro


def listar(db: Session, student_id: int) -> list[CurriculumVaga]:
    """Retorna os currículos por vaga do aluno, do mais recente para o mais antigo."""
    return list(
        db.scalars(
            select(CurriculumVaga)
            .where(CurriculumVaga.student_id == student_id)
            .order_by(CurriculumVaga.created_at.desc())
        ).all()
    )


def obter(db: Session, student_id: int, vaga_id: int) -> CurriculumVaga | None:
    """Retorna o registro se existir E pertencer ao aluno (posse verificada nos dois ids)."""
    return db.scalar(
        select(CurriculumVaga).where(
            CurriculumVaga.id == vaga_id,
            CurriculumVaga.student_id == student_id,
        )
    )


def atualizar_texto(db: Session, student_id: int, vaga_id: int, texto: str) -> CurriculumVaga:
    """Salva o texto editado do currículo da vaga.

    Levanta ValueError se o texto ficar vazio ou o registro não existir/pertencer ao aluno.
    """
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("O currículo não pode ficar vazio.")
    registro = obter(db, student_id, vaga_id)
    if registro is None:
        raise ValueError("Currículo por vaga não encontrado.")
    registro.curriculum_text = texto
    db.commit()
    db.refresh(registro)
    logger.info("Currículo por vaga editado: id=%d student_id=%d", vaga_id, student_id)
    return registro


def excluir(db: Session, student_id: int, vaga_id: int) -> bool:
    """Exclui o currículo por vaga. Retorna True se excluiu, False se não existia/não é do aluno."""
    registro = obter(db, student_id, vaga_id)
    if registro is None:
        return False
    db.delete(registro)
    db.commit()
    logger.info("Currículo por vaga excluído: id=%d student_id=%d", vaga_id, student_id)
    return True
