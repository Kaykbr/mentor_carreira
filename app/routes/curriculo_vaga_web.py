"""Rotas HTML dos Currículos por Vaga (análise + currículo direcionado + recomendações).

Atenção à ordem das rotas: `GET .../vagas/nova` precisa vir ANTES de
`GET .../vagas/{vaga_id}` — o Starlette casa `{vaga_id}` como segmento genérico e
"nova" seria capturada pela rota parametrizada (422).
"""

import logging

import anthropic
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_proprio_aluno_html
from app.routes._web import flash, primeiro_erro, templates
from app.schemas import AnaliseVagaInput, CurriculoUpdate
from app.services import curriculum_vaga_service, profile_service

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False)


@router.get("/alunos/{student_id}/curriculo/vagas/nova", response_class=HTMLResponse)
def pagina_nova_vaga(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe o formulário para colar a descrição da vaga."""
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        flash(request, "erro", "Conclua a triagem e gere seu perfil primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "curriculo_vaga_form.html", {"aluno": aluno})


@router.post("/alunos/{student_id}/curriculo/vagas", response_class=HTMLResponse)
def criar_curriculo_vaga(
    request: Request,
    student_id: int,
    jd_text: str = Form(default=""),
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Analisa a vaga, gera recomendações + currículo direcionado e redireciona ao detalhe."""
    try:
        dados = AnaliseVagaInput(jd_text=jd_text)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "curriculo_vaga_form.html",
            {"aluno": aluno, "erro": primeiro_erro(exc), "jd_text": jd_text},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        registro = curriculum_vaga_service.gerar(db, student_id, dados.jd_text)
    except ValueError as e:
        flash(request, "erro", str(e))
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    except anthropic.APIError:
        # Sem este catch, o handler global devolveria JSON 503 cru a um POST de formulário.
        logger.warning("IA indisponível ao gerar currículo por vaga (student_id=%d)", student_id)
        flash(request, "erro", "O mentor (IA) está indisponível no momento. Tente novamente em instantes.")
        return RedirectResponse(
            f"/alunos/{student_id}/curriculo/vagas/nova", status_code=status.HTTP_303_SEE_OTHER
        )

    flash(request, "sucesso", "Análise concluída e currículo direcionado gerado.")
    return RedirectResponse(
        f"/alunos/{student_id}/curriculo/vagas/{registro.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/alunos/{student_id}/curriculo/vagas/{vaga_id}", response_class=HTMLResponse)
def pagina_detalhe_vaga(
    request: Request,
    student_id: int,
    vaga_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe a análise, as recomendações e o currículo direcionado de uma vaga."""
    registro = curriculum_vaga_service.obter(db, student_id, vaga_id)
    if registro is None:
        flash(request, "erro", "Currículo por vaga não encontrado.")
        return RedirectResponse(f"/alunos/{student_id}/curriculo", status_code=status.HTTP_303_SEE_OTHER)
    analise = registro.analise_json
    return templates.TemplateResponse(
        request,
        "curriculo_vaga_detalhe.html",
        {
            "aluno": aluno,
            "vaga": registro,
            "analise": analise,
            "recomendacoes": analise.get("recomendacoes", {}),
        },
    )


@router.post("/alunos/{student_id}/curriculo/vagas/{vaga_id}/editar")
def salvar_curriculo_vaga(
    request: Request,
    student_id: int,
    vaga_id: int,
    curriculum_text: str = Form(...),
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """Salva o texto editado do currículo direcionado."""
    destino = f"/alunos/{student_id}/curriculo/vagas/{vaga_id}"
    try:
        dados = CurriculoUpdate(curriculum_text=curriculum_text)
        curriculum_vaga_service.atualizar_texto(db, student_id, vaga_id, dados.curriculum_text)
    except (ValidationError, ValueError) as exc:
        msg = primeiro_erro(exc) if isinstance(exc, ValidationError) else str(exc)
        flash(request, "erro", msg)
        return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)
    flash(request, "sucesso", "Currículo da vaga salvo com sucesso.")
    return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/alunos/{student_id}/curriculo/vagas/{vaga_id}/excluir")
def excluir_curriculo_vaga(
    request: Request,
    student_id: int,
    vaga_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """Exclui um currículo por vaga do aluno."""
    if curriculum_vaga_service.excluir(db, student_id, vaga_id):
        flash(request, "sucesso", "Currículo por vaga excluído.")
    else:
        flash(request, "erro", "Currículo por vaga não encontrado.")
    return RedirectResponse(f"/alunos/{student_id}/curriculo", status_code=status.HTTP_303_SEE_OTHER)
