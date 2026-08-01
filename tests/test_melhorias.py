"""Testes das melhorias de segurança/qualidade (headers, config, e-mail normalizado)."""

import pytest
from pydantic import ValidationError

from app.config import SECRET_KEY_INSEGURA, Settings


# ---------------------------------------------------------------------------
# Headers de segurança (middleware em main.py)
# ---------------------------------------------------------------------------


def test_headers_seguranca_presentes(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "same-origin"


def test_headers_seguranca_em_pagina_html(client):
    r = client.get("/login")
    assert r.headers["x-content-type-options"] == "nosniff"


# ---------------------------------------------------------------------------
# Validação de configuração de produção (app/config.py)
# ---------------------------------------------------------------------------


def test_producao_rejeita_secret_key_padrao():
    with pytest.raises(ValidationError):
        Settings(app_env="production", anthropic_api_key="x", secret_key=SECRET_KEY_INSEGURA)


def test_producao_ativa_cookie_secure_por_padrao():
    s = Settings(app_env="production", anthropic_api_key="x", secret_key="chave-bem-forte-1234567890")
    assert s.session_https_only is True


def test_producao_respeita_override_de_https_only():
    s = Settings(
        app_env="production",
        anthropic_api_key="x",
        secret_key="chave-bem-forte-1234567890",
        session_https_only=False,
    )
    assert s.session_https_only is False


def test_desenvolvimento_nao_exige_https_only():
    s = Settings(app_env="development", anthropic_api_key="x", secret_key=SECRET_KEY_INSEGURA)
    assert s.session_https_only is False


# ---------------------------------------------------------------------------
# E-mail case-insensitive (student_service.normalizar_email)
# ---------------------------------------------------------------------------


def test_cadastro_normaliza_email_para_minusculas(client):
    r = client.post(
        "/students",
        json={"nome": "Maria", "email": "Maria@Email.COM", "periodo": 1, "senha": "senha-super-secreta"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "maria@email.com"


def test_login_json_email_case_insensitive(client):
    client.post(
        "/students",
        json={"nome": "Caso", "email": "caso@example.com", "periodo": 2, "senha": "senha-super-secreta"},
    )
    client.post("/auth/logout")

    r = client.post("/auth/login", json={"email": "CaSo@Example.Com", "senha": "senha-super-secreta"})
    assert r.status_code == 200
    assert r.json()["email"] == "caso@example.com"


def test_cadastro_email_duplicado_ignora_capitalizacao(client):
    client.post(
        "/students",
        json={"nome": "A", "email": "dup@example.com", "periodo": 1, "senha": "senha-super-secreta"},
    )
    r = client.post(
        "/students",
        json={"nome": "B", "email": "DUP@example.com", "periodo": 1, "senha": "senha-super-secreta"},
    )
    assert r.status_code == 409
