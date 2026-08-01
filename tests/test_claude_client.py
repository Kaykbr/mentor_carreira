"""Testes unitários do `claude_client`: modelo por operação e personalização da triagem.

Não fazem chamadas HTTP — mockam `_cliente()` diretamente (mesmo padrão usado em
`tests/test_claude_failures.py`) e inspecionam os argumentos passados para
`messages.create`.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app.config import get_settings
from app.services.claude_client import (
    PROMPT_SISTEMA_TRIAGEM,
    conversar_triagem,
    gerar_curriculo,
    gerar_pdi,
    gerar_perfil_estruturado,
)


class _FakeBlocoTexto:
    type = "text"

    def __init__(self, texto: str):
        self.text = texto


class _FakeBlocoToolUse:
    type = "tool_use"

    def __init__(self, input_: dict):
        self.input = input_


class _FakeResposta:
    def __init__(self, content):
        self.content = content


@contextmanager
def _cliente_mockado(content):
    """Faz `_cliente().messages.create(...)` retornar uma resposta fake e expõe o mock."""
    with patch("app.services.claude_client._cliente") as mock_cliente:
        mock_cliente.return_value.messages.create.return_value = _FakeResposta(content)
        yield mock_cliente


@pytest.fixture
def _override_modelo(monkeypatch):
    """Define uma variável de ambiente de modelo e força releitura de `get_settings`."""

    def _set(nome: str, valor: str) -> None:
        monkeypatch.setenv(nome, valor)
        get_settings.cache_clear()

    yield _set
    get_settings.cache_clear()


HISTORICO = [{"role": "user", "content": "Oi"}]
PERFIL_MINIMO = {"resumo_geral": "Aluno dedicado"}


# ---------------------------------------------------------------------------
# Sem overrides: todas as operações usam CLAUDE_MODEL
# ---------------------------------------------------------------------------


def test_sem_overrides_todas_operacoes_usam_claude_model():
    modelo_padrao = get_settings().claude_model

    with _cliente_mockado([_FakeBlocoTexto("Olá!")]) as mock_cliente:
        conversar_triagem(HISTORICO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao

    with _cliente_mockado([_FakeBlocoToolUse(PERFIL_MINIMO)]) as mock_cliente:
        gerar_perfil_estruturado(HISTORICO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao

    with _cliente_mockado([_FakeBlocoToolUse({"objetivo_geral": "Crescer"})]) as mock_cliente:
        gerar_pdi(PERFIL_MINIMO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao

    with _cliente_mockado([_FakeBlocoTexto("RESUMO\nTexto")]) as mock_cliente:
        gerar_curriculo(PERFIL_MINIMO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao


# ---------------------------------------------------------------------------
# CLAUDE_MODEL_ANALISE: usado apenas na extração de perfil
# ---------------------------------------------------------------------------


def test_claude_model_analise_usado_apenas_no_perfil(_override_modelo):
    _override_modelo("CLAUDE_MODEL_ANALISE", "claude-haiku-4-5")
    modelo_padrao = get_settings().claude_model

    with _cliente_mockado([_FakeBlocoToolUse(PERFIL_MINIMO)]) as mock_cliente:
        gerar_perfil_estruturado(HISTORICO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"

    with _cliente_mockado([_FakeBlocoTexto("Olá!")]) as mock_cliente:
        conversar_triagem(HISTORICO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao

    with _cliente_mockado([_FakeBlocoToolUse({"objetivo_geral": "Crescer"})]) as mock_cliente:
        gerar_pdi(PERFIL_MINIMO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao

    with _cliente_mockado([_FakeBlocoTexto("RESUMO\nTexto")]) as mock_cliente:
        gerar_curriculo(PERFIL_MINIMO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao


# ---------------------------------------------------------------------------
# CLAUDE_MODEL_GERACAO: usado em PDI e currículo
# ---------------------------------------------------------------------------


def test_claude_model_geracao_usado_em_pdi_e_curriculo(_override_modelo):
    _override_modelo("CLAUDE_MODEL_GERACAO", "claude-opus-4-8")
    modelo_padrao = get_settings().claude_model

    with _cliente_mockado([_FakeBlocoToolUse({"objetivo_geral": "Crescer"})]) as mock_cliente:
        gerar_pdi(PERFIL_MINIMO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"

    with _cliente_mockado([_FakeBlocoTexto("RESUMO\nTexto")]) as mock_cliente:
        gerar_curriculo(PERFIL_MINIMO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"

    with _cliente_mockado([_FakeBlocoTexto("Olá!")]) as mock_cliente:
        conversar_triagem(HISTORICO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao

    with _cliente_mockado([_FakeBlocoToolUse(PERFIL_MINIMO)]) as mock_cliente:
        gerar_perfil_estruturado(HISTORICO)
    assert mock_cliente.return_value.messages.create.call_args.kwargs["model"] == modelo_padrao


# ---------------------------------------------------------------------------
# Personalização do prompt da triagem com o nome do aluno
# ---------------------------------------------------------------------------


def test_conversar_triagem_personaliza_prompt_com_nome_do_aluno():
    with _cliente_mockado([_FakeBlocoTexto("Olá, Ana!")]) as mock_cliente:
        conversar_triagem(HISTORICO, nome_aluno="Ana")

    system = mock_cliente.return_value.messages.create.call_args.kwargs["system"]
    assert "Ana" in system
    assert system.startswith(PROMPT_SISTEMA_TRIAGEM)


def test_conversar_triagem_sem_nome_usa_prompt_padrao():
    with _cliente_mockado([_FakeBlocoTexto("Olá!")]) as mock_cliente:
        conversar_triagem(HISTORICO)

    system = mock_cliente.return_value.messages.create.call_args.kwargs["system"]
    assert system == PROMPT_SISTEMA_TRIAGEM
