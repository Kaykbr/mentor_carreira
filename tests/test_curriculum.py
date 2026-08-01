"""Testes dos endpoints JSON de currículo."""

from unittest.mock import patch

from tests.conftest import CURRICULO_FAKE, PDI_FAKE, PERFIL_FAKE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_aluno(client):
    return client.post(
        "/students",
        json={"nome": "Pedro", "email": "pedro@t.com", "periodo": 6, "senha": "senha-segura-123"},
    ).json()


def _criar_aluno_com_perfil(client):
    from app.services import claude_client

    sid = _criar_aluno(client)["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        client.post(f"/triage/{sid}/finalizar")
    return sid


def _criar_aluno_com_perfil_e_pdi(client):
    sid = _criar_aluno_com_perfil(client)
    with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
        client.post(f"/pdi/{sid}/gerar")
    return sid


# ---------------------------------------------------------------------------
# POST /curriculum/{id}/gerar
# ---------------------------------------------------------------------------


def test_gerar_curriculo_retorna_200(client):
    sid = _criar_aluno_com_perfil(client)
    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        r = client.post(f"/curriculum/{sid}/gerar")
    assert r.status_code == 200


def test_gerar_curriculo_retorna_texto(client):
    sid = _criar_aluno_com_perfil(client)
    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        r = client.post(f"/curriculum/{sid}/gerar")
    data = r.json()
    assert data["student_id"] == sid
    assert data["curriculum_text"] == CURRICULO_FAKE


def test_gerar_curriculo_sem_perfil_retorna_400(client):
    sid = _criar_aluno(client)["id"]
    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        r = client.post(f"/curriculum/{sid}/gerar")
    assert r.status_code == 400


def test_gerar_curriculo_sem_sessao_retorna_401(client):
    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        r = client.post("/curriculum/9999/gerar")
    assert r.status_code == 401


def test_gerar_curriculo_sem_pdi_passa_none_para_claude(client):
    """Sem PDI gerado, o claude_client deve receber pdi_json=None."""
    sid = _criar_aluno_com_perfil(client)
    chamadas = []

    def _fake(profile_json, pdi_json=None, contexto_aluno=None):
        chamadas.append(pdi_json)
        return CURRICULO_FAKE

    with patch("app.services.claude_client.gerar_curriculo", side_effect=_fake):
        client.post(f"/curriculum/{sid}/gerar")

    assert chamadas[0] is None


def test_gerar_curriculo_com_pdi_passa_pdi_para_claude(client):
    """Com PDI gerado, o claude_client deve receber o pdi_json correto."""
    sid = _criar_aluno_com_perfil_e_pdi(client)
    chamadas = []

    def _fake(profile_json, pdi_json=None, contexto_aluno=None):
        chamadas.append(pdi_json)
        return CURRICULO_FAKE

    with patch("app.services.claude_client.gerar_curriculo", side_effect=_fake):
        client.post(f"/curriculum/{sid}/gerar")

    assert chamadas[0] is not None
    assert chamadas[0]["objetivo_geral"] == PDI_FAKE["objetivo_geral"]


def test_gerar_curriculo_duas_vezes_atualiza_existente(client):
    sid = _criar_aluno_com_perfil(client)
    curriculo_v2 = "RESUMO\nTexto atualizado."

    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        client.post(f"/curriculum/{sid}/gerar")
    with patch("app.services.claude_client.gerar_curriculo", return_value=curriculo_v2):
        r = client.post(f"/curriculum/{sid}/gerar")

    assert r.json()["curriculum_text"] == curriculo_v2


# ---------------------------------------------------------------------------
# GET /curriculum/{id}
# ---------------------------------------------------------------------------


def test_obter_curriculo_existente_retorna_200(client):
    sid = _criar_aluno_com_perfil(client)
    with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
        client.post(f"/curriculum/{sid}/gerar")
    r = client.get(f"/curriculum/{sid}")
    assert r.status_code == 200
    assert r.json()["curriculum_text"] == CURRICULO_FAKE


def test_obter_curriculo_inexistente_retorna_404(client):
    sid = _criar_aluno_com_perfil(client)
    r = client.get(f"/curriculum/{sid}")
    assert r.status_code == 404


def test_obter_curriculo_sem_sessao_retorna_401(client):
    r = client.get("/curriculum/9999")
    assert r.status_code == 401
