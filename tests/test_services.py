"""Testes unitários dos serviços (sem camada HTTP)."""

from unittest.mock import patch

import pytest

from app.models import Curriculum, PDI, Student, StudentProfile, TriageMessage
from app.services import (
    auth_service,
    curriculum_service,
    pdi_service,
    profile_service,
    student_service,
)
from tests.conftest import CURRICULO_FAKE, PDI_FAKE, PERFIL_FAKE


# Hash de senha pré-calculado e reutilizado entre os testes (bcrypt é lento de propósito).
_SENHA_HASH = auth_service.gerar_hash_senha("senha-segura-123")


def _criar_aluno(db, nome, email, periodo):
    """Atalho para `student_service.criar_aluno` com um hash de senha fixo de teste."""
    return student_service.criar_aluno(db, nome, email, periodo, password_hash=_SENHA_HASH)


# ---------------------------------------------------------------------------
# student_service
# ---------------------------------------------------------------------------


class TestStudentService:
    def test_criar_aluno(self, db_session):
        aluno = _criar_aluno(db_session, "Maria", "maria@s.com", 3)
        assert isinstance(aluno, Student)
        assert aluno.id is not None
        assert aluno.nome == "Maria"
        assert aluno.email == "maria@s.com"
        assert aluno.periodo == 3
        assert aluno.curso == "Sistemas de Informação"
        assert aluno.password_hash == _SENHA_HASH

    def test_email_em_uso_verdadeiro(self, db_session):
        _criar_aluno(db_session, "X", "x@s.com", 1)
        assert student_service.email_em_uso(db_session, "x@s.com") is True

    def test_email_em_uso_falso(self, db_session):
        assert student_service.email_em_uso(db_session, "nao@existe.com") is False

    def test_obter_por_email_existente(self, db_session):
        criado = _criar_aluno(db_session, "Y", "y@s.com", 2)
        obtido = student_service.obter_por_email(db_session, "y@s.com")
        assert obtido is not None
        assert obtido.id == criado.id

    def test_obter_por_email_inexistente_retorna_none(self, db_session):
        assert student_service.obter_por_email(db_session, "nao@existe.com") is None

    def test_obter_aluno_existente(self, db_session):
        criado = _criar_aluno(db_session, "C", "c@s.com", 4)
        obtido = student_service.obter_aluno(db_session, criado.id)
        assert obtido is not None
        assert obtido.id == criado.id

    def test_obter_aluno_inexistente_retorna_none(self, db_session):
        assert student_service.obter_aluno(db_session, 9999) is None


# ---------------------------------------------------------------------------
# profile_service
# ---------------------------------------------------------------------------


