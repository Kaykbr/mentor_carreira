"""Testes dos endpoints JSON de alunos (CRUD) e autorização por aluno."""

import pytest

from tests.conftest import PERFIL_FAKE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAYLOAD_BASE = {
    "nome": "Ana Souza",
    "email": "ana@example.com",
    "periodo": 4,
    "senha": "senha-segura-123",
}


def _criar_aluno(client, payload: dict | None = None):
    """Cria um aluno via API e retorna o JSON de resposta.

    Como o cadastro inicia a sessão automaticamente, o `client` passa a ficar
    autenticado como o aluno recém-criado.
    """
    return client.post("/students", json=payload or _PAYLOAD_BASE)


# ---------------------------------------------------------------------------
# POST /students
# ---------------------------------------------------------------------------


def test_cadastrar_aluno_retorna_201(client):
    r = _criar_aluno(client)
    assert r.status_code == 201


def test_cadastrar_aluno_campos_corretos(client):
    r = _criar_aluno(client)
    data = r.json()
    assert data["nome"] == "Ana Souza"
    assert data["email"] == "ana@example.com"
    assert data["periodo"] == 4
    assert data["curso"] == "Sistemas de Informação"
    assert "id" in data
    assert "created_at" in data
    assert "senha" not in data
    assert "password_hash" not in data


def test_cadastrar_aluno_curso_sempre_fixo(client):
    """O campo curso não deve ser alterável pelo cliente."""
    r = _criar_aluno(client)
    assert r.json()["curso"] == "Sistemas de Informação"


def test_cadastrar_aluno_inicia_sessao(client):
    """O cadastro deve logar automaticamente o aluno (cookie de sessão)."""
    sid = _criar_aluno(client).json()["id"]
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_cadastrar_aluno_email_duplicado_retorna_409(client):
    _criar_aluno(client)
    r = _criar_aluno(client)  # mesmo e-mail
    assert r.status_code == 409
    assert "e-mail" in r.json()["detail"].lower()


def test_cadastrar_aluno_email_invalido_retorna_422(client):
    r = _criar_aluno(client, {**_PAYLOAD_BASE, "email": "nao-e-um-email"})
    assert r.status_code == 422


def test_cadastrar_aluno_sem_nome_retorna_422(client):
    r = client.post("/students", json={"email": "x@x.com", "periodo": 1, "senha": "senha-segura-123"})
    assert r.status_code == 422


def test_cadastrar_aluno_sem_periodo_retorna_422(client):
    r = client.post("/students", json={"nome": "X", "email": "x@x.com", "senha": "senha-segura-123"})
    assert r.status_code == 422


def test_cadastrar_aluno_periodo_negativo_retorna_422(client):
    """Período deve ser >= 1 (Field ge=1)."""
    r = client.post("/students", json={**_PAYLOAD_BASE, "periodo": -1})
    assert r.status_code == 422


def test_cadastrar_aluno_periodo_zero_retorna_422(client):
    """Período zero não é válido."""
    r = client.post("/students", json={**_PAYLOAD_BASE, "periodo": 0})
    assert r.status_code == 422


def test_cadastrar_aluno_periodo_acima_do_limite_retorna_422(client):
    """Período deve ser <= 12 (Field le=12)."""
    r = client.post("/students", json={**_PAYLOAD_BASE, "periodo": 13})
    assert r.status_code == 422


def test_cadastrar_aluno_nome_vazio_retorna_422(client):
    """Nome vazio não deve ser aceito (Field min_length=1)."""
    r = client.post("/students", json={**_PAYLOAD_BASE, "nome": ""})
    assert r.status_code == 422


def test_cadastrar_aluno_sem_senha_retorna_422(client):
    payload = {k: v for k, v in _PAYLOAD_BASE.items() if k != "senha"}
    r = client.post("/students", json=payload)
    assert r.status_code == 422


def test_cadastrar_aluno_senha_curta_retorna_422(client):
    """Senha deve ter ao menos 8 caracteres (Field min_length=8)."""
    r = client.post("/students", json={**_PAYLOAD_BASE, "senha": "1234567"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /students/{id}
# ---------------------------------------------------------------------------


def test_obter_aluno_sem_sessao_retorna_401(client):
    r = client.get("/students/1")
    assert r.status_code == 401


def test_obter_aluno_proprio_retorna_200(aluno_logado, client):
    sid = aluno_logado["id"]
    r = client.get(f"/students/{sid}")
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_obter_aluno_de_outro_aluno_retorna_403(client):
    sid_a = _criar_aluno(client, {**_PAYLOAD_BASE, "email": "a@a.com"}).json()["id"]
    # Cadastra (e loga como) um segundo aluno, substituindo a sessão do primeiro.
    _criar_aluno(client, {**_PAYLOAD_BASE, "email": "b@b.com"})

    r = client.get(f"/students/{sid_a}")
    assert r.status_code == 403


def test_obter_aluno_inexistente_com_sessao_retorna_403(aluno_logado, client):
    """Um id inexistente não revela essa informação: aparece como 403, não 404."""
    r = client.get("/students/9999")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /students/{id}/profile
# ---------------------------------------------------------------------------


def test_obter_perfil_sem_sessao_retorna_401(client):
    r = client.get("/students/1/profile")
    assert r.status_code == 401


def test_obter_perfil_sem_triagem_retorna_404(aluno_logado, client):
    sid = aluno_logado["id"]
    r = client.get(f"/students/{sid}/profile")
    assert r.status_code == 404


def test_obter_perfil_apos_triagem_retorna_200(aluno_logado, client):
    from unittest.mock import patch
    from app.services import claude_client

    sid = aluno_logado["id"]

    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Olá"})

    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        client.post(f"/triage/{sid}/finalizar")

    r = client.get(f"/students/{sid}/profile")
    assert r.status_code == 200
    data = r.json()
    assert data["student_id"] == sid
    assert "objetivo_carreira" in data["profile_json"]


def test_obter_perfil_de_outro_aluno_retorna_403(client):
    sid_a = _criar_aluno(client, {**_PAYLOAD_BASE, "email": "a@a.com"}).json()["id"]
    _criar_aluno(client, {**_PAYLOAD_BASE, "email": "b@b.com"})

    r = client.get(f"/students/{sid_a}/profile")
    assert r.status_code == 403
