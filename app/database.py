"""Configuração da conexão com o banco de dados (SQLite em dev, PostgreSQL em produção)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_e_sqlite = settings.database_url.startswith("sqlite")

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
    settings.database_url,
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
