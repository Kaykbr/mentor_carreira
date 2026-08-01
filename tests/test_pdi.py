"""Testes dos endpoints JSON de PDI."""

from unittest.mock import patch

from tests.conftest import PDI_FAKE, PERFIL_FAKE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_aluno(client):
    return client.post(
        "/students",
        json={"nome": "Bia", "email": "bia@t.com", "periodo": 5, "senha": "senha-segura-123"},
    ).json()


def _criar_aluno_com_perfil(client):
    from app.services import claude_client

    sid = _criar_aluno(client)["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        client.post(f"/triage/{sid}/finalizar")
    return sid


# ---------------------------------------------------------------------------
# POST /pdi/{id}/gerar
# ---------------------------------------------------------------------------


def test_gerar_pdi_retorna_200(client):
    sid = _criar_aluno_com_perfil(client)
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        r = client.post(f"/pdi/{sid}/gerar")
    assert r.status_code == 200


def test_gerar_pdi_retorna_estrutura_correta(client):
    sid = _criar_aluno_com_perfil(client)
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        r = client.post(f"/pdi/{sid}/gerar")
    data = r.json()
    assert data["student_id"] == sid
    pj = data["pdi_json"]
    for chave in ("objetivo_geral", "metas_curto_prazo", "metas_medio_prazo",
                  "competencias_a_desenvolver", "acoes_recomendadas", "cronograma"):
        assert chave in pj, f"Chave '{chave}' ausente no pdi_json"


def test_gerar_pdi_sem_perfil_retorna_400(client):
    sid = _criar_aluno(client)["id"]
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        r = client.post(f"/pdi/{sid}/gerar")
    assert r.status_code == 400
    assert "triagem" in r.json()["detail"].lower()


def test_gerar_pdi_sem_sessao_retorna_401(client):
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        r = client.post("/pdi/9999/gerar")
    assert r.status_code == 401


def test_gerar_pdi_recebe_profile_json_correto(client):
    """O claude_client.gerar_pdi deve receber o profile_json salvo do aluno."""
    sid = _criar_aluno_com_perfil(client)
    perfil_recebido = []

    def _fake(profile_json, contexto_aluno=None):
        perfil_recebido.append(profile_json)
        return PDI_FAKE

    with patch("app.services.claude_client.gerar_pdi", side_effect=_fake):
        client.post(f"/pdi/{sid}/gerar")

    assert perfil_recebido[0]["resumo_geral"] == PERFIL_FAKE["resumo_geral"]


def test_gerar_pdi_duas_vezes_atualiza_existente(client):
    sid = _criar_aluno_com_perfil(client)
    pdi_v2 = {**PDI_FAKE, "objetivo_geral": "Objetivo atualizado"}

    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        client.post(f"/pdi/{sid}/gerar")
    with patch("app.services.claude_client.gerar_pdi", return_value=pdi_v2):
        r = client.post(f"/pdi/{sid}/gerar")

    assert r.json()["pdi_json"]["objetivo_geral"] == "Objetivo atualizado"


# ---------------------------------------------------------------------------
# GET /pdi/{id}
# ---------------------------------------------------------------------------


def test_obter_pdi_existente_retorna_200(client):
    sid = _criar_aluno_com_perfil(client)
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        client.post(f"/pdi/{sid}/gerar")
    r = client.get(f"/pdi/{sid}")
    assert r.status_code == 200
    assert r.json()["pdi_json"]["objetivo_geral"] == PDI_FAKE["objetivo_geral"]


def test_obter_pdi_inexistente_retorna_404(client):
    sid = _criar_aluno_com_perfil(client)
    r = client.get(f"/pdi/{sid}")
    assert r.status_code == 404


def test_obter_pdi_sem_sessao_retorna_401(client):
    r = client.get("/pdi/9999")
    assert r.status_code == 401