class TestProfileService:
    def _aluno(self, db):
        return _criar_aluno(db, "Test", "test@ps.com", 2)

    def test_aluno_existe(self, db_session):
        a = self._aluno(db_session)
        assert profile_service.aluno_existe(db_session, a.id) is True

    def test_aluno_nao_existe(self, db_session):
        assert profile_service.aluno_existe(db_session, 9999) is False

    def test_historico_vazio(self, db_session):
        a = self._aluno(db_session)
        assert profile_service.obter_historico(db_session, a.id) == []

    def test_enviar_mensagem_salva_user_e_assistant(self, db_session):
        a = self._aluno(db_session)
        with patch("app.services.claude_client.conversar_triagem", return_value="Resposta"):
            profile_service.enviar_mensagem_triagem(db_session, a.id, "Pergunta")

        historico = profile_service.obter_historico(db_session, a.id)
        assert len(historico) == 2
        assert historico[0].role == "user"
        assert historico[0].content == "Pergunta"
        assert historico[1].role == "assistant"
        assert historico[1].content == "Resposta"

    def test_historico_em_ordem_cronologica(self, db_session):
        a = self._aluno(db_session)
        with patch("app.services.claude_client.conversar_triagem", return_value="R"):
            profile_service.enviar_mensagem_triagem(db_session, a.id, "Msg1")
            profile_service.enviar_mensagem_triagem(db_session, a.id, "Msg2")

        historico = profile_service.obter_historico(db_session, a.id)
        user_msgs = [m for m in historico if m.role == "user"]
        assert user_msgs[0].content == "Msg1"
        assert user_msgs[1].content == "Msg2"

    def test_finalizar_triagem_cria_perfil(self, db_session):
        a = self._aluno(db_session)
        with patch("app.services.claude_client.conversar_triagem", return_value="Ok"):
            profile_service.enviar_mensagem_triagem(db_session, a.id, "Oi")
        with patch("app.services.claude_client.gerar_perfil_estruturado", return_value=PERFIL_FAKE):
            perfil = profile_service.finalizar_triagem(db_session, a.id)

        assert isinstance(perfil, StudentProfile)
        assert perfil.student_id == a.id
        assert perfil.profile_json["resumo_geral"] == PERFIL_FAKE["resumo_geral"]

    def test_finalizar_triagem_sem_historico_levanta_value_error(self, db_session):
        a = self._aluno(db_session)
        with pytest.raises(ValueError, match="triagem"):
            profile_service.finalizar_triagem(db_session, a.id)

    def test_finalizar_triagem_duas_vezes_nao_duplica(self, db_session):
        a = self._aluno(db_session)
        with patch("app.services.claude_client.conversar_triagem", return_value="Ok"):
            profile_service.enviar_mensagem_triagem(db_session, a.id, "Oi")
        with patch("app.services.claude_client.gerar_perfil_estruturado", return_value=PERFIL_FAKE):
            profile_service.finalizar_triagem(db_session, a.id)
        perfil_v2 = {**PERFIL_FAKE, "resumo_geral": "Atualizado"}
        with patch("app.services.claude_client.gerar_perfil_estruturado", return_value=perfil_v2):
            profile_service.finalizar_triagem(db_session, a.id)

        from sqlalchemy import select
        count = len(list(db_session.scalars(select(StudentProfile).where(StudentProfile.student_id == a.id)).all()))
        assert count == 1

        perfil_final = profile_service.obter_perfil(db_session, a.id)
        assert perfil_final.profile_json["resumo_geral"] == "Atualizado"

    def test_obter_perfil_retorna_none_sem_triagem(self, db_session):
        a = self._aluno(db_session)
        assert profile_service.obter_perfil(db_session, a.id) is None

    def test_historico_para_claude_funde_papeis_consecutivos(self):
        """Mensagens consecutivas do mesmo papel são fundidas (a API exige papéis alternados)."""
        msgs = [
            TriageMessage(student_id=1, role="user", content="Oi"),
            TriageMessage(student_id=1, role="user", content="Está aí?"),
            TriageMessage(student_id=1, role="assistant", content="Olá!"),
            TriageMessage(student_id=1, role="assistant", content="   "),
        ]
        convertido = profile_service._historico_para_claude(msgs)
        assert convertido == [
            {"role": "user", "content": "Oi\nEstá aí?"},
            {"role": "assistant", "content": "Olá!"},
        ]

    def test_historico_para_claude_janela_comeca_com_user(self):
        """A janela de contexto corta o histórico e descarta assistant órfão no início."""
        msgs = [
            TriageMessage(student_id=1, role="user" if i % 2 == 0 else "assistant", content=f"m{i}")
            for i in range(10)
        ]
        janela = profile_service._historico_para_claude(msgs, max_mensagens=3)
        # Últimas 3: m7 (assistant), m8 (user), m9 (assistant) — assistant inicial cai fora
        assert janela == [{"role": "user", "content": "m8"}, {"role": "assistant", "content": "m9"}]

    def test_historico_para_claude_formato_correto(self, db_session):
        """Verifica que as mensagens enviadas ao Claude têm o formato {role, content}."""
        a = self._aluno(db_session)
        capturado = []

        def _fake(historico, nome_aluno=None):
            capturado.append(historico)
            return "Ok"

        with patch("app.services.claude_client.conversar_triagem", side_effect=_fake):
            profile_service.enviar_mensagem_triagem(db_session, a.id, "Testando")

        mensagem = capturado[0][0]
        assert set(mensagem.keys()) == {"role", "content"}
        assert mensagem["role"] == "user"
        assert mensagem["content"] == "Testando"


# ---------------------------------------------------------------------------
# pdi_service
# ---------------------------------------------------------------------------


