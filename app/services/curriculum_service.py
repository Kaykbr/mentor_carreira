"""Lógica de geração e persistência do currículo em formato amigável para ATS."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Curriculum
from app.services import claude_client, contexto_aluno, pdi_service, profile_service
from app.services._base import upsert_registro

logger = logging.getLogger(__name__)


def montar_contexto_curriculo(db: Session, student_id: int, perfil) -> dict:
    """Monta o `contexto_aluno` usado na geração de currículos (geral ou por vaga).

    Reúne dados de contato/formação do `Student`, o nível de experiência calculado e as
    restrições práticas. As áreas de afinidade e a stack vêm do próprio `profile_json`.
    """
    contexto = contexto_aluno.montar_contexto(db, student_id)
    contexto_dict = (
        {"nome": contexto.nome, "email": contexto.email, "curso": contexto.curso, "periodo_atual": contexto.periodo}
        if contexto
        else {}
    )

    contexto_aluno.enriquecer_contexto(contexto_dict, perfil.profile_json)

    return contexto_dict


def gerar_curriculo(db: Session, student_id: int) -> Curriculum:
    """Gera o currículo a partir do perfil estruturado (e do PDI, se já existir) e salva no banco."""
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        raise ValueError("O aluno ainda não possui perfil estruturado (conclua a triagem primeiro).")

    pdi = pdi_service.obter_pdi(db, student_id)
    pdi_json = pdi.pdi_json if pdi is not None else None

    contexto_dict = montar_contexto_curriculo(db, student_id, perfil)

    logger.info("Gerando currículo para student_id=%d (com PDI: %s)", student_id, pdi is not None)
    texto = claude_client.gerar_curriculo(perfil.profile_json, pdi_json, contexto_aluno=contexto_dict)
    curriculo = upsert_registro(db, Curriculum, student_id, curriculum_text=texto)
    logger.info("Currículo salvo/atualizado para student_id=%d", student_id)
    return curriculo


def obter_curriculo(db: Session, student_id: int) -> Curriculum | None:
    """Retorna o currículo salvo de um aluno, se existir."""
    return db.scalar(select(Curriculum).where(Curriculum.student_id == student_id))


def atualizar_curriculo(db: Session, student_id: int, texto: str) -> Curriculum:
    """Salva o texto do currículo editado pelo aluno (sobrescreve o existente).

    Levanta ValueError se o texto ficar vazio ou se o aluno ainda não tem currículo
    gerado (só se edita um currículo que já foi produzido).
    """
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("O currículo não pode ficar vazio.")
    if obter_curriculo(db, student_id) is None:
        raise ValueError("O aluno ainda não possui currículo (gere o currículo primeiro).")

    curriculo = upsert_registro(db, Curriculum, student_id, curriculum_text=texto)
    logger.info("Currículo editado para student_id=%d", student_id)
    return curriculo
