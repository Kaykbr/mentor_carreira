"""Infraestrutura compartilhada pelos routers de páginas HTML.

Reúne o objeto `Jinja2Templates` (apontando para `app/templates/`) e os helpers de
parsing/validação de formulário usados por mais de um router. Mantém os routers de
domínio (`paginas_web`, `perfil_web`, `pdi_web`, `curriculo_web`) enxutos e sem
duplicação.
"""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Sistema de flash messages
# ---------------------------------------------------------------------------

def flash(request: Request, tipo: str, msg: str) -> None:
    """Armazena uma flash message na sessão para ser exibida na próxima página."""
    request.session.setdefault("_flashes", []).append({"tipo": tipo, "msg": msg})


def pop_flashes(request: Request) -> list:
    """Remove e retorna todas as flash messages da sessão."""
    return request.session.pop("_flashes", [])


# Registra pop_flashes como global Jinja2 — disponível em qualquer template
# via {{ pop_flashes(request) }} sem precisar passar no contexto explicitamente.
templates.env.globals["pop_flashes"] = pop_flashes


def linhas(texto: str | None) -> list[str]:
    """Quebra um texto (textarea) em itens: uma linha = um item; descarta linhas vazias."""
    return [linha.strip() for linha in (texto or "").splitlines() if linha.strip()]


def itens_csv(texto: str | None) -> list[str]:
    """Quebra um texto separado por vírgulas em itens; descarta itens vazios."""
    return [item.strip() for item in (texto or "").split(",") if item.strip()]


def primeiro_erro(exc: ValidationError) -> str:
    """Extrai uma mensagem amigável do primeiro erro de validação do Pydantic."""
    erros = exc.errors()
    if not erros:
        return "Há um campo inválido no formulário."
    erro = erros[0]
    campo = " → ".join(str(p) for p in erro.get("loc", ())) or "campo"
    return f"Verifique o campo: {campo} ({erro.get('msg', 'inválido')})."
