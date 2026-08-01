"""Painel de administração (HTML): métricas visuais, diagnóstico e gestão de alunos.

Todas as rotas exigem um administrador (ver `verificar_admin_html`). Não aparecem na
documentação automática da API (`include_in_schema=False`).
"""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_admin_html
from app.routes._web import flash, templates
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)


@router.get("", response_class=HTMLResponse)
def painel(
    request: Request,
    db: Session = Depends(get_db),
    admin: Student = Depends(verificar_admin_html),
) -> HTMLResponse:
    """Dashboard com KPIs, gráficos e resumo do diagnóstico."""
    metricas = admin_service.obter_metricas(db)
    checks = admin_service.obter_diagnostico(db)
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "admin": admin,
            "secao": "dashboard",
            "m": metricas,
            "diag_resumo": admin_service.resumo_diagnostico(checks),
        },
    )


@router.get("/alunos", response_class=HTMLResponse)
def listar(
    request: Request,
    db: Session = Depends(get_db),
    admin: Student = Depends(verificar_admin_html),
) -> HTMLResponse:
    """Tabela com todos os alunos e o status de cada etapa."""
    return templates.TemplateResponse(
        request,
        "admin/alunos.html",
        {"admin": admin, "secao": "alunos", "linhas": admin_service.listar_alunos(db)},
    )


@router.get("/alunos/{student_id}", response_class=HTMLResponse)
def detalhe(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    admin: Student = Depends(verificar_admin_html),
) -> Response:
    """Detalhe de um aluno, com ações de gestão."""
    dados = admin_service.obter_aluno_detalhe(db, student_id)
    if dados is None:
        flash(request, "erro", "Aluno não encontrado.")
        return RedirectResponse("/admin/alunos", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "admin/aluno_detalhe.html",
        {"admin": admin, "secao": "alunos", **dados},
    )


@router.post("/alunos/{student_id}/admin")
def alterar_admin(
    request: Request,
    student_id: int,
    valor: str = Form(...),
    db: Session = Depends(get_db),
    admin: Student = Depends(verificar_admin_html),
) -> RedirectResponse:
    """Promove ou rebaixa um aluno a administrador (form `valor` = '1' ou '0')."""
    conceder = valor == "1"
    if not conceder and student_id == admin.id:
        flash(request, "erro", "Você não pode remover o próprio acesso de admin.")
        return RedirectResponse(f"/admin/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    aluno = admin_service.definir_admin(db, student_id, conceder)
    if aluno is None:
        flash(request, "erro", "Aluno não encontrado.")
        return RedirectResponse("/admin/alunos", status_code=status.HTTP_303_SEE_OTHER)
    acao = "promovido a administrador" if conceder else "rebaixado a aluno comum"
    flash(request, "sucesso", f"{aluno.nome} {acao}.")
    return RedirectResponse(f"/admin/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/alunos/{student_id}/excluir")
def excluir(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    admin: Student = Depends(verificar_admin_html),
) -> RedirectResponse:
    """Exclui um aluno e todos os seus dados."""
    if student_id == admin.id:
        flash(request, "erro", "Você não pode excluir a própria conta.")
        return RedirectResponse(f"/admin/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    excluido = admin_service.excluir_aluno(db, student_id)
    if not excluido:
        flash(request, "erro", "Aluno não encontrado.")
        return RedirectResponse("/admin/alunos", status_code=status.HTTP_303_SEE_OTHER)
    flash(request, "sucesso", "Aluno excluído com sucesso.")
    return RedirectResponse("/admin/alunos", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/sistema", response_class=HTMLResponse)
def sistema(
    request: Request,
    db: Session = Depends(get_db),
    admin: Student = Depends(verificar_admin_html),
) -> HTMLResponse:
    """Configuração atual (somente leitura) e diagnóstico completo do sistema."""
    checks = admin_service.obter_diagnostico(db)
    return templates.TemplateResponse(
        request,
        "admin/sistema.html",
        {
            "admin": admin,
            "secao": "sistema",
            "config": admin_service.obter_config(db),
            "checks": checks,
            "diag_resumo": admin_service.resumo_diagnostico(checks),
        },
    )
