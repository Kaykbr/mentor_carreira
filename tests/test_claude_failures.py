"""Testes do comportamento do sistema quando a API da Anthropic falha.

Falhas da API (rate limit, conexão, 5xx) viram **503** com mensagem amigável
("mentor indisponível"); exceções genéricas e respostas malformadas viram **500**.
Nenhum caso expõe traceback ao usuário.

Usa o fixture `error_client` (raise_server_exceptions=False) para poder verificar
o código de status de exceções não tratadas sem que o TestClient as re-levante.
"""

from unittest.mock import patch

import anthropic
import pytest

from tests.conftest import PERFIL_FAKE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_aluno(client):
    return client.post(
        "/students",
        json={"nome": "Erro", "email": "erro@t.com", "periodo": 3, "senha": "senha-segura-123"},
    ).json()


def _criar_aluno_com_mensagem(error_client):
    from app.services import claude_client

    sid = _criar_aluno(error_client)["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    return sid


# ---------------------------------------------------------------------------
# POST /triage/{id}/mensagens — falha na chamada ao Claude
# ---------------------------------------------------------------------------


def test_enviar_mensagem_quando_claude_levanta_exception_retorna_500(error_client):
    """Se conversar_triagem lançar Exception genérica, a API deve retornar 500."""
    sid = _criar_aluno(error_client)["id"]
    with patch("app.services.claude_client.conversar_triagem", side_effect=Exception("API offline")):
        r = error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    assert r.status_code == 500


def test_enviar_mensagem_quando_rate_limit_retorna_503(error_client):
    """RateLimitError (após esgotar retries) vira 503 'mentor indisponível', não 500."""
    from unittest.mock import MagicMock

    sid = _criar_aluno(error_client)["id"]
    # Cria um mock de response HTTP compatível com o construtor do RateLimitError
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.request = MagicMock()
    erro = anthropic.RateLimitError(message="rate limit", response=mock_response, body=None)

    # tenacity tenta 3x e reraise — o handler de anthropic.APIError converte em 503
    with patch("app.services.claude_client.conversar_triagem", side_effect=erro):
        r = error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    assert r.status_code == 503
    assert "mentor" in r.json()["detail"].lower()


def test_enviar_mensagem_quando_conexao_falha_retorna_503(error_client):
    """Falha de conexão/timeout com a API também vira 503 amigável."""
    from unittest.mock import MagicMock

    sid = _criar_aluno(error_client)["id"]
    erro = anthropic.APIConnectionError(request=MagicMock())

    with patch("app.services.claude_client.conversar_triagem", side_effect=erro):
        r = error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    assert r.status_code == 503
    assert "detail" in r.json()


# ---------------------------------------------------------------------------
# POST /triage/{id}/finalizar — falha ao gerar perfil
# ---------------------------------------------------------------------------


def test_finalizar_quando_claude_levanta_exception_retorna_500(error_client):
    """Se gerar_perfil_estruturado lançar Exception, a API deve retornar 500."""
    sid = _criar_aluno_com_mensagem(error_client)
    with patch(
        "app.services.claude_client.gerar_perfil_estruturado",
        side_effect=Exception("timeout"),
    ):
        r = error_client.post(f"/triage/{sid}/finalizar")
    assert r.status_code == 500


def test_finalizar_quando_claude_retorna_sem_tool_use_retorna_500(error_client):
    """RuntimeError de resposta malformada (sem tool_use) deve virar HTTP 500."""
    sid = _criar_aluno_com_mensagem(error_client)
    with patch(
        "app.services.claude_client.gerar_perfil_estruturado",
        side_effect=RuntimeError("Claude não retornou o bloco 'tool_use' esperado ao gerar perfil."),
    ):
        r = error_client.post(f"/triage/{sid}/finalizar")
    assert r.status_code == 500


def test_resposta_500_contem_mensagem_legivel(error_client):
    """O corpo da resposta 500 deve ter um campo 'detail' com mensagem ao usuário."""
    sid = _criar_aluno(error_client)["id"]
    with patch("app.services.claude_client.conversar_triagem", side_effect=Exception("crash")):
        r = error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    assert r.status_code == 500
    assert "detail" in r.json()
    # Deve ser uma mensagem amigável, não o traceback bruto
    assert "Erro interno" in r.json()["detail"]


# ---------------------------------------------------------------------------
# POST /pdi/{id}/gerar — falha ao gerar PDI
# ---------------------------------------------------------------------------


def test_gerar_pdi_quando_claude_levanta_exception_retorna_500(error_client):
    """Se gerar_pdi lançar Exception, a API deve retornar 500."""
    from app.services import claude_client

    sid = _criar_aluno(error_client)["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        error_client.post(f"/triage/{sid}/finalizar")

    with patch("app.services.claude_client.gerar_pdi", side_effect=Exception("Falha de rede")):
        r = error_client.post(f"/pdi/{sid}/gerar")
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# POST /curriculum/{id}/gerar — falha ao gerar currículo
# ---------------------------------------------------------------------------


def test_gerar_curriculo_quando_claude_levanta_exception_retorna_500(error_client):
    """Se gerar_curriculo lançar Exception, a API deve retornar 500."""
    from app.services import claude_client

    sid = _criar_aluno(error_client)["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        error_client.post(f"/triage/{sid}/finalizar")

    with patch("app.services.claude_client.gerar_curriculo", side_effect=Exception("Timeout")):
        r = error_client.post(f"/curriculum/{sid}/gerar")
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Mensagem de erro do RuntimeError é descritiva (testes unitários — sem HTTP)
# ---------------------------------------------------------------------------


def test_runtime_error_perfil_contem_contexto():
    """Verifica que o RuntimeError gerado pelo claude_client tem mensagem informativa."""
    from app.services.claude_client import gerar_perfil_estruturado

    class FakeBloco:
        type = "text"
        text = "Desculpe, não consigo responder agora."

    class FakeResposta:
        content = [FakeBloco()]

    with patch("app.services.claude_client._cliente") as mock_cliente:
        mock_cliente.return_value.messages.create.return_value = FakeResposta()
        with pytest.raises(RuntimeError, match="tool_use"):
            gerar_perfil_estruturado([{"role": "user", "content": "Oi"}])


def test_runtime_error_pdi_contem_contexto():
    """Verifica que o RuntimeError do PDI tem mensagem informativa sobre tool_use."""
    from app.services.claude_client import gerar_pdi

    class FakeBloco:
        type = "text"
        text = "Não consigo gerar."

    class FakeResposta:
        content = [FakeBloco()]

    with patch("app.services.claude_client._cliente") as mock_cliente:
        mock_cliente.return_value.messages.create.return_value = FakeResposta()
        with pytest.raises(RuntimeError, match="tool_use"):
            gerar_pdi({"objetivo_carreira": {}})
