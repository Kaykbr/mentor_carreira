"""Lógica de cadastro e consulta de alunos (compartilhada entre API JSON e páginas web)."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Student

logger = logging.getLogger(__name__)

CURSO_PADRAO = "Sistemas de Informação"


def normalizar_email(email: str) -> str:
    """Normaliza o e-mail (remove espaços e padroniza minúsculas).

    Garante que o e-mail funcione como identificador único independente de
    capitalização — 'Ana@X.com' e 'ana@x.com' viram a mesma conta.
    """
    return email.strip().lower()


def email_em_uso(db: Session, email: str) -> bool:
    """Verifica se já existe um aluno cadastrado com o e-mail informado."""
    return db.scalar(select(Student).where(Student.email == normalizar_email(email))) is not None


def obter_por_email(db: Session, email: str) -> Student | None:
    """Retorna um aluno pelo e-mail (case-insensitive), ou `None` se não existir."""
    return db.scalar(select(Student).where(Student.email == normalizar_email(email)))


def criar_aluno(db: Session, nome: str, email: str, periodo: int, password_hash: str) -> Student:
    """Cadastra um novo aluno com curso fixo em 'Sistemas de Informação'."""
    email = normalizar_email(email)
    aluno = Student(nome=nome.strip(), email=email, curso=CURSO_PADRAO, periodo=periodo, password_hash=password_hash)
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    logger.info("Aluno cadastrado: id=%d, email=%s", aluno.id, email)
    return aluno


def obter_aluno(db: Session, student_id: int) -> Student | None:
    """Retorna um aluno pelo id, ou `None` se não existir."""
    return db.get(Student, student_id)


def atualizar_aluno(db: Session, aluno: Student, nome: str, email: str, periodo: int) -> Student:
    """Atualiza dados básicos da conta; e-mail é re-normalizado e verificado por unicidade."""
    email = normalizar_email(email)
    if email != aluno.email and email_em_uso(db, email):
        raise ValueError("E-mail já cadastrado por outro aluno.")
    aluno.nome = nome.strip()
    aluno.email = email
    aluno.periodo = periodo
    db.commit()
    db.refresh(aluno)
    logger.info("Aluno atualizado: id=%d, email=%s", aluno.id, email)
    return aluno
