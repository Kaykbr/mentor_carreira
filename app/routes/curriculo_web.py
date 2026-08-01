"""Rotas HTML do currículo (visualização, geração e edição inline)."""

import anthropic
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_proprio_aluno_html
from app.routes._web import flash, templates
from app.schemas import CurriculoUpdate
from app.services import (
    curriculum_analise_service,
    curriculum_service,
    curriculum_vaga_service,
    pdi_service,
    profile_service,
)

router = APIRouter(include_in_schema=False)


@router.get("/alunos/{student_id}/curriculo", response_class=HTMLResponse)
def pagina_curriculo(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe o currículo do aluno (ou a opção de gerá-lo, se ainda não existir)."""
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        flash(request, "erro", "O currículo depende do perfil. Conclua a triagem primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)

    curriculo = curriculum_service.obter_curriculo(db, student_id)
    pdi = pdi_service.obter_pdi(db, student_id)
    vagas = curriculum_vaga_service.listar(db, student_id)

    # Diagnóstico é determinístico e barato: recalculado a cada visita, reflete edições
    # manuais na hora. As dicas da IA são persistidas e podem estar defasadas.
    diagnostico = None
    analise = None
    analise_defasada = False
    if curriculo is not None:
        diagnostico = curriculum_analise_service.montar_diagnostico(db, student_id, curriculo.curriculum_text)
        analise = curriculum_analise_service.obter(db, student_id)
        analise_defasada = curriculum_analise_service.esta_desatualizada(analise, curriculo.curriculum_text)

    return templates.TemplateResponse(
        request,
        "curriculo.html",
        {
            "aluno": aluno,
            "curriculo": curriculo,
            "pdi": pdi,
            "vagas": vagas,
            "diagnostico": diagnostico,
            "analise": analise,
            "analise_defasada": analise_defasada,
        },
    )


@router.post("/alunos/{student_id}/curriculo/gerar")
def gerar_curriculo_web(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """Gera (ou regenera) o currículo do aluno e volta para a página do currículo."""
    try:
        curriculum_service.gerar_curriculo(db, student_id)
    except ValueError:
        flash(request, "erro", "Não foi possível gerar o currículo: conclua a triagem primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(f"/alunos/{student_id}/curriculo", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/alunos/{student_id}/curriculo/analisar")
def analisar_curriculo_web(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """Gera (ou regenera) as dicas de melhoria do currículo pela IA."""
    destino = f"/alunos/{student_id}/curriculo"
    try:
        curriculum_analise_service.analisar(db, student_id)
    except ValueError as erro:
        flash(request, "erro", str(erro))
        return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)
    except anthropic.APIError:
        # Sem este except o handler global devolveria JSON 503 cru para um POST de formulário.
        flash(request, "erro", "O mentor (IA) está indisponível agora. Tente analisar novamente em instantes.")
        return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)

    flash(request, "sucesso", "Análise do currículo concluída.")
    return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/alunos/{student_id}/curriculo/editar", response_class=HTMLResponse)
def salvar_curriculo_web(
    request: Request,
    student_id: int,
    curriculum_text: str = Form(...),
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Salva o texto do currículo editado pelo aluno (edição inline na página do currículo)."""
    try:
        dados = CurriculoUpdate(curriculum_text=curriculum_text)
    except ValidationError:
        flash(request, "erro", "O currículo não pode ficar vazio.")
        return RedirectResponse(
            f"/alunos/{student_id}/curriculo",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        curriculum_service.atualizar_curriculo(db, student_id, dados.curriculum_text)
    except ValueError as erro:
        flash(request, "erro", str(erro))
        return RedirectResponse(
            f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER
        )
    flash(request, "sucesso", "Currículo salvo com sucesso.")
    return RedirectResponse(f"/alunos/{student_id}/curriculo", status_code=status.HTTP_303_SEE_OTHER)
