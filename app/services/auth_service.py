"""Lógica de autenticação: hashing de senha e verificação de credenciais."""

import logging

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models import Student
from app.services import student_service

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def gerar_hash_senha(senha: str) -> str:
    """Gera o hash bcrypt de uma senha em texto plano."""
    return _pwd_context.hash(senha)


def verificar_senha(senha: str, password_hash: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash armazenado."""
    return _pwd_context.verify(senha, password_hash)


def autenticar_aluno(db: Session, email: str, senha: str) -> Student | None:
    """Retorna o aluno se as credenciais forem válidas, ou `None` caso contrário."""
    aluno = student_service.obter_por_email(db, email)
    if aluno is None or not verificar_senha(senha, aluno.password_hash):
        return None
    return aluno
