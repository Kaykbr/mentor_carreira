"""Rotas HTML de autenticação, cadastro, painel do aluno e triagem.

Páginas que não pertencem a um artefato específico (perfil/PDI/currículo têm routers
próprios). `include_in_schema=False` mantém o `/docs` focado nos endpoints JSON.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Student
from app.routes._deps import eh_admin, verificar_proprio_aluno_html
from app.rate_limit import LIMITE_CADASTRO, LIMITE_LOGIN, LIMITE_TRIAGEM, limiter
from app.routes._web import flash, templates
from app.services import auth_service, curriculum_service, pdi_service, profile_service, student_service

router = APIRouter(include_in_schema=False)


@router.get("/", include_in_schema=False)
def pagina_inicial(request: Request) -> RedirectResponse:
    """Redireciona a raiz do site para o painel do aluno logado, ou para o login."""
    student_id = request.session.get("student_id")
    if student_id is None:
        return RedirectResponse("/login")
    return RedirectResponse(f"/alunos/{student_id}")


@router.get("/login", response_class=HTMLResponse)
def pagina_login(request: Request) -> Response:
    """Exibe o formulário de login (ou redireciona para o painel, se já autenticado)."""
    student_id = request.session.get("student_id")
    if student_id is not None:
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login", response_class=HTMLResponse)
@limiter.limit(LIMITE_LOGIN)
def login_web(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
) -> Response:
    """Processa o formulário de login e inicia a sessão do aluno."""
    aluno = auth_service.autenticar_aluno(db, email, senha)
    if aluno is None:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"erro": "E-mail ou senha inválidos.", "email": email},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session["student_id"] = aluno.id
    request.session["is_admin"] = eh_admin(aluno)
    return RedirectResponse(f"/alunos/{aluno.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout_web(request: Request) -> RedirectResponse:
    """Encerra a sessão do aluno e volta para a tela de login."""
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/alunos", response_class=HTMLResponse)
def pagina_alunos(request: Request) -> RedirectResponse:
    """Atalho: leva o aluno autenticado direto ao próprio painel (ou ao login)."""
    student_id = request.session.get("student_id")
    if student_id is None:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/alunos/novo", response_class=HTMLResponse)
def pagina_novo_aluno(request: Request) -> HTMLResponse:
    """Exibe o formulário de cadastro de um novo aluno."""
    return templates.TemplateResponse(
        request, "aluno_form.html", {"exige_convite": bool(get_settings().invite_code)}
    )


@router.post("/alunos/novo", response_class=HTMLResponse)
@limiter.limit(LIMITE_CADASTRO)
def cadastrar_aluno_web(
    request: Request,
    nome: str = Form(..., min_length=1, max_length=200),
    email: str = Form(...),
    periodo: int = Form(..., ge=1, le=8),
    senha: str = Form(..., min_length=8, max_length=128),
    confirmar_senha: str = Form(...),
    codigo_convite: str = Form(default=""),
    db: Session = Depends(get_db),
) -> Response:
    """Processa o formulário de cadastro, cria a conta e já inicia a sessão do aluno."""
    convite_exigido = get_settings().invite_code
    contexto = {"nome": nome, "email": email, "periodo": periodo, "exige_convite": bool(convite_exigido)}

    # Trava o cadastro quando o sistema está publicado com link aberto.
    if convite_exigido and codigo_convite.strip() != convite_exigido:
        return templates.TemplateResponse(
            request,
            "aluno_form.html",
            {**contexto, "erro": "Código de convite inválido. Peça o código ao responsável pela pesquisa."},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if senha != confirmar_senha:
        return templates.TemplateResponse(
            request,
            "aluno_form.html",
            {**contexto, "erro": "As senhas não coincidem."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if student_service.email_em_uso(db, email):
        return templates.TemplateResponse(
            request,
            "aluno_form.html",
            {**contexto, "erro": "Já existe um aluno cadastrado com este e-mail."},
            status_code=status.HTTP_409_CONFLICT,
        )

    aluno = student_service.criar_aluno(
        db,
        nome=nome,
        email=email,
        periodo=periodo,
        password_hash=auth_service.gerar_hash_senha(senha),
    )
    request.session["student_id"] = aluno.id
    return RedirectResponse(f"/alunos/{aluno.id}", status_code=status.HTTP_303_SEE_OTHER)


def _calcular_nivel(etapas: int, pct_kanban: int) -> dict:
    """Calcula o nível de desenvolvimento baseado nas etapas concluídas e progresso do Kanban."""
    if etapas == 4 and pct_kanban >= 50:
        return {"nome": "Avançado", "classe": "verde", "emoji": "🏆", "descricao": "Perfil completo e em desenvolvimento ativo"}
    if etapas >= 3 or pct_kanban >= 25:
        return {"nome": "Em Crescimento", "classe": "amarelo", "emoji": "📈", "descricao": "Bom progresso, continue avançando"}
    if etapas >= 2:
        return {"nome": "Iniciando", "classe": "azul", "emoji": "🚀", "descricao": "Você está no caminho certo"}
    return {"nome": "Explorando", "classe": "cinza", "emoji": "🌱", "descricao": "Complete as primeiras etapas"}


@router.get("/alunos/{student_id}", response_class=HTMLResponse)
def pagina_painel_aluno(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> HTMLResponse:
    """Exibe o painel do aluno com o status de cada etapa (triagem, perfil, PDI, currículo)."""
    perfil = profile_service.obter_perfil(db, student_id)
    pdi = pdi_service.obter_pdi(db, student_id)
    curriculo = curriculum_service.obter_curriculo(db, student_id)
    historico = profile_service.obter_historico(db, student_id)

    areas_afinidade = (perfil.profile_json.get("areas_afinidade") or []) if perfil else []

    kanban_stats = {"total": 0, "concluidos": 0, "em_progresso": 0, "a_fazer": 0, "pct": 0}
    if pdi:
        cards = pdi.pdi_json.get("quadro_kanban", [])
        kanban_stats["total"] = len(cards)
        kanban_stats["concluidos"] = sum(1 for c in cards if c.get("coluna") == "concluido")
        kanban_stats["em_progresso"] = sum(1 for c in cards if c.get("coluna") == "em_progresso")
        kanban_stats["a_fazer"] = sum(1 for c in cards if c.get("coluna") == "a_fazer")
        if cards:
            kanban_stats["pct"] = round(100 * kanban_stats["concluidos"] / len(cards))

    tem_historico = bool(historico)
    n_ok = (1 if tem_historico or perfil else 0) + (1 if perfil else 0) + (1 if pdi else 0) + (1 if curriculo else 0)
    nivel = _calcular_nivel(n_ok, kanban_stats["pct"])

    return templates.TemplateResponse(
        request,
        "aluno_dashboard.html",
        {
            "aluno": aluno,
            "perfil": perfil,
            "pdi": pdi,
            "curriculo": curriculo,
            "tem_historico": tem_historico,
            "areas_afinidade": areas_afinidade,
            "kanban_stats": kanban_stats,
            "nivel": nivel,
        },
    )


@router.get("/alunos/{student_id}/triagem", response_class=HTMLResponse)
def pagina_triagem(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> HTMLResponse:
    """Exibe o chat de triagem com o histórico de mensagens já trocadas."""
    mensagens = profile_service.obter_historico(db, student_id)
    perfil = profile_service.obter_perfil(db, student_id)

    return templates.TemplateResponse(
        request,
        "triagem.html",
        {"aluno": aluno, "mensagens": mensagens, "perfil": perfil},
    )


@router.get("/alunos/{student_id}/configuracoes", response_class=HTMLResponse)
def pagina_configuracoes(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Exibe a página de configurações da conta do aluno (dados básicos e senha)."""
    return templates.TemplateResponse(
        request, "configuracoes.html", {"aluno": aluno}
    )


