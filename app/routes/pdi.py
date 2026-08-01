"""Endpoints de geração e consulta do PDI (Plano de Desenvolvimento Individual)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_proprio_aluno
from app.schemas import PDIRead
from app.services import pdi_service

router = APIRouter(prefix="/pdi", tags=["pdi"])


@router.post("/{student_id}/gerar", response_model=PDIRead)
def gerar_pdi(
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> PDIRead:
    """Gera (ou regenera) o PDI do aluno a partir do perfil estruturado salvo."""
    try:
        return pdi_service.gerar_pdi(db, student_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro


@router.get("/{student_id}", response_model=PDIRead)
def obter_pdi(
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> PDIRead:
    """Retorna o PDI já gerado para o aluno."""
    pdi = pdi_service.obter_pdi(db, student_id)
    if pdi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDI ainda não foi gerado para este aluno.")
    return pdi
