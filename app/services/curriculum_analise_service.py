"""Análise do currículo base: diagnóstico determinístico + dicas qualitativas da IA.

Divisão de responsabilidades (mesmo padrão da análise de vaga):
- o que é **objetivo** (seções, verbos, quantificação, formatação ATS) é medido por código
  em `curriculo_qualidade` — grátis, recalculado a cada exibição da página;
- o que exige **julgamento** (clareza, priorização, posicionamento) vem da IA e é
  persistido, porque custa uma chamada.

`texto_hash` guarda o SHA-256 do currículo analisado: se o aluno editar ou regerar o texto
depois, `esta_desatualizada` avisa que as dicas são de uma versão anterior.
"""

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CurriculumAnalise
from app.services import claude_client, curriculo_qualidade, curriculum_service, profile_service
from app.services._base import upsert_registro

logger = logging.getLogger(__name__)


def _hash_texto(texto: str) -> str:
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest()


def montar_diagnostico(db: Session, student_id: int, curriculum_text: str) -> dict:
    """Calcula o diagnóstico determinístico do currículo (sem IA, sem custo)."""
    perfil = profile_service.obter_perfil(db, student_id)
    profile_json = perfil.profile_json if perfil else {}
    return curriculo_qualidade.diagnosticar(curriculum_text, profile_json)


def obter(db: Session, student_id: int) -> CurriculumAnalise | None:
    """Retorna a análise salva do currículo do aluno, se existir."""
    return db.scalar(select(CurriculumAnalise).where(CurriculumAnalise.student_id == student_id))


def esta_desatualizada(analise: CurriculumAnalise | None, curriculum_text: str) -> bool:
    """True se o currículo mudou depois que a análise foi gerada."""
    return analise is not None and analise.texto_hash != _hash_texto(curriculum_text)


def analisar(db: Session, student_id: int) -> CurriculumAnalise:
    """Gera (ou regenera) a análise qualitativa do currículo base e salva.

    Levanta ValueError se o aluno ainda não tem perfil ou currículo gerado.
    """
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        raise ValueError("O aluno ainda não possui perfil estruturado (conclua a triagem primeiro).")

    curriculo = curriculum_service.obter_curriculo(db, student_id)
    if curriculo is None:
        raise ValueError("O aluno ainda não possui currículo (gere o currículo primeiro).")

    texto = curriculo.curriculum_text
    diagnostico = curriculo_qualidade.diagnosticar(texto, perfil.profile_json)

    logger.info("Analisando currículo de student_id=%d (pontuação=%d)", student_id, diagnostico["pontuacao"])
    dicas = claude_client.analisar_curriculo(texto, perfil.profile_json, diagnostico)

    analise = upsert_registro(
        db,
        CurriculumAnalise,
        student_id,
        analise_json=dicas,
        texto_hash=_hash_texto(texto),
    )
    logger.info("Análise de currículo salva para student_id=%d", student_id)
    return analise
