"""Testes de autenticação (auth_service, /auth/*) e autorização cruzada entre alunos."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services import auth_service, student_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_aluno(client, email="auth@t.com", senha="senha-segura-123", nome="Auth"):
    return client.post(
        "/students",
        json={"nome": nome, "email": email, "periodo": 2, "senha": senha},
    ).json()


@pytest.fixture
def two_clients(db_session):
    """Dois TestClients independentes (cookies separados) compartilhando o mesmo banco."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, follow_redirects=False) as client_a, TestClient(app, follow_redirects=False) as client_b:
        yield client_a, client_b
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# auth_service: hashing e verificação de senha
# ---------------------------------------------------------------------------


def test_gerar_hash_senha_difere_da_senha_original():
    h = auth_service.gerar_hash_senha("minha-senha-123")
    assert h != "minha-senha-123"


def test_verificar_senha_correta_retorna_true():
    h = auth_service.gerar_hash_senha("minha-senha-123")
    assert auth_service.verificar_senha("minha-senha-123", h) is True


def test_verificar_senha_incorreta_retorna_false():
    h = auth_service.gerar_hash_senha("minha-senha-123")
    assert auth_service.verificar_senha("senha-errada", h) is False


def test_autenticar_aluno_credenciais_validas(db_session):
    aluno = student_service.criar_aluno(
        db_session,
        nome="Fulano",
        email="fulano@t.com",
        periodo=1,
        password_hash=auth_service.gerar_hash_senha("senha-123456"),
    )
    resultado = auth_service.autenticar_aluno(db_session, "fulano@t.com", "senha-123456")
    assert resultado is not None
    assert resultado.id == aluno.id


def test_autenticar_aluno_senha_incorreta_retorna_none(db_session):
    student_service.criar_aluno(
        db_session,
        nome="Ciclano",
        email="ciclano@t.com",
        periodo=1,
        password_hash=auth_service.gerar_hash_senha("senha-123456"),
    )
    assert auth_service.autenticar_aluno(db_session, "ciclano@t.com", "senha-errada") is None


def test_autenticar_aluno_email_inexistente_retorna_none(db_session):
    assert auth_service.autenticar_aluno(db_session, "naoexiste@t.com", "qualquer-senha") is None


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


def test_login_com_credenciais_corretas_retorna_200(client):
    aluno = _criar_aluno(client)
    client.post("/auth/logout")

    r = client.post("/auth/login", json={"email": "auth@t.com", "senha": "senha-segura-123"})
    assert r.status_code == 200
    assert r.json()["id"] == aluno["id"]


def test_login_com_senha_invalida_retorna_401(client):
    _criar_aluno(client, email="auth2@t.com")
    client.post("/auth/logout")

    r = client.post("/auth/login", json={"email": "auth2@t.com", "senha": "senha-errada"})
    assert r.status_code == 401


def test_login_com_email_inexistente_retorna_401(client):
    r = client.post("/auth/login", json={"email": "naoexiste@t.com", "senha": "qualquer-senha"})
    assert r.status_code == 401


def test_login_inicia_sessao(client):
    aluno = _criar_aluno(client, email="auth3@t.com")
    client.post("/auth/logout")
    client.post("/auth/login", json={"email": "auth3@t.com", "senha": "senha-segura-123"})

    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["id"] == aluno["id"]


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


def test_logout_encerra_sessao(client):
    _criar_aluno(client)
    r = client.post("/auth/logout")
    assert r.status_code == 204

    r2 = client.get("/auth/me")
    assert r2.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


def test_me_sem_sessao_retorna_401(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_com_sessao_retorna_dados_do_aluno(client):
    aluno = _criar_aluno(client)
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == aluno["email"]


# ---------------------------------------------------------------------------
# Autorização cruzada entre alunos (cada um com sua própria sessão)
# ---------------------------------------------------------------------------


def test_autorizacao_cruzada_students(two_clients):
    client_a, client_b = two_clients
    aluno_a = _criar_aluno(client_a, email="a@cross.com", nome="A")
    aluno_b = _criar_aluno(client_b, email="b@cross.com", nome="B")

    # B não pode acessar dados de A, e vice-versa.
    assert client_b.get(f"/students/{aluno_a['id']}").status_code == 403
    assert client_a.get(f"/students/{aluno_b['id']}").status_code == 403

    # Cada um continua acessando os próprios dados normalmente.
    assert client_a.get(f"/students/{aluno_a['id']}").status_code == 200
    assert client_b.get(f"/students/{aluno_b['id']}").status_code == 200


def test_autorizacao_cruzada_triagem_pdi_curriculo(two_clients):
    from app.services import claude_client

    client_a, client_b = two_clients
    aluno_a = _criar_aluno(client_a, email="a2@cross.com", nome="A2")
    _criar_aluno(client_b, email="b2@cross.com", nome="B2")

    sid_a = aluno_a["id"]

    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        assert client_b.post(f"/triage/{sid_a}/mensagens", json={"mensagem": "Oi"}).status_code == 403
    assert client_b.get(f"/triage/{sid_a}/mensagens").status_code == 403
    assert client_b.post(f"/triage/{sid_a}/finalizar").status_code == 403
    assert client_b.post(f"/pdi/{sid_a}/gerar").status_code == 403
    assert client_b.get(f"/pdi/{sid_a}").status_code == 403
    assert client_b.post(f"/curriculum/{sid_a}/gerar").status_code == 403
    assert client_b.get(f"/curriculum/{sid_a}").status_code == 403


def test_autorizacao_cruzada_paginas_html(two_clients):
    client_a, client_b = two_clients
    aluno_a = _criar_aluno(client_a, email="a3@cross.com", nome="A3")
    _criar_aluno(client_b, email="b3@cross.com", nome="B3")

    sid_a = aluno_a["id"]
    assert client_b.get(f"/alunos/{sid_a}").status_code == 403
    assert client_b.get(f"/alunos/{sid_a}/triagem").status_code == 403
    assert client_b.get(f"/alunos/{sid_a}/perfil").status_code == 403
    assert client_b.get(f"/alunos/{sid_a}/pdi").status_code == 403
    assert client_b.get(f"/alunos/{sid_a}/curriculo").status_code == 403
