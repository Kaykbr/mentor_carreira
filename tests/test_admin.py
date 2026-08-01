"""Testes do painel de administração (/admin): autorização, métricas, diagnóstico e gestão."""

from unittest.mock import patch

from sqlalchemy import select

from app.models import Student, StudentProfile, TriageMessage
from app.services import admin_service
from tests.conftest import PERFIL_FAKE

ADMIN_EMAIL = "admin.teste@example.com"  # presente em ADMIN_EMAILS (definido no conftest)


def _cadastrar(client, email, nome="Aluno Teste", periodo=3):
    """Cadastra (e autentica o client como) um aluno; retorna o JSON da resposta."""
    r = client.post(
        "/students",
        json={"nome": nome, "email": email, "periodo": periodo, "senha": "senha-super-secreta"},
    )
    assert r.status_code == 201
    return r.json()


# ---------------------------------------------------------------------------
# Autorização
# ---------------------------------------------------------------------------


def test_admin_sem_sessao_redireciona_para_login(client):
    r = client.get("/admin")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_admin_aluno_comum_recebe_403(client):
    _cadastrar(client, "comum@t.com")
    for rota in ("/admin", "/admin/alunos", "/admin/sistema", "/admin/alunos/1"):
        assert client.get(rota).status_code == 403, rota


def test_acoes_admin_negadas_a_aluno_comum(client):
    aluno = _cadastrar(client, "comum2@t.com")
    assert client.post(f"/admin/alunos/{aluno['id']}/admin", data={"valor": "1"}).status_code == 403
    assert client.post(f"/admin/alunos/{aluno['id']}/excluir").status_code == 403


def test_admin_por_email_da_config_acessa(client):
    _cadastrar(client, ADMIN_EMAIL, nome="Admin Env")
    r = client.get("/admin")
    assert r.status_code == 200
    assert "Painel de administração" in r.text


def test_admin_por_flag_no_banco_acessa(client, db_session):
    aluno = _cadastrar(client, "flag@t.com")
    db_session.get(Student, aluno["id"]).is_admin = True
    db_session.commit()
    assert client.get("/admin").status_code == 200


def test_nav_mostra_link_admin_para_admin(client):
    aluno = _cadastrar(client, ADMIN_EMAIL)
    r = client.get(f"/alunos/{aluno['id']}")
    assert 'href="/admin"' in r.text


def test_nav_oculta_link_admin_para_aluno_comum(client):
    aluno = _cadastrar(client, "semlink@t.com")
    r = client.get(f"/alunos/{aluno['id']}")
    assert 'href="/admin"' not in r.text


# ---------------------------------------------------------------------------
# Dashboard, lista e detalhe
# ---------------------------------------------------------------------------


def test_dashboard_exibe_kpis_e_graficos(client):
    _cadastrar(client, ADMIN_EMAIL)
    r = client.get("/admin")
    assert "Funil de conclusão" in r.text
    assert "Alunos por período" in r.text
    assert "Diagnóstico do sistema" in r.text


def test_lista_alunos_mostra_cadastrados(client):
    _cadastrar(client, "listado@t.com", nome="Fulano Listado")
    _cadastrar(client, ADMIN_EMAIL)
    r = client.get("/admin/alunos")
    assert r.status_code == 200
    assert "Fulano Listado" in r.text
    assert "listado@t.com" in r.text


def test_detalhe_aluno_existente(client):
    alvo = _cadastrar(client, "alvo@t.com", nome="Alvo Detalhe")
    _cadastrar(client, ADMIN_EMAIL)
    r = client.get(f"/admin/alunos/{alvo['id']}")
    assert r.status_code == 200
    assert "Alvo Detalhe" in r.text


