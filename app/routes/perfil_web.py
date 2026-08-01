"""Rotas HTML do perfil estruturado (visualização e edição)."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.routes._deps import verificar_proprio_aluno_html
from app.routes._web import flash, itens_csv, linhas, primeiro_erro, templates
from app.schemas import PerfilUpdate

from app.services import profile_service

router = APIRouter(include_in_schema=False)


_NIVEIS_STACK = {"", "basico", "intermediario", "avancado"}


def _montar_itens_stack(nomes: list[str], niveis: list[str]) -> list[dict]:
    """Converte as listas paralelas do form em `[{"nome", "nivel"}]`.

    Ignora linhas em branco (o aluno clicou "+ Adicionar" e não preencheu) e valida o
    `nivel` contra o conjunto conhecido — valor desconhecido cai para "" (sem nível).
    """
    itens: list[dict] = []
    for i, bruto in enumerate(nomes):
        nome = (bruto or "").strip()
        if not nome:
            continue
        nivel = (niveis[i] if i < len(niveis) else "").strip().lower()
        if nivel not in _NIVEIS_STACK:
            nivel = ""
        itens.append({"nome": nome, "nivel": nivel})
    return itens


def _calcular_completude(pj: dict) -> dict:
    """Retorna percentual e mapa de seções preenchidas do profile_json."""
    checks = {
        "resumo": bool(pj.get("resumo_geral", "").strip()),
        "objetivo": bool(
            pj.get("objetivo_carreira", {}).get("curto_prazo", "").strip()
            or pj.get("objetivo_carreira", {}).get("medio_prazo", "").strip()
        ),
        "experiencias": bool(pj.get("experiencias")),
        "stack": bool(
            pj.get("stack_tecnica", {}).get("linguagens")
            or pj.get("stack_tecnica", {}).get("frameworks_ferramentas")
        ),
        "formacao": bool(
            pj.get("formacao", {}).get("instituicao", "").strip()
            or pj.get("formacao", {}).get("destaques_academicos")
        ),
        "links": bool(
            pj.get("links", {}).get("github", "").strip()
            or pj.get("links", {}).get("linkedin", "").strip()
            or pj.get("links", {}).get("portfolio", "").strip()
        ),
        "certificacoes": bool(pj.get("certificacoes")),
        "soft_skills": bool(pj.get("soft_skills")),
    }
    preenchidas = sum(1 for v in checks.values() if v)
    total = len(checks)
    pct = round(100 * preenchidas / total) if total else 0
    return {"secoes": checks, "preenchidas": preenchidas, "total": total, "pct": pct}


@router.get("/alunos/{student_id}/perfil", response_class=HTMLResponse)
def pagina_perfil(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe o perfil estruturado do aluno."""
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        flash(request, "erro", "O perfil ainda não foi gerado. Conclua a triagem primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)

    completude = _calcular_completude(perfil.profile_json)

    return templates.TemplateResponse(
        request,
        "perfil.html",
        {
            "aluno": aluno,
            "perfil": perfil,
            "perfil_json": perfil.profile_json,
            "areas_afinidade": perfil.profile_json.get("areas_afinidade") or [],
            "completude": completude,
        },
    )


@router.get("/alunos/{student_id}/perfil/editar", response_class=HTMLResponse)
def pagina_editar_perfil(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe o formulário de edição do perfil estruturado."""
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        flash(request, "erro", "O perfil ainda não foi gerado. Conclua a triagem primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "perfil_editar.html",
        {"aluno": aluno, "perfil_json": perfil.profile_json},
    )


@router.post("/alunos/{student_id}/perfil/editar", response_class=HTMLResponse)
def salvar_perfil_web(
    request: Request,
    student_id: int,
    resumo_geral: str = Form(""),
    objetivo_curto: str = Form(""),
    objetivo_medio: str = Form(""),
    areas_interesse: str = Form(""),
    stack_lang_nome: list[str] = Form(default=[]),
    stack_lang_nivel: list[str] = Form(default=[]),
    stack_fw_nome: list[str] = Form(default=[]),
    stack_fw_nivel: list[str] = Form(default=[]),
    soft_skills: str = Form(""),
    restricoes_carga: str = Form(""),
    restricoes_local: str = Form(""),
    restricoes_modalidade: str = Form("indiferente"),
    restricoes_outras: str = Form(""),
    formacao_instituicao: str = Form(""),
    formacao_previsao: str = Form(""),
    formacao_destaques: str = Form(""),
    link_github: str = Form(""),
    link_linkedin: str = Form(""),
    link_portfolio: str = Form(""),
    link_outro: str = Form(""),
    exp_tipo: list[str] = Form(default=[]),
    exp_titulo: list[str] = Form(default=[]),
    exp_descricao: list[str] = Form(default=[]),
    exp_periodo: list[str] = Form(default=[]),
    exp_tecnologias: list[str] = Form(default=[]),
    exp_resultados: list[str] = Form(default=[]),
    cert_nome: list[str] = Form(default=[]),
    cert_instituicao: list[str] = Form(default=[]),
    cert_ano: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Processa o formulário de edição do perfil e salva o perfil estruturado completo."""
    experiencias = []
    for i, titulo in enumerate(exp_titulo):
        if not titulo.strip():
            continue  # linha em branco (o aluno adicionou e não preencheu)
        experiencias.append(
            {
                "tipo": exp_tipo[i] if i < len(exp_tipo) else "projeto_pessoal",
                "titulo": titulo.strip(),
                "descricao": (exp_descricao[i] if i < len(exp_descricao) else "").strip(),
                "periodo": (exp_periodo[i] if i < len(exp_periodo) else "").strip(),
                "tecnologias": itens_csv(exp_tecnologias[i] if i < len(exp_tecnologias) else ""),
                "resultados": (exp_resultados[i] if i < len(exp_resultados) else "").strip(),
            }
        )

    perfil_atual = profile_service.obter_perfil(db, student_id)
    disciplinas_preservadas = (
        perfil_atual.profile_json.get("disciplinas_relevantes", [])
        if perfil_atual else []
    )

    certificacoes = []
    for i, nome in enumerate(cert_nome):
        if not nome.strip():
            continue
        certificacoes.append(
            {
                "nome": nome.strip(),
                "instituicao": (cert_instituicao[i] if i < len(cert_instituicao) else "").strip(),
                "ano": (cert_ano[i] if i < len(cert_ano) else "").strip(),
            }
        )

    profile_json = {
        "objetivo_carreira": {
            "curto_prazo": objetivo_curto.strip(),
            "medio_prazo": objetivo_medio.strip(),
            "areas_interesse": linhas(areas_interesse),
        },
        "experiencias": experiencias,
        "disciplinas_relevantes": disciplinas_preservadas,
        "stack_tecnica": {
            "linguagens": _montar_itens_stack(stack_lang_nome, stack_lang_nivel),
            "frameworks_ferramentas": _montar_itens_stack(stack_fw_nome, stack_fw_nivel),
        },
        "soft_skills": linhas(soft_skills),
        "restricoes": {
            "carga_horaria_disponivel": restricoes_carga.strip(),
            "localizacao": restricoes_local.strip(),
            "modalidade_preferida": restricoes_modalidade,
            "outras": restricoes_outras.strip(),
        },
        "resumo_geral": resumo_geral.strip(),
        "formacao": {
            "instituicao": formacao_instituicao.strip(),
            "previsao_conclusao": formacao_previsao.strip(),
            "destaques_academicos": linhas(formacao_destaques),
        },
        "certificacoes": certificacoes,
        "links": {
            "github": link_github.strip(),
            "linkedin": link_linkedin.strip(),
            "portfolio": link_portfolio.strip(),
            "outro": link_outro.strip(),
        },
    }

    perfil_atual = profile_service.obter_perfil(db, student_id)
    if perfil_atual is None:
        flash(request, "erro", "O perfil ainda não foi gerado. Conclua a triagem primeiro.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    # Áreas de afinidade são geradas pela IA e não editadas no formulário: preservar.
    profile_json["areas_afinidade"] = perfil_atual.profile_json.get("areas_afinidade") or []

    try:
        validado = PerfilUpdate(**profile_json)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "perfil_editar.html",
            {"aluno": aluno, "perfil_json": profile_json, "erro": primeiro_erro(exc)},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    profile_service.atualizar_perfil(db, student_id, validado.model_dump())
    flash(request, "sucesso", "Perfil salvo com sucesso.")
    return RedirectResponse(f"/alunos/{student_id}/perfil", status_code=status.HTTP_303_SEE_OTHER)
