"""Endpoints JSON de autenticação (login, logout e sessão atual)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import eh_admin, obter_aluno_logado
from app.schemas import LoginRequest, StudentRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=StudentRead)
def login(dados: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Student:
    """Autentica o aluno por e-mail/senha e inicia uma sessão (cookie)."""
    aluno = auth_service.autenticar_aluno(db, dados.email, dados.senha)
    if aluno is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")
    request.session["student_id"] = aluno.id
    request.session["is_admin"] = eh_admin(aluno)
    return aluno


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> None:
    """Encerra a sessão atual."""
    request.session.clear()


@router.get("/me", response_model=StudentRead)
def me(aluno: Student = Depends(obter_aluno_logado)) -> Student:
    """Retorna os dados do aluno autenticado na sessão atual."""
    return aluno
