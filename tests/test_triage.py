"""Testes dos endpoints JSON de triagem."""

from unittest.mock import call, patch

from tests.conftest import PERFIL_FAKE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_aluno(client):
    return client.post(
        "/students",
        json={"nome": "Carlos", "email": "carlos@t.com", "periodo": 3, "senha": "senha-segura-123"},
    ).json()


def _enviar_mensagem(client, sid, texto="Olá, quero começar"):
    from app.services import claude_client

    with patch.object(claude_client, "conversar_triagem", return_value="Entendido!"):
        return client.post(f"/triage/{sid}/mensagens", json={"mensagem": texto})


# ---------------------------------------------------------------------------
# POST /triage/{id}/mensagens
# ---------------------------------------------------------------------------


def test_enviar_mensagem_retorna_200(client):
    sid = _criar_aluno(client)["id"]
    r = _enviar_mensagem(client, sid)
    assert r.status_code == 200


def test_enviar_mensagem_retorna_resposta(client):
    from app.services import claude_client

    sid = _criar_aluno(client)["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Qual seu objetivo?"):
        r = client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    assert r.json()["resposta"] == "Qual seu objetivo?"


def test_enviar_mensagem_sem_sessao_retorna_401(client):
    from app.services import claude_client

    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        r = client.post("/triage/9999/mensagens", json={"mensagem": "Oi"})
    assert r.status_code == 401


def test_enviar_mensagem_passa_nome_do_aluno_ao_claude(client):
    """O nome do aluno cadastrado é repassado a `conversar_triagem` para personalizar o prompt."""
    from app.services import claude_client

    sid = _criar_aluno(client)["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok") as mock_conversar:
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})

    assert mock_conversar.call_args.kwargs["nome_aluno"] == "Carlos"


def test_enviar_mensagem_outro_aluno_retorna_403(client):
    from app.services import claude_client

    sid_a = _criar_aluno(client)["id"]
    client.post(
        "/students",
        json={"nome": "Outro", "email": "outro@t.com", "periodo": 2, "senha": "senha-segura-123"},
    )

    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        r = client.post(f"/triage/{sid_a}/mensagens", json={"mensagem": "Oi"})
    assert r.status_code == 403


def test_enviar_mensagem_vazia_retorna_422(client):
    """Mensagem com string vazia deve ser rejeitada pela validação Pydantic (min_length=1)."""
    sid = _criar_aluno(client)["id"]
    r = client.post(f"/triage/{sid}/mensagens", json={"mensagem": ""})
    assert r.status_code == 422


def test_enviar_mensagem_muito_longa_retorna_422(client):
    """Mensagem acima de 5000 caracteres deve ser rejeitada (max_length=5000)."""
    sid = _criar_aluno(client)["id"]
    r = client.post(f"/triage/{sid}/mensagens", json={"mensagem": "x" * 5001})
    assert r.status_code == 422


def test_enviar_mensagem_apenas_espacos_retorna_422(client):
    """Mensagem composta só de espaços é rejeitada pelo validador do schema."""
    sid = _criar_aluno(client)["id"]
    r = client.post(f"/triage/{sid}/mensagens", json={"mensagem": "   "})
    assert r.status_code == 422


def test_limite_de_mensagens_da_triagem_retorna_400(client, monkeypatch):
    """Ao atingir o limite de mensagens, o aluno é orientado a finalizar (400)."""
    from app.services import profile_service

    monkeypatch.setattr(profile_service, "LIMITE_MENSAGENS_TRIAGEM", 2)
    sid = _criar_aluno(client)["id"]
    _enviar_mensagem(client, sid, "Primeira")  # grava user + assistant = 2 mensagens

    r = _enviar_mensagem(client, sid, "Segunda")
    assert r.status_code == 400
    assert "limite" in r.json()["detail"].lower()


def test_chat_se_recupera_apos_falha_do_claude(error_client):
    """Falha do Claude após gravar a mensagem do aluno não pode quebrar o chat.

    A 1ª tentativa deixa duas mensagens 'user' consecutivas no banco; a sanitização
    do histórico as funde em um único turno, mantendo os papéis alternados que a
    API exige — o próximo envio funciona normalmente.
    """
    from app.services import claude_client

    sid = _criar_aluno(error_client)["id"]

    with patch.object(claude_client, "conversar_triagem", side_effect=Exception("boom")):
        r1 = error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi, mentor!"})
    assert r1.status_code == 500

    capturado = []

    def _fake(historico, nome_aluno=None):
        capturado.append(historico)
        return "Tudo certo, vamos continuar!"

    with patch.object(claude_client, "conversar_triagem", side_effect=_fake):
        r2 = error_client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Ainda está aí?"})

    assert r2.status_code == 200
    roles = [m["role"] for m in capturado[0]]
    assert roles == ["user"]  # um único turno de user (mensagens fundidas)
    assert "Oi, mentor!" in capturado[0][0]["content"]
    assert "Ainda está aí?" in capturado[0][0]["content"]


