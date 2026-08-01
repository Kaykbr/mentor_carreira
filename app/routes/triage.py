"""Endpoints do chat de triagem conduzido pela Claude."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_proprio_aluno
from app.schemas import (
    StudentProfileRead,
    TriageMensagemEnvio,
    TriageMensagemRead,
    TriageRespostaRead,
)
from app.services import profile_service

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/{student_id}/mensagens", response_model=TriageRespostaRead)
def enviar_mensagem(
    student_id: int,
    dados: TriageMensagemEnvio,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> TriageRespostaRead:
    """Envia uma mensagem do aluno ao mentor (Claude) e retorna a resposta da triagem.

    Retorna 400 para regras de negócio violadas (mensagem vazia, limite da triagem).
    """
    try:
        resposta = profile_service.enviar_mensagem_triagem(db, student_id, dados.mensagem)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    return TriageRespostaRead(resposta=resposta)


@router.get("/{student_id}/mensagens", response_model=list[TriageMensagemRead])
def listar_mensagens(
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> list[TriageMensagemRead]:
    """Lista o histórico de mensagens da triagem de um aluno."""
    return list(profile_service.obter_historico(db, student_id))


@router.post("/{student_id}/finalizar", response_model=StudentProfileRead)
def finalizar_triagem(
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> StudentProfileRead:
    """Encerra a triagem e gera o perfil estruturado do aluno a partir da conversa."""
    try:
        return profile_service.finalizar_triagem(db, student_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
