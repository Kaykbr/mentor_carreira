"""Testes do frontend web (rotas HTML servidas pelo FastAPI via Jinja2)."""

from unittest.mock import patch

from tests.conftest import CURRICULO_FAKE, PDI_FAKE, PERFIL_FAKE


# ---------------------------------------------------------------------------
# Helpers reutilizáveis
# ---------------------------------------------------------------------------


def _criar_aluno(client, nome="Luana", email="luana@t.com", periodo=3, senha="senha-segura-123"):
    r = client.post(
        "/alunos/novo",
        data={"nome": nome, "email": email, "periodo": periodo, "senha": senha, "confirmar_senha": senha},
    )
    assert r.status_code == 303
    return int(r.headers["location"].split("/")[-1])


def _enviar_mensagem(client, sid):
    from app.services import claude_client

    with patch.object(claude_client, "conversar_triagem", return_value="Entendido!"):
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})


def _finalizar_triagem(client, sid):
    from app.services import claude_client

    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        r = client.post(f"/alunos/{sid}/triagem/finalizar")
    assert r.status_code == 303
    assert r.headers["location"] == f"/alunos/{sid}/perfil"


def _gerar_pdi(client, sid):
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        r = client.post(f"/alunos/{sid}/pdi/gerar")
    assert r.status_code == 303


def _gerar_curriculo(client, sid):
    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        r = client.post(f"/alunos/{sid}/curriculo/gerar")
    assert r.status_code == 303


# ---------------------------------------------------------------------------
# Navegação e redirecionamentos
# ---------------------------------------------------------------------------


def test_raiz_sem_sessao_redireciona_para_login(client):
    r = client.get("/")
    assert r.status_code in (301, 302, 307, 308)
    assert r.headers["location"] == "/login"


def test_raiz_com_sessao_redireciona_para_painel(client):
    sid = _criar_aluno(client)
    r = client.get("/")
    assert r.status_code in (301, 302, 307, 308)
    assert r.headers["location"] == f"/alunos/{sid}"


def test_docs_nao_contem_rotas_web(client):
    """As rotas web não devem aparecer no schema OpenAPI (include_in_schema=False)."""
    paths = client.get("/openapi.json").json()["paths"]
    for path in paths:
        assert not path.startswith("/alunos"), f"Rota web '{path}' não deveria estar no /docs"


# ---------------------------------------------------------------------------
# Atalho /alunos
# ---------------------------------------------------------------------------


def test_pagina_alunos_sem_sessao_redireciona_para_login(client):
    r = client.get("/alunos")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_pagina_alunos_com_sessao_redireciona_para_painel(client):
    sid = _criar_aluno(client)
    r = client.get("/alunos")
    assert r.status_code == 303
    assert r.headers["location"] == f"/alunos/{sid}"


# ---------------------------------------------------------------------------
# Cadastro de aluno (formulário)
# ---------------------------------------------------------------------------


def test_get_formulario_cadastro(client):
    r = client.get("/alunos/novo")
    assert r.status_code == 200
    assert "<form" in r.text


def test_cadastro_via_form_redireciona(client):
    r = client.post(
        "/alunos/novo",
        data={
            "nome": "João",
            "email": "joao@t.com",
            "periodo": 2,
            "senha": "senha-segura-123",
            "confirmar_senha": "senha-segura-123",
        },
    )
    assert r.status_code == 303
    sid = int(r.headers["location"].split("/")[-1])
    assert sid >= 1


def test_cadastro_via_form_inicia_sessao(client):
    """Após o cadastro, o aluno já deve estar logado e conseguir acessar o próprio painel."""
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid}")
    assert r.status_code == 200


def test_cadastro_email_duplicado_re_renderiza_com_erro(client):
    _criar_aluno(client, email="dup@t.com")
    r = client.post(
        "/alunos/novo",
        data={
            "nome": "X",
            "email": "dup@t.com",
            "periodo": 1,
            "senha": "senha-segura-123",
            "confirmar_senha": "senha-segura-123",
        },
    )
    assert r.status_code == 409
    assert "Já existe um aluno" in r.text


