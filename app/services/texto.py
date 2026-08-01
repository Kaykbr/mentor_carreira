"""Utilitários de texto compartilhados.

`limpar_markdown` remove marcações de Markdown das saídas da IA. O front exibe os textos
gerados como texto puro (sem renderização Markdown), então `**negrito**` e `- listas`
apareceriam literalmente ao aluno — especialmente no chat de triagem. A função é
conservadora: remove os marcadores mantendo o conteúdo, sem tentar reescrever o texto.
"""

import re

# Ênfase: **texto** / __texto__ / *texto* / _texto_ → texto (mantém o conteúdo interno).
_ENFASE_DUPLA = re.compile(r"(\*\*|__)(.+?)\1", re.DOTALL)
_ENFASE_SIMPLES = re.compile(r"(?<!\w)([*_])(?!\s)(.+?)(?<!\s)\1(?!\w)", re.DOTALL)
# Código inline: `trecho` → trecho.
_CODIGO_INLINE = re.compile(r"`([^`]+)`")
# Marcador de lista no início da linha: "- ", "* ", "+ " (com indentação opcional).
_BULLET = re.compile(r"^[ \t]*[-*+][ \t]+", re.MULTILINE)
# Título Markdown no início da linha: "# ", "## " etc.
_TITULO = re.compile(r"^[ \t]*#{1,6}[ \t]+", re.MULTILINE)


def limpar_markdown(texto: str) -> str:
    """Remove marcações de Markdown (ênfase, listas, títulos, código inline) de `texto`.

    Preserva o conteúdo — apenas tira os caracteres de marcação que o front não renderiza.
    Retorna string vazia para entrada vazia/None.
    """
    if not texto:
        return ""
    resultado = _ENFASE_DUPLA.sub(r"\2", texto)
    resultado = _ENFASE_SIMPLES.sub(r"\2", resultado)
    resultado = _CODIGO_INLINE.sub(r"\1", resultado)
    resultado = _TITULO.sub("", resultado)
    resultado = _BULLET.sub("", resultado)
    return resultado
