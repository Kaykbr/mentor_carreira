"""Endpoints relacionados ao cadastro e consulta de alunos."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Student
from app.routes._deps import eh_admin, verificar_proprio_aluno
from app.schemas import StudentCreate, StudentProfileRead, StudentRead
from app.services import auth_service, profile_service, student_service

router = APIRouter(prefix="/students", tags=["students"])


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def cadastrar_aluno(dados: StudentCreate, request: Request, db: Session = Depends(get_db)) -> Student:
    """Cadastra um novo aluno (curso fixo em 'Sistemas de Informação') e inicia a sessão.

    Quando `INVITE_CODE` está configurado (deploy público), o campo `codigo_convite` do
    corpo passa a ser obrigatório — impede que estranhos criem contas pela API JSON,
    contornando a trava do formulário HTML.
    """
    convite_exigido = get_settings().invite_code
    if convite_exigido and (dados.codigo_convite or "").strip() != convite_exigido:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Código de convite inválido.",
        )

    if student_service.email_em_uso(db, dados.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um aluno com este e-mail.")

    aluno = student_service.criar_aluno(
        db,
        nome=dados.nome,
        email=dados.email,
        periodo=dados.periodo,
        password_hash=auth_service.gerar_hash_senha(dados.senha),
    )
    request.session["student_id"] = aluno.id
    request.session["is_admin"] = eh_admin(aluno)
    return aluno


@router.get("/{student_id}", response_model=StudentRead)
def obter_aluno(student_id: int, aluno: Student = Depends(verificar_proprio_aluno)) -> Student:
    """Retorna os dados do aluno autenticado (somente os próprios dados)."""
    return aluno


@router.get("/{student_id}/profile", response_model=StudentProfileRead)
def obter_perfil_aluno(
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno),
) -> StudentProfileRead:
    """Retorna o perfil estruturado do aluno gerado ao final da triagem."""
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil ainda não foi gerado para este aluno.",
        )
    return perfil