def test_detalhe_aluno_com_perfil_exibe_artefatos(client):
    from app.services import claude_client

    alvo = _cadastrar(client, "comperfil@t.com", nome="Com Perfil")
    sid = alvo["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        client.post(f"/triage/{sid}/finalizar")

    _cadastrar(client, ADMIN_EMAIL)
    r = client.get(f"/admin/alunos/{sid}")
    assert r.status_code == 200
    assert "Ver perfil (JSON)" in r.text  # bloco <details> com o JSON bruto
    assert "2 mensagem(ns)" in r.text


def test_detalhe_aluno_inexistente_redireciona(client):
    _cadastrar(client, ADMIN_EMAIL)
    r = client.get("/admin/alunos/9999")
    assert r.status_code == 303
    assert "/admin/alunos" in r.headers["location"]


# ---------------------------------------------------------------------------
# Gestão: promover / rebaixar / excluir
# ---------------------------------------------------------------------------


def test_promover_aluno_a_admin(client, db_session):
    alvo = _cadastrar(client, "promovido@t.com")
    _cadastrar(client, ADMIN_EMAIL)
    r = client.post(f"/admin/alunos/{alvo['id']}/admin", data={"valor": "1"})
    assert r.status_code == 303
    assert db_session.get(Student, alvo["id"]).is_admin is True


def test_rebaixar_admin(client, db_session):
    alvo = _cadastrar(client, "rebaixado@t.com")
    _cadastrar(client, ADMIN_EMAIL)
    client.post(f"/admin/alunos/{alvo['id']}/admin", data={"valor": "1"})
    client.post(f"/admin/alunos/{alvo['id']}/admin", data={"valor": "0"})
    assert db_session.get(Student, alvo["id"]).is_admin is False


def test_admin_nao_remove_proprio_acesso(client):
    me = _cadastrar(client, ADMIN_EMAIL)
    r = client.post(f"/admin/alunos/{me['id']}/admin", data={"valor": "0"})
    assert r.status_code == 303
    assert "erro=" in r.headers["location"]


def test_admin_nao_exclui_propria_conta(client, db_session):
    me = _cadastrar(client, ADMIN_EMAIL)
    r = client.post(f"/admin/alunos/{me['id']}/excluir")
    assert r.status_code == 303
    assert "erro=" in r.headers["location"]
    assert db_session.get(Student, me["id"]) is not None


def test_excluir_aluno_remove_todos_os_dados(client, db_session):
    from app.services import claude_client

    alvo = _cadastrar(client, "excluido@t.com")
    sid = alvo["id"]
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        client.post(f"/triage/{sid}/mensagens", json={"mensagem": "Oi"})
    with patch.object(claude_client, "gerar_perfil_estruturado", return_value=PERFIL_FAKE):
        client.post(f"/triage/{sid}/finalizar")

    _cadastrar(client, ADMIN_EMAIL)
    r = client.post(f"/admin/alunos/{sid}/excluir")
    assert r.status_code == 303
    assert db_session.get(Student, sid) is None
    assert db_session.scalar(select(TriageMessage).where(TriageMessage.student_id == sid)) is None
    assert db_session.scalar(select(StudentProfile).where(StudentProfile.student_id == sid)) is None


def test_excluir_aluno_inexistente_redireciona_com_erro(client):
    _cadastrar(client, ADMIN_EMAIL)
    r = client.post("/admin/alunos/9999/excluir")
    assert r.status_code == 303
    assert "erro=" in r.headers["location"]


# ---------------------------------------------------------------------------
# Sistema: diagnóstico e configuração
# ---------------------------------------------------------------------------


def test_sistema_mostra_diagnostico_e_config(client):
    _cadastrar(client, ADMIN_EMAIL)
    r = client.get("/admin/sistema")
    assert r.status_code == 200
    assert "Diagnóstico" in r.text
    assert "ANTHROPIC_API_KEY" in r.text
    assert "CLAUDE_MODEL" in r.text
    assert "CLAUDE_MODEL_ANALISE" in r.text
    assert "CLAUDE_MODEL_GERACAO" in r.text


def test_sistema_nao_vaza_segredos(client):
    _cadastrar(client, ADMIN_EMAIL)
    r = client.get("/admin/sistema")
    # Valores reais (de teste) não podem aparecer em claro na página.
    assert "sk-test-dummy" not in r.text
    assert "test-secret-key-not-for-production" not in r.text


# ---------------------------------------------------------------------------
# admin_service (unitários)
# ---------------------------------------------------------------------------


def test_mascarar_segredos():
    assert admin_service._mascarar("") == "(não definido)"
    assert admin_service._mascarar("curta") == "••••••"
    assert admin_service._mascarar("sk-ant-1234567890") == "sk-a••••90"


def test_obter_metricas_contagens_e_funil(client, db_session):
    from app.services import claude_client

    a = _cadastrar(client, "m1@t.com", periodo=3)
    with patch.object(claude_client, "conversar_triagem", return_value="Ok"):
        client.post(f"/triage/{a['id']}/mensagens", json={"mensagem": "Oi"})
    _cadastrar(client, "m2@t.com", periodo=3)

    m = admin_service.obter_metricas(db_session)
    assert m["total"] == 2
    assert m["com_triagem"] == 1
    assert m["com_perfil"] == 0
    assert m["mensagens_triagem"] == 2  # user + assistant
    assert m["funil"][0]["valor"] == 2
    assert m["funil"][1] == {"etapa": "Iniciaram triagem", "valor": 1, "pct": 50}

    p3 = next(b for b in m["por_periodo"] if b["periodo"] == 3)
    assert p3["valor"] == 2
    assert p3["pct"] == 100


def test_metricas_contam_admin_por_email_da_config(client, db_session):
    _cadastrar(client, ADMIN_EMAIL)
    m = admin_service.obter_metricas(db_session)
    assert m["admins"] == 1


def test_diagnostico_resumo(db_session):
    checks = admin_service.obter_diagnostico(db_session)
    resumo = admin_service.resumo_diagnostico(checks)
    assert resumo["erro"] == 0
    assert resumo["ok"] >= 4
    nomes = {c["nome"] for c in checks}
    assert "Banco de dados" in nomes
    assert "Esquema (tabelas)" in nomes
    # Chave de teste ("sk-test-dummy") deve aparecer como aviso
    chave = next(c for c in checks if c["nome"] == "ANTHROPIC_API_KEY")
    assert chave["status"] == "aviso"