def _render_configuracoes(
    request: Request,
    aluno: Student,
    *,
    nome: str | None = None,
    periodo: int | None = None,
    erro_dados: str | None = None,
    campo_dados: str | None = None,
    erro_senha: str | None = None,
    campo_senha: str | None = None,
    http_status: int = 200,
) -> Response:
    """Re-renderiza a tela de configurações preservando o valor digitado e o erro específico
    de cada seção (dados ou senha), sem misturar as duas."""
    return templates.TemplateResponse(
        request,
        "configuracoes.html",
        {
            "aluno": aluno,
            "nome": nome if nome is not None else aluno.nome,
            "periodo": periodo if periodo is not None else aluno.periodo,
            "erro_dados": erro_dados,
            "campo_dados": campo_dados,
            "erro_senha": erro_senha,
            "campo_senha": campo_senha,
        },
        status_code=http_status,
    )


@router.post("/alunos/{student_id}/configuracoes", response_class=HTMLResponse)
def salvar_configuracoes(
    request: Request,
    student_id: int,
    nome: str = Form(...),
    periodo: int = Form(...),
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Salva nome e período do aluno. E-mail não é editável aqui (é o identificador de login)."""
    if not 1 <= periodo <= 8:
        return _render_configuracoes(
            request, aluno, nome=nome, periodo=periodo,
            erro_dados="O período deve estar entre 1 e 8.", campo_dados="periodo",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    if not nome.strip():
        return _render_configuracoes(
            request, aluno, nome=nome, periodo=periodo,
            erro_dados="O nome não pode ficar em branco.", campo_dados="nome",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    # E-mail permanece o mesmo (não vem do form) — apenas repassamos ao serviço.
    student_service.atualizar_aluno(db, aluno, nome, aluno.email, periodo)
    flash(request, "sucesso", "Dados atualizados com sucesso.")
    return RedirectResponse(
        f"/alunos/{student_id}/configuracoes",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/alunos/{student_id}/configuracoes/senha", response_class=HTMLResponse)
def alterar_senha(
    request: Request,
    student_id: int,
    senha_atual: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_nova_senha: str = Form(...),
    db: Session = Depends(get_db),
    aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Troca a senha do aluno (fluxo isolado — não mexe em nome/período)."""
    def erro(campo: str, msg: str) -> Response:
        return _render_configuracoes(
            request, aluno, erro_senha=msg, campo_senha=campo,
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    if not auth_service.verificar_senha(senha_atual, aluno.password_hash):
        return erro("senha_atual", "Senha atual incorreta.")
    if len(nova_senha) < 8:
        return erro("nova_senha", "A nova senha deve ter pelo menos 8 caracteres.")
    if nova_senha != confirmar_nova_senha:
        return erro("confirmar_nova_senha", "As senhas não conferem.")

    aluno.password_hash = auth_service.gerar_hash_senha(nova_senha)
    db.commit()
    flash(request, "sucesso", "Senha alterada com sucesso.")
    return RedirectResponse(
        f"/alunos/{student_id}/configuracoes",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/alunos/{student_id}/triagem/mensagem", response_class=HTMLResponse)
@limiter.limit(LIMITE_TRIAGEM)
def enviar_mensagem_htmx(
    request: Request,
    student_id: int,
    mensagem: str = Form(...),
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> Response:
    """Rota HTMX: recebe mensagem do aluno, chama o mentor e devolve fragmento HTML."""
    hora = datetime.now().strftime("%H:%M")
    try:
        resposta = profile_service.enviar_mensagem_triagem(db, student_id, mensagem)
        return templates.TemplateResponse(
            request,
            "_partials/mensagem_chat.html",
            {"mensagem_user": mensagem, "resposta": resposta, "hora": hora},
        )
    except ValueError as erro:
        return templates.TemplateResponse(
            request,
            "_partials/mensagem_chat.html",
            {"mensagem_user": mensagem, "erro": str(erro), "hora": hora},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.post("/alunos/{student_id}/triagem/finalizar")
def finalizar_triagem_web(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    _aluno: Student = Depends(verificar_proprio_aluno_html),
) -> RedirectResponse:
    """Encerra a triagem, gera o perfil estruturado e redireciona para a página do perfil."""
    try:
        profile_service.finalizar_triagem(db, student_id)
    except ValueError:
        flash(request, "erro", "Não há conversa de triagem registrada para gerar o perfil.")
        return RedirectResponse(f"/alunos/{student_id}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(f"/alunos/{student_id}/perfil", status_code=status.HTTP_303_SEE_OTHER)