def test_cadastro_mantem_dados_no_form_apos_erro(client):
    """Os dados preenchidos devem ser preservados ao re-renderizar o formulário com erro."""
    _criar_aluno(client, email="dup2@t.com")
    r = client.post(
        "/alunos/novo",
        data={
            "nome": "Outro",
            "email": "dup2@t.com",
            "periodo": 5,
            "senha": "senha-segura-123",
            "confirmar_senha": "senha-segura-123",
        },
    )
    assert "Outro" in r.text
    assert "dup2@t.com" in r.text


def test_cadastro_periodo_invalido_retorna_erro(client):
    """Período fora do range (1-12) deve resultar em resposta de erro."""
    r = client.post(
        "/alunos/novo",
        data={
            "nome": "X",
            "email": "x@t.com",
            "periodo": 0,
            "senha": "senha-segura-123",
            "confirmar_senha": "senha-segura-123",
        },
    )
    # FastAPI retorna 422 para Form com valor inválido
    assert r.status_code == 422


def test_cadastro_periodo_negativo_retorna_erro(client):
    """Período negativo deve ser rejeitado."""
    r = client.post(
        "/alunos/novo",
        data={
            "nome": "X",
            "email": "x@t.com",
            "periodo": -5,
            "senha": "senha-segura-123",
            "confirmar_senha": "senha-segura-123",
        },
    )
    assert r.status_code == 422


def test_cadastro_senhas_diferentes_retorna_400(client):
    """Senha e confirmação diferentes devem re-renderizar o formulário com erro 400."""
    r = client.post(
        "/alunos/novo",
        data={
            "nome": "X",
            "email": "senha-dif@t.com",
            "periodo": 1,
            "senha": "senha-segura-123",
            "confirmar_senha": "outra-senha-456",
        },
    )
    assert r.status_code == 400
    assert "não coincidem" in r.text


def test_cadastro_senha_curta_retorna_422(client):
    """Senha menor que 8 caracteres deve ser rejeitada (Form min_length=8)."""
    r = client.post(
        "/alunos/novo",
        data={
            "nome": "X",
            "email": "senha-curta@t.com",
            "periodo": 1,
            "senha": "1234567",
            "confirmar_senha": "1234567",
        },
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Dashboard do aluno
# ---------------------------------------------------------------------------


def test_dashboard_aluno_existente(client):
    sid = _criar_aluno(client, nome="Marcos")
    r = client.get(f"/alunos/{sid}")
    assert r.status_code == 200
    assert "Marcos" in r.text


def test_dashboard_sem_sessao_redireciona_para_login(client):
    r = client.get("/alunos/9999")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_dashboard_outro_aluno_retorna_403(client):
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid + 1}")
    assert r.status_code == 403


def test_dashboard_status_nao_iniciada(client):
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid}")
    assert "Não iniciada" in r.text


def test_dashboard_status_em_andamento(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    r = client.get(f"/alunos/{sid}")
    assert "Em andamento" in r.text


def test_dashboard_status_concluida_apos_perfil(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    r = client.get(f"/alunos/{sid}")
    assert "Concluída" in r.text


def test_dashboard_quatro_badges_ok_ao_final(client):
    """Após todas as etapas concluídas, deve haver 4 badges 'badge-ok'."""
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    _gerar_pdi(client, sid)
    _gerar_curriculo(client, sid)
    r = client.get(f"/alunos/{sid}")
    assert r.text.count("badge-ok") == 4


def test_dashboard_com_erro_na_query_string(client):
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid}?erro=Algo deu errado")
    assert r.status_code == 200
    assert "Algo deu errado" in r.text


# ---------------------------------------------------------------------------
# Triagem
# ---------------------------------------------------------------------------


def test_pagina_triagem_exibe_formulario(client):
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid}/triagem")
    assert r.status_code == 200
    assert "form-mensagem" in r.text


def test_pagina_triagem_exibe_historico(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    r = client.get(f"/alunos/{sid}/triagem")
    assert "Oi" in r.text
    assert "Entendido!" in r.text


def test_finalizar_triagem_sem_mensagens_redireciona_com_erro(client):
    sid = _criar_aluno(client)
    r = client.post(f"/alunos/{sid}/triagem/finalizar")
    assert r.status_code == 303
    assert "erro=" in r.headers["location"]


def test_finalizar_triagem_com_mensagens_redireciona_para_perfil(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)  # já asserta 303 + location correto


# ---------------------------------------------------------------------------
# Perfil
# ---------------------------------------------------------------------------


def test_pagina_perfil_sem_triagem_redireciona(client):
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid}/perfil")
    assert r.status_code == 303
    assert "erro=" in r.headers["location"]