class TestPDIService:
    def _aluno_com_perfil(self, db):
        a = _criar_aluno(db, "PDI", "pdi@ps.com", 4)
        with patch("app.services.claude_client.conversar_triagem", return_value="Ok"):
            profile_service.enviar_mensagem_triagem(db, a.id, "Oi")
        with patch("app.services.claude_client.gerar_perfil_estruturado", return_value=PERFIL_FAKE):
            profile_service.finalizar_triagem(db, a.id)
        return a

    def test_gerar_pdi_cria_objeto(self, db_session):
        a = self._aluno_com_perfil(db_session)
        with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
            pdi = pdi_service.gerar_pdi(db_session, a.id)
        assert isinstance(pdi, PDI)
        assert pdi.student_id == a.id
        assert pdi.pdi_json["objetivo_geral"] == PDI_FAKE["objetivo_geral"]

    def test_gerar_pdi_sem_perfil_levanta_value_error(self, db_session):
        a = _criar_aluno(db_session, "SemPerfil", "sp@ps.com", 1)
        with pytest.raises(ValueError, match="triagem"):
            pdi_service.gerar_pdi(db_session, a.id)

    def test_gerar_pdi_recebe_profile_json(self, db_session):
        a = self._aluno_com_perfil(db_session)
        recebido = []

        def _fake(profile_json):
            recebido.append(profile_json)
            return PDI_FAKE

        with patch("app.services.claude_client.gerar_pdi", side_effect=_fake):
            pdi_service.gerar_pdi(db_session, a.id)

        assert recebido[0]["resumo_geral"] == PERFIL_FAKE["resumo_geral"]

    def test_gerar_pdi_duas_vezes_atualiza(self, db_session):
        a = self._aluno_com_perfil(db_session)
        pdi_v2 = {**PDI_FAKE, "objetivo_geral": "Objetivo v2"}

        with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
            pdi_service.gerar_pdi(db_session, a.id)
        with patch("app.services.claude_client.gerar_pdi", return_value=pdi_v2):
            pdi_service.gerar_pdi(db_session, a.id)

        from sqlalchemy import select
        count = len(list(db_session.scalars(select(PDI).where(PDI.student_id == a.id)).all()))
        assert count == 1

        pdi_final = pdi_service.obter_pdi(db_session, a.id)
        assert pdi_final.pdi_json["objetivo_geral"] == "Objetivo v2"

    def test_obter_pdi_retorna_none_sem_geracao(self, db_session):
        a = self._aluno_com_perfil(db_session)
        assert pdi_service.obter_pdi(db_session, a.id) is None


# ---------------------------------------------------------------------------
# curriculum_service
# ---------------------------------------------------------------------------


class TestCurriculumService:
    def _aluno_com_perfil(self, db):
        a = _criar_aluno(db, "CV", "cv@cs.com", 5)
        with patch("app.services.claude_client.conversar_triagem", return_value="Ok"):
            profile_service.enviar_mensagem_triagem(db, a.id, "Oi")
        with patch("app.services.claude_client.gerar_perfil_estruturado", return_value=PERFIL_FAKE):
            profile_service.finalizar_triagem(db, a.id)
        return a

    def test_gerar_curriculo_cria_objeto(self, db_session):
        a = self._aluno_com_perfil(db_session)
        with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
            cv = curriculum_service.gerar_curriculo(db_session, a.id)
        assert isinstance(cv, Curriculum)
        assert cv.curriculum_text == CURRICULO_FAKE

    def test_gerar_curriculo_sem_perfil_levanta_value_error(self, db_session):
        a = _criar_aluno(db_session, "SemCV", "scv@cs.com", 1)
        with pytest.raises(ValueError, match="triagem"):
            curriculum_service.gerar_curriculo(db_session, a.id)

    def test_gerar_curriculo_sem_pdi_passa_none(self, db_session):
        a = self._aluno_com_perfil(db_session)
        recebido = []

        def _fake(profile_json, pdi_json=None):
            recebido.append(pdi_json)
            return CURRICULO_FAKE

        with patch("app.services.claude_client.gerar_curriculo", side_effect=_fake):
            curriculum_service.gerar_curriculo(db_session, a.id)

        assert recebido[0] is None

    def test_gerar_curriculo_com_pdi_passa_pdi(self, db_session):
        a = self._aluno_com_perfil(db_session)
        with patch("app.services.claude_client.gerar_pdi", return_value=PDI_FAKE):
            pdi_service.gerar_pdi(db_session, a.id)

        recebido = []

        def _fake(profile_json, pdi_json=None):
            recebido.append(pdi_json)
            return CURRICULO_FAKE

        with patch("app.services.claude_client.gerar_curriculo", side_effect=_fake):
            curriculum_service.gerar_curriculo(db_session, a.id)

        assert recebido[0] is not None
        assert recebido[0]["objetivo_geral"] == PDI_FAKE["objetivo_geral"]

    def test_gerar_curriculo_duas_vezes_atualiza(self, db_session):
        a = self._aluno_com_perfil(db_session)
        with patch("app.services.claude_client.gerar_curriculo", return_value=CURRICULO_FAKE):
            curriculum_service.gerar_curriculo(db_session, a.id)
        with patch("app.services.claude_client.gerar_curriculo", return_value="Texto novo"):
            curriculum_service.gerar_curriculo(db_session, a.id)

        from sqlalchemy import select
        count = len(list(db_session.scalars(select(Curriculum).where(Curriculum.student_id == a.id)).all()))
        assert count == 1

        cv = curriculum_service.obter_curriculo(db_session, a.id)
        assert cv.curriculum_text == "Texto novo"

    def test_obter_curriculo_retorna_none_sem_geracao(self, db_session):
        a = self._aluno_com_perfil(db_session)
        assert curriculum_service.obter_curriculo(db_session, a.id) is None
