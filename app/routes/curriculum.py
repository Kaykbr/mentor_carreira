"""Endpoints de geração e consulta do currículo em formato amigável para ATS."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_proprio_aluno
from app.schemas import CurriculumRead
from app.services import curriculum_service

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.post("/{student_id}/gerar", response_model=CurriculumRead)
def gerar_curriculo(
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> CurriculumRead:
    """Gera (ou regenera) o currículo do aluno a partir do perfil estruturado (e do PDI, se houver)."""
    try:
        return curriculum_service.gerar_curriculo(db, student_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro


@router.get("/{student_id}", response_model=CurriculumRead)
def obter_curriculo(
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> CurriculumRead:
    """Retorna o currículo já gerado para o aluno."""
    curriculo = curriculum_service.obter_curriculo(db, student_id)
    if curriculo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo ainda não foi gerado para este aluno.",
        )
    return curriculo