def test_claude_recebe_historico_acumulado(client):
    """A cada nova mensagem, o Claude deve receber o histórico completo até aquele ponto."""
    from app.services import claude_client

    sid = _criar_aluno(client)["id"]
    historicos_recebidos = []

    def _fake_chat(historico, nome_aluno=None):
        historicos_recebidos.append(historico)
        return "Ok"

    with patch.object(claude_client, "conversar_triagem", side_effect=_fake_chat):
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Msg 1"})
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Msg 2"})

    # 1ª chamada: 1 mensagem de user
    assert len(historicos_recebidos[0]) == 1
    assert historicos_recebidos[0][0]["role"] == "user"

    # 2ª chamada: user + assistant + user
    assert len(historicos_recebidos[1]) == 3
    assert historicos_recebidos[1][2]["role"] == "user"
    assert historicos_recebidos[1][2]["content"] == "Msg 2"


# ---------------------------------------------------------------------------
# GET /triage/{id}/mensagens
# ---------------------------------------------------------------------------


def test_listar_mensagens_vazio(client):
    sid = _criar_aluno(client)["id"]
    r = client.get(f"/triage/{sid}/mensagens")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_mensagens_apos_envio(client):
    sid = _criar_aluno(client)["id"]
    _enviar_mensagem(client, sid, "Quero backend")
    r = client.get(f"/triage/{sid}/mensagens")
    mensagens = r.json()
    assert len(mensagens) == 2  # user + assistant
    assert mensagens[0]["role"] == "user"
    assert mensagens[0]["content"] == "Quero backend"
    assert mensagens[1]["role"] == "assistant"


def test_listar_mensagens_ordem_cronologica(client):
    sid = _criar_aluno(client)["id"]
    _enviar_mensagem(client, sid, "Primeira")
    _enviar_mensagem(client, sid, "Segunda")
    msgs = client.get(f"/triage/{sid}/mensagens").json()
    conteudos_user = [m["content"] for m in msgs if m["role"] == "user"]
    assert conteudos_user == ["Primeira", "Segunda"]


def test_listar_mensagens_sem_sessao_retorna_401(client):
    r = client.get("/triage/9999/mensagens")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /triage/{id}/finalizar
# ---------------------------------------------------------------------------


def test_finalizar_triagem_retorna_perfil(client):
    sid = _criar_aluno(client)["id"]
    _enviar_mensagem(client, sid)

    from app.services import claude_client

    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        r = client.post(f"/triage/{sid}/finalizar")

    assert r.status_code == 200
    data = r.json()
    assert data["student_id"] == sid
    assert data["profile_json"]["resumo_geral"] == PERFIL_FAKE["resumo_geral"]


def test_finalizar_triagem_sem_mensagens_retorna_400(client):
    sid = _criar_aluno(client)["id"]
    r = client.post(f"/triage/{sid}/finalizar")
    assert r.status_code == 400


def test_finalizar_triagem_sem_sessao_retorna_401(client):
    from app.services import claude_client

    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        r = client.post("/triage/9999/finalizar")
    assert r.status_code == 401


def test_finalizar_triagem_duas_vezes_atualiza_perfil(client):
    """Chamar finalizar duas vezes deve atualizar o perfil existente, não duplicar."""
    from app.services import claude_client

    sid = _criar_aluno(client)["id"]
    _enviar_mensagem(client, sid)

    perfil_v2 = {**PERFIL_FAKE, "resumo_geral": "Versão atualizada do perfil."}

    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        client.post(f"/triage/{sid}/finalizar")

    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=perfil_v2):
        r = client.post(f"/triage/{sid}/finalizar")

    assert r.json()["profile_json"]["resumo_geral"] == "Versão atualizada do perfil."

    # Não deve haver dois perfis — GET deve retornar o atualizado
    r2 = client.get(f"/students/{sid}/profile")
    assert r2.json()["profile_json"]["resumo_geral"] == "Versão atualizada do perfil."


def test_perfil_gerado_contem_schema_completo(client):
    """O profile_json retornado deve conter todas as chaves esperadas."""
    from app.services import claude_client

    sid = _criar_aluno(client)["id"]
    _enviar_mensagem(client, sid)

    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        r = client.post(f"/triage/{sid}/finalizar")

    pj = r.json()["profile_json"]
    for chave in ("objetivo_carreira", "experiencias", "disciplinas_relevantes",
                  "stack_tecnica", "soft_skills", "restricoes", "resumo_geral"):
        assert chave in pj, f"Chave '{chave}' ausente no profile_json"
