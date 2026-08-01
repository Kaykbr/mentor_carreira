"""Redirects da antiga Análise de Vaga para o fluxo de Currículos por Vaga.

A análise de vaga foi fundida ao fluxo de currículo direcionado
(`app/routes/curriculo_vaga_web.py`): a mesma análise agora também gera o currículo
com as palavras-chave da vaga e recomendações de competitividade, com persistência.
Estas rotas existem apenas para não quebrar links/favoritos antigos.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from app.models import Student
from app.routes._deps import verificar_proprio_aluno_html

router = APIRouter(include_in_schema=False)


@router.get("/alunos/{student_id}/analise-vaga")
def redirect_analise_vaga(
    request: Request,
    student_id: int,
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """Redireciona a antiga página de análise para o novo fluxo."""
    return RedirectResponse(
        f"/alunos/{student_id}/curriculo/vagas/nova", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/alunos/{student_id}/analise-vaga")
def redirect_analise_vaga_post(
    request: Request,
    student_id: int,
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """POSTs antigos também vão para o novo formulário (o texto precisa ser recolado)."""
    return RedirectResponse(
        f"/alunos/{student_id}/curriculo/vagas/nova", status_code=status.HTTP_303_SEE_OTHER
    )
