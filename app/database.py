"""Configuração da conexão com o banco de dados (SQLite em dev, PostgreSQL em produção)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalizar_url_postgres(url: str) -> str:
    """Ajusta a URL do banco para o driver `psycopg` v3 (que instalamos).

    Provedores gerenciados (Render, Heroku, Neon) entregam a URL como
    `postgres://...` ou `postgresql://...`. Sem qualificador de driver, o
    SQLAlchemy tenta importar o `psycopg2` (v2) e quebra com
    `ModuleNotFoundError: No module named 'psycopg2'`. Convertemos para
    `postgresql+psycopg://...` para forçar o driver v3.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_url_banco = _normalizar_url_postgres(settings.database_url)
_e_sqlite = _url_banco.startswith("sqlite")

# `check_same_thread=False` é exclusivo do SQLite — passá-lo ao psycopg quebra a conexão.
_connect_args = {"check_same_thread": False} if _e_sqlite else {}

# Pool dimensionado para uso concorrente (~50 alunos simultâneos em 2 workers uvicorn).
# `pool_pre_ping` descarta conexões mortas antes de usar: o Postgres gerenciado encerra
# conexões ociosas, e sem isso a primeira query após um período parado falharia.
_pool_kwargs: dict = (
    {}
    if _e_sqlite
    else {"pool_size": 10, "max_overflow": 5, "pool_timeout": 30, "pool_recycle": 300}
)

engine = create_engine(
    _url_banco,
    connect_args=_connect_args,
    pool_pre_ping=True,
    **_pool_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe base para os modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco de dados para os endpoints (dependência do FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
