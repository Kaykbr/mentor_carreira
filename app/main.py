"""Ponto de entrada da aplicação FastAPI — Mentor de Carreira."""

import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "padrao": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "padrao",
                "level": "DEBUG",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
        # Reduz verbosidade de libs de terceiros
        "loggers": {
            "sqlalchemy.engine": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
            "anthropic": {"level": "WARNING"},
        },
    }
)

import anthropic
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.rate_limit import limiter
from app.routes import admin, auth, curriculum, pdi, students, triage
from app.routes import analise_vaga_web, curriculo_vaga_web, curriculo_web, paginas_web, pdi_web, perfil_web
from app.routes._deps import RedirectParaLogin

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação: inicializa o banco ao subir e libera ao encerrar."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados inicializado com sucesso.")
    except Exception:
        logger.exception("Falha ao inicializar o banco de dados — a aplicação não pode subir.")
        raise
    yield
    logger.info("Aplicação encerrada.")


app = FastAPI(
    title="Mentor de Carreira para Estudantes de Sistemas de Informação",
    version="0.1.0",
    lifespan=lifespan,
)

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

_settings = get_settings()
app.add_middleware(
    SessionMiddleware,
    secret_key=_settings.secret_key,
    same_site="lax",
    https_only=_settings.session_https_only,
    max_age=_settings.session_max_age,
)

# Limitação por IP (protege o link público de abuso/bot durante a coleta).
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Responde 429 com mensagem amigável (HTML nas páginas, JSON na API)."""
    logger.warning("Rate limit atingido em %s %s", request.method, request.url.path)
    mensagem = (
        "Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente."
    )
    if request.url.path.startswith(("/students", "/auth", "/triage", "/pdi", "/curriculum")):
        return JSONResponse(status_code=429, content={"detail": mensagem})
    return HTMLResponse(
        f"<!doctype html><meta charset='utf-8'><title>Aguarde um pouco</title>"
        f"<div style=\"font-family:system-ui,sans-serif;max-width:32rem;margin:4rem auto;"
        f"padding:1.5rem;border:1px solid #dde5de;border-radius:12px\">"
        f"<h1 style='font-size:1.3rem'>Aguarde um pouco</h1><p>{mensagem}</p>"
        f"<p><a href='/' style='color:#1e7b34'>Voltar ao início</a></p></div>",
        status_code=429,
    )


@app.middleware("http")
async def adicionar_headers_seguranca(request: Request, call_next):
    """Adiciona cabeçalhos de segurança básicos a todas as respostas."""
    resposta = await call_next(request)
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("X-Frame-Options", "DENY")
    resposta.headers.setdefault("Referrer-Policy", "same-origin")
    return resposta


app.include_router(auth.router)
app.include_router(students.router)
app.include_router(triage.router)
app.include_router(pdi.router)
app.include_router(curriculum.router)
app.include_router(admin.router)
app.include_router(paginas_web.router)
app.include_router(perfil_web.router)
app.include_router(pdi_web.router)
app.include_router(curriculo_web.router)
app.include_router(curriculo_vaga_web.router)
app.include_router(analise_vaga_web.router)


@app.exception_handler(RedirectParaLogin)
async def redirect_para_login_handler(request: Request, exc: RedirectParaLogin) -> RedirectResponse:
    """Redireciona páginas HTML para /login quando não há sessão ativa."""
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.exception_handler(anthropic.APIError)
async def claude_indisponivel_handler(request: Request, exc: anthropic.APIError) -> JSONResponse:
    """Converte falhas na API Anthropic (já esgotados os retries) em HTTP 503.

    Distingue indisponibilidade do mentor (transitória, o aluno pode tentar de novo)
    de erros internos reais (500). Cobre rate limit, falha/timeout de conexão e 5xx.
    """
    logger.warning(
        "API Anthropic indisponível em %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "O mentor (IA) está indisponível no momento. Tente novamente em instantes."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Captura qualquer exceção não tratada e retorna HTTP 500 com mensagem legível.

    Sem este handler, exceções genéricas (RuntimeError, timeout, etc.) propagariam
    pelo stack ASGI sem ser convertidas em resposta HTTP, causando crashes difíceis
    de diagnosticar em produção.
    """
    logger.exception("Erro interno não tratado em %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente ou contate o suporte."},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Endpoint simples para verificar se a API está no ar."""
    return {"status": "ok"}