def test_pagina_perfil_exibe_dados(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    r = client.get(f"/alunos/{sid}/perfil")
    assert r.status_code == 200
    assert PERFIL_FAKE["resumo_geral"] in r.text


def test_pagina_perfil_exibe_experiencias(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    r = client.get(f"/alunos/{sid}/perfil")
    assert "API de tarefas" in r.text


# ---------------------------------------------------------------------------
# PDI
# ---------------------------------------------------------------------------


def test_pagina_pdi_sem_perfil_redireciona(client):
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid}/pdi")
    assert r.status_code == 303
    assert "erro=" in r.headers["location"]


def test_pagina_pdi_sem_pdi_gerado_exibe_botao(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    r = client.get(f"/alunos/{sid}/pdi")
    assert r.status_code == 200
    assert "Gerar PDI" in r.text


def test_pagina_pdi_exibe_conteudo_apos_gerar(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    _gerar_pdi(client, sid)
    r = client.get(f"/alunos/{sid}/pdi")
    assert r.status_code == 200
    assert PDI_FAKE["objetivo_geral"] in r.text
    assert "Regenerar PDI" in r.text


def test_gerar_pdi_redireciona_para_pagina_pdi(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        r = client.post(f"/alunos/{sid}/pdi/gerar")
    assert r.status_code == 303
    assert r.headers["location"] == f"/alunos/{sid}/pdi"


# ---------------------------------------------------------------------------
# Currículo
# ---------------------------------------------------------------------------


def test_pagina_curriculo_sem_perfil_redireciona(client):
    sid = _criar_aluno(client)
    r = client.get(f"/alunos/{sid}/curriculo")
    assert r.status_code == 303
    assert "erro=" in r.headers["location"]


def test_pagina_curriculo_sem_curriculo_gerado_exibe_botao(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    r = client.get(f"/alunos/{sid}/curriculo")
    assert r.status_code == 200
    assert "Gerar currículo" in r.text


def test_pagina_curriculo_exibe_texto_apos_gerar(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    _gerar_curriculo(client, sid)
    r = client.get(f"/alunos/{sid}/curriculo")
    assert r.status_code == 200
    assert "RESUMO" in r.text
    assert "Regenerar currículo" in r.text


def test_gerar_curriculo_redireciona_para_pagina_curriculo(client):
    sid = _criar_aluno(client)
    _enviar_mensagem(client, sid)
    _finalizar_triagem(client, sid)
    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        r = client.post(f"/alunos/{sid}/curriculo/gerar")
    assert r.status_code == 303
    assert r.headers["location"] == f"/alunos/{sid}/curriculo"


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------


def test_get_pagina_login(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "<form" in r.text


def test_get_pagina_login_quando_autenticado_redireciona(client):
    sid = _criar_aluno(client)
    r = client.get("/login")
    assert r.status_code == 303
    assert r.headers["location"] == f"/alunos/{sid}"


def test_login_com_credenciais_corretas_redireciona(client):
    sid = _criar_aluno(client, email="login@t.com")
    client.post("/logout")
    r = client.post("/login", data={"email": "login@t.com", "senha": "senha-segura-123"})
    assert r.status_code == 303
    assert r.headers["location"] == f"/alunos/{sid}"


def test_login_com_senha_incorreta_retorna_401(client):
    _criar_aluno(client, email="login2@t.com")
    client.post("/logout")
    r = client.post("/login", data={"email": "login2@t.com", "senha": "senha-errada"})
    assert r.status_code == 401
    assert "inválidos" in r.text


def test_login_com_email_inexistente_retorna_401(client):
    r = client.post("/login", data={"email": "naoexiste@t.com", "senha": "qualquer-senha"})
    assert r.status_code == 401


def test_logout_limpa_sessao(client):
    sid = _criar_aluno(client)
    r = client.post("/logout")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

    r2 = client.get(f"/alunos/{sid}")
    assert r2.status_code == 303
    assert r2.headers["location"] == "/login"
