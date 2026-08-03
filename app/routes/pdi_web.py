"""Rotas HTML do PDI (visualização, geração, edição e quadro Kanban)."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_proprio_aluno_html
from app.rate_limit import LIMITE_GERACAO, limiter
from app.routes._web import flash, linhas, primeiro_erro, templates
from app.schemas import PDIUpdate, QuadroUpdate
from app.services import pdi_service, profile_service

router = APIRouter(include_in_schema=False)


@router.get("/alunos/{student_id}/pdi", response_class=HTMLResponse)
def pagina_pdi(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe o PDI do aluno (ou a opção de gerá-lo, se ainda não existir)."""
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        flash(request, "erro", "O PDI depende do perfil. Conclua a triagem primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)

    pdi = pdi_service.garantir_quadro(db, student_id)
    return templates.TemplateResponse(
        request,
        "pdi.html",
        {"aluno": aluno, "pdi": pdi, "pdi_json": pdi.pdi_json if pdi else None},
    )


@router.post("/alunos/{student_id}/pdi/gerar")
@limiter.limit(LIMITE_GERACAO)
def gerar_pdi_web(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """Gera (ou regenera) o PDI do aluno e volta para a página do PDI."""
    try:
        pdi_service.gerar_pdi(db, student_id)
    except ValueError:
        flash(request, "erro", "Não foi possível gerar o PDI: conclua a triagem primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(f"/alunos/{student_id}/pdi", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/alunos/{student_id}/pdi/editar", response_class=HTMLResponse)
def pagina_editar_pdi(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe o formulário de edição dos campos estratégicos do PDI."""
    pdi = pdi_service.obter_pdi(db, student_id)
    if pdi is None:
        flash(request, "erro", "O PDI ainda não foi gerado. Gere o PDI primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "pdi_editar.html",
        {"aluno": aluno, "pdi_json": pdi.pdi_json},
    )


@router.post("/alunos/{student_id}/pdi/editar", response_class=HTMLResponse)
def salvar_pdi_web(
    request: Request,
    student_id: int,
    objetivo_geral: str = Form(""),
    metas_curto: str = Form(""),
    metas_medio: str = Form(""),
    comp_nome: list[str] = Form(default=[]),
    comp_motivo: list[str] = Form(default=[]),
    cron_periodo: list[str] = Form(default=[]),
    cron_foco: list[str] = Form(default=[]),
    cron_atividades: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Processa o formulário de edição do PDI (objetivo, metas, competências, cronograma)."""
    competencias = []
    for i, nome in enumerate(comp_nome):
        if not nome.strip():
            continue
        competencias.append(
            {
                "nome": nome.strip(),
                "motivo": (comp_motivo[i] if i < len(comp_motivo) else "").strip(),
            }
        )

    cronograma = []
    for i, periodo in enumerate(cron_periodo):
        if not periodo.strip():
            continue
        cronograma.append(
            {
                "periodo": periodo.strip(),
                "foco": (cron_foco[i] if i < len(cron_foco) else "").strip(),
                "atividades": linhas(cron_atividades[i] if i < len(cron_atividades) else ""),
            }
        )

    campos = {
        "objetivo_geral": objetivo_geral.strip(),
        "metas_curto_prazo": linhas(metas_curto),
        "metas_medio_prazo": linhas(metas_medio),
        "competencias_a_desenvolver": competencias,
        "cronograma": cronograma,
    }

    try:
        validado = PDIUpdate(**campos)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "pdi_editar.html",
            {"aluno": aluno, "pdi_json": campos, "erro": primeiro_erro(exc)},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pdi_service.atualizar_pdi(db, student_id, validado.model_dump())
    except ValueError as erro:
        flash(request, "erro", str(erro))
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    flash(request, "sucesso", "PDI salvo com sucesso.")
    return RedirectResponse(f"/alunos/{student_id}/pdi", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/alunos/{student_id}/pdi/quadro")
def salvar_quadro_pdi(
    student_id: int,
    dados: QuadroUpdate,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> dict:
    """Persiste o estado do quadro Kanban do PDI (chamado via fetch a cada mudança)."""
    try:
        pdi_service.atualizar_quadro(db, student_id, [card.model_dump() for card in dados.cards])
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    return {"ok": True}
