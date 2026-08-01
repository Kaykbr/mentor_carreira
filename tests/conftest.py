"""Configuração global da suíte de testes.

As variáveis de ambiente são definidas *antes* de qualquer import da aplicação para
garantir que o banco SQLite seja criado em memória e que nenhuma chave real da Anthropic
seja necessária para rodar os testes.
"""

import os

# Deve vir antes de qualquer import da app — garante banco em memória e key fictícia
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ANTHROPIC_API_KEY"] = "sk-test-dummy"
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["ADMIN_EMAILS"] = "admin.teste@example.com"  # admin de teste (ver test_admin.py)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

get_settings.cache_clear()  # força releitura com as variáveis acima

from app.database import Base, get_db  # noqa: E402 (import após configuração de env)
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Dados de teste reutilizáveis
# ---------------------------------------------------------------------------

PERFIL_FAKE: dict = {
    "objetivo_carreira": {
        "curto_prazo": "Conseguir estágio na área de backend",
        "medio_prazo": "Atuar como desenvolvedor pleno em 2 anos",
        "areas_interesse": ["backend", "APIs REST"],
    },
    "experiencias": [
        {
            "tipo": "projeto_pessoal",
            "titulo": "API de tarefas",
            "descricao": "API REST construída com FastAPI e SQLite",
            "periodo": "2024-2025",
            "tecnologias": ["Python", "FastAPI", "SQLite"],
        }
    ],
    "disciplinas_relevantes": [
        {"nome": "Banco de Dados", "relevancia": "Base para modelagem de dados no backend"},
    ],
    "stack_tecnica": {
        "linguagens": ["Python", "SQL"],
        "frameworks_ferramentas": ["FastAPI", "SQLAlchemy"],
        "nivel_geral": "intermediario",
    },
    "soft_skills": ["comunicação", "trabalho em equipe", "proatividade"],
    "restricoes": {
        "carga_horaria_disponivel": "20 horas por semana",
        "localizacao": "São Paulo - SP",
        "modalidade_preferida": "remoto",
        "outras": "",
    },
    "resumo_geral": "Aluno de SI com foco em backend, experiência com Python e FastAPI.",
}

PDI_FAKE: dict = {
    "objetivo_geral": "Tornar-se desenvolvedor backend pleno em até 2 anos",
    "metas_curto_prazo": [
        "Conseguir estágio em empresa de tecnologia",
        "Dominar testes automatizados com pytest",
    ],
    "metas_medio_prazo": [
        "Assumir posição júnior com autonomia técnica",
        "Contribuir com projetos open source",
    ],
    "competencias_a_desenvolver": [
        {"nome": "Testes automatizados", "motivo": "Aumentar confiança no código"},
        {"nome": "Docker", "motivo": "Facilitar deploy e ambientes consistentes"},
    ],
    "acoes_recomendadas": [
        "Construir ao menos 2 projetos completos com FastAPI e testes",
        "Estudar Docker e containerização",
        "Participar de processos seletivos mensalmente",
    ],
    "cronograma": [
        {
            "periodo": "0-3 meses",
            "foco": "Consolidação técnica",
            "atividades": ["Revisar Python avançado", "Implementar testes com pytest"],
        },
        {
            "periodo": "3-6 meses",
            "foco": "Mercado de trabalho",
            "atividades": ["Candidatar-se a estágios", "Montar portfólio no GitHub"],
        },
        {
            "periodo": "6-12 meses",
            "foco": "Crescimento profissional",
            "atividades": ["Consolidar experiência no estágio", "Estudar arquitetura"],
        },
    ],
}

CURRICULO_FAKE = (
    "RESUMO\n"
    "Desenvolvedor backend em formação, com experiência em Python e FastAPI.\n\n"
    "FORMAÇÃO\n"
    "Bacharelado em Sistemas de Informação — em andamento.\n\n"
    "EXPERIÊNCIAS\n"
    "Não informado.\n\n"
    "PROJETOS\n"
    "API de tarefas — API REST com FastAPI e SQLite.\n\n"
    "SKILLS TÉCNICAS\n"
    "Python, SQL, FastAPI, SQLAlchemy.\n\n"
    "SKILLS COMPORTAMENTAIS\n"
    "Comunicação, trabalho em equipe, proatividade.\n\n"
    "CERTIFICAÇÕES\n"
    "Não informado."
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    """Sessão isolada em SQLite em memória — criada e destruída a cada teste.

    StaticPool garante que todas as conexões ao mesmo banco em memória
    compartilhem o mesmo objeto de conexão subjacente, evitando que a segunda
    conexão abra um banco vazio (comportamento padrão do sqlite:///:memory:).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSL = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSL()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(db_session):
    """TestClient do FastAPI com o banco de dados substituído pelo db_session isolado."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def aluno_logado(client):
    """Cadastra um aluno e retorna seus dados.

    Como `POST /students` já inicia a sessão (`request.session["student_id"]`), o
    `client` retornado fica autenticado (cookie de sessão) para chamadas seguintes.
    """
    resp = client.post(
        "/students",
        json={
            "nome": "Aluno Teste",
            "email": "aluno.teste@example.com",
            "periodo": 3,
            "senha": "senha-super-secreta",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def error_client(db_session):
    """TestClient que converte exceções não tratadas em resposta 500 em vez de re-levantá-las.

    Necessário para testar cenários onde o app lança Exception genérica (ex.: falha
    na API Anthropic). O Starlette re-levanta exceções por padrão no TestClient para
    facilitar o debug — este fixture desativa esse comportamento para poder checar
    o código HTTP 500.
    """

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
