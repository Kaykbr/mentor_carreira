"""Dependências e guards compartilhados entre os routers da API.

Centraliza a checagem de autenticação (sessão) e autorização (propriedade do
recurso) para evitar duplicação de código entre students.py, triage.py, pdi.py,
curriculum.py e web.py.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Student
from app.services import student_service


class RedirectParaLogin(Exception):
    """Levantada por rotas HTML quando não há sessão ativa (tratada em main.py)."""


def eh_admin(aluno: Student) -> bool:
    """Indica se o aluno tem privilégios de administrador.

    É admin quem tiver a flag `is_admin` no banco OU cujo e-mail esteja em
    `ADMIN_EMAILS` (config). Os e-mails de `ADMIN_EMAILS` são sempre admins,
    independentemente da flag — útil para bootstrap do primeiro administrador.
    """
    return bool(aluno.is_admin) or student_service.normalizar_email(aluno.email) in get_settings().emails_admin


def _aluno_da_sessao(request: Request, db: Session) -> Student | None:
    """Retorna o aluno associado à sessão atual, ou `None` se não houver sessão válida."""
    student_id = request.session.get("student_id")
    if student_id is None:
        return None
    aluno = student_service.obter_aluno(db, student_id)
    if aluno is None:
        request.session.clear()
    return aluno


def obter_aluno_logado(request: Request, db: Session = Depends(get_db)) -> Student:
    """Retorna o aluno autenticado via cookie de sessão; levanta 401 (rotas JSON)."""
    aluno = _aluno_da_sessao(request, db)
    if aluno is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado.")
    return aluno


def obter_aluno_logado_html(request: Request, db: Session = Depends(get_db)) -> Student:
    """Como `obter_aluno_logado`, mas redireciona para /login (rotas HTML)."""
    aluno = _aluno_da_sessao(request, db)
    if aluno is None:
        raise RedirectParaLogin()
    return aluno


def verificar_proprio_aluno(student_id: int, aluno_logado: Student = Depends(obter_aluno_logado)) -> Student:
    """Garante que o aluno autenticado só acesse os próprios dados (rotas JSON).

    401 se não autenticado, 403 se autenticado como outro aluno.
    """
    if aluno_logado.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")
    return aluno_logado


def verificar_proprio_aluno_html(
    student_id: int, aluno_logado: Student = Depends(obter_aluno_logado_html)
) -> Student:
    """Como `verificar_proprio_aluno`, mas a checagem de sessão redireciona para /login (rotas HTML)."""
    if aluno_logado.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")
    return aluno_logado


def verificar_admin_html(aluno_logado: Student = Depends(obter_aluno_logado_html)) -> Student:
    """Restringe o acesso ao painel de administração (rotas HTML).

    Sem sessão → redireciona para /login; autenticado mas sem privilégio → 403.
    """
    if not eh_admin(aluno_logado):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores.")
    return aluno_logado
