"""Diagnóstico determinístico da qualidade do currículo — sem IA, sem banco.

O `PROMPT_GERAR_CURRICULO` impõe um contrato verificável ao texto gerado (7 seções em
ordem fixa, bullets com "- ", zero Markdown, cabeçalho com e-mail e links, bullets
iniciados por verbo de ação no passado). Este módulo confere esse contrato por regex e
devolve uma pontuação auditável — nenhuma chamada de API, nenhum custo.

Como é barato, o diagnóstico é recalculado a cada exibição da página: reflete na hora as
edições manuais do aluno. As dicas *qualitativas* (que exigem julgamento) ficam a cargo da
IA em `curriculum_analise_service`, que recebe este diagnóstico pronto como entrada.
"""

import re
import unicodedata

# Seções obrigatórias, na ordem exigida pelo prompt (app/prompts/curriculo.py).
SECOES = (
    "RESUMO",
    "FORMAÇÃO",
    "EXPERIÊNCIAS",
    "PROJETOS",
    "SKILLS TÉCNICAS",
    "SKILLS COMPORTAMENTAIS",
    "CERTIFICAÇÕES",
)

# Verbos de ação no passado (1ª pessoa) citados no prompt + os mais comuns em currículos.
VERBOS_ACAO = frozenset(
    """desenvolvi implementei construí automatizei integrei criei projetei otimizei
    configurei liderei participei realizei apliquei modelei publiquei refatorei testei
    documentei colaborei atuei analisei reduzi aumentei migrei estruturei elaborei
    desenvolvi conduzi coordenei apresentei entreguei""".split()
)

# Marcação Markdown que quebra parsers de ATS (o texto é exibido em fonte monoespaçada).
_MARKDOWN = (
    (r"\*\*", "negrito (**)"),
    (r"(?m)^\s*#{1,6}\s", "títulos (#)"),
    (r"(?m)^\s*\|.*\|", "tabelas (|)"),
    (r"(?m)^\s*```", "blocos de código (```)"),
)

_PESOS = {
    "estrutura": 20,
    "cabecalho": 15,
    "secoes_vazias": 15,
    "verbos_acao": 15,
    "quantificacao": 15,
    "limpeza_ats": 10,
    "tamanho": 5,
    "keywords": 5,
}


def _sem_acento(texto: str) -> str:
    """Remove acentos para comparações tolerantes (ex.: 'construí' ≈ 'construi')."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _item(chave: str, titulo: str, status: str, detalhe: str, como_corrigir: str = "") -> dict:
    return {
        "id": chave,
        "titulo": titulo,
        "status": status,  # ok | atencao | falha
        "detalhe": detalhe,
        "como_corrigir": como_corrigir,
    }


def _linhas_uteis(texto: str) -> list[str]:
    return [linha.strip() for linha in texto.splitlines() if linha.strip()]


def _chave_secao(linha: str) -> str:
    """Normaliza uma linha para comparar com um título de seção.

    Tolerante de propósito: currículos editados à mão aparecem com marcação (`# RESUMO`,
    `**RESUMO**`) ou sem acento (`EXPERIENCIAS`). Reconhecer mesmo assim dá um diagnóstico
    mais fiel — a marcação continua sendo apontada pelo item `limpeza_ats`.
    """
    limpa = re.sub(r"[#*_`:]", "", linha).strip()
    return _sem_acento(limpa).upper()


def _indices_secoes(linhas: list[str]) -> dict[str, int]:
    """Mapeia cada seção encontrada para o índice da linha em que aparece."""
    alvos = {_chave_secao(sec): sec for sec in SECOES}
    indices: dict[str, int] = {}
    for i, linha in enumerate(linhas):
        sec = alvos.get(_chave_secao(linha))
        if sec and sec not in indices:  # 1ª ocorrência vence
            indices[sec] = i
    return indices


def _corpo_da_secao(linhas: list[str], indices: dict[str, int], secao: str) -> list[str]:
    """Retorna as linhas de conteúdo de uma seção (até a próxima seção ou o fim)."""
    if secao not in indices:
        return []
    inicio = indices[secao]
    proximos = [i for i in indices.values() if i > inicio]
    fim = min(proximos) if proximos else len(linhas)
    return linhas[inicio + 1 : fim]


def _bullets(linhas: list[str]) -> list[str]:
    return [linha[2:].strip() for linha in linhas if linha.startswith("- ")]


def _avaliar_estrutura(linhas: list[str], indices: dict[str, int]) -> tuple[dict, float]:
    faltando = [s for s in SECOES if s not in indices]
    if faltando:
        return (
            _item(
                "estrutura",
                "Seções obrigatórias",
                "falha",
                f"Faltam {len(faltando)} seção(ões): {', '.join(faltando)}.",
                "Regere o currículo pela IA — ele monta as 7 seções no padrão ATS. "
                "Se você editou à mão, adicione o título da seção em uma linha só, em maiúsculas.",
            ),
            0.0,
        )

    posicoes = [indices[s] for s in SECOES]
    if posicoes != sorted(posicoes):
        return (
            _item(
                "estrutura",
                "Seções obrigatórias",
                "atencao",
                "As 7 seções estão presentes, mas fora da ordem esperada.",
                f"A ordem recomendada para leitura por recrutadores é: {' → '.join(SECOES)}.",
            ),
            0.5,
        )

    return (
        _item("estrutura", "Seções obrigatórias", "ok", "As 7 seções estão presentes e na ordem correta."),
        1.0,
    )


def _avaliar_cabecalho(linhas: list[str], indices: dict[str, int]) -> tuple[dict, float]:
    fim = indices.get("RESUMO", len(linhas))
    cabecalho = linhas[:fim]
    if not cabecalho:
        return (
            _item(
                "cabecalho",
                "Cabeçalho de contato",
                "falha",
                "Não há cabeçalho antes da seção RESUMO.",
                "O currículo deve começar com seu nome e, na linha seguinte, e-mail e links.",
            ),
            0.0,
        )

    texto_cab = " ".join(cabecalho)
    tem_email = "@" in texto_cab
    tem_link = bool(re.search(r"(github|linkedin|gitlab|behance|portfólio|portfolio|https?://)", texto_cab, re.I))

    if tem_email and tem_link:
        return (_item("cabecalho", "Cabeçalho de contato", "ok", "Nome, e-mail e links de contato presentes."), 1.0)
    if tem_email:
        return (
            _item(
                "cabecalho",
                "Cabeçalho de contato",
                "atencao",
                "Há e-mail, mas nenhum link (GitHub, LinkedIn ou portfólio).",
                "Preencha GitHub/LinkedIn em Perfil → Links e regere: para vaga de tecnologia, "
                "o link do GitHub costuma ser o primeiro lugar que o recrutador abre.",
            ),
            0.5,
        )
    return (
        _item(
            "cabecalho",
            "Cabeçalho de contato",
            "falha",
            "O cabeçalho não tem e-mail — o recrutador não tem como te contatar.",
            "Confira se o e-mail da sua conta está correto em Configurações e regere o currículo.",
        ),
        0.0,
    )


def _avaliar_secoes_vazias(linhas: list[str], indices: dict[str, int]) -> tuple[dict, float]:
    vazias = [
        sec
        for sec in SECOES
        if any("não informado" in linha.lower() for linha in _corpo_da_secao(linhas, indices, sec))
    ]
    if not vazias:
        return (_item("secoes_vazias", "Seções preenchidas", "ok", "Nenhuma seção ficou como 'Não informado'."), 1.0)

    proporcao = 1 - (len(vazias) / len(SECOES))
    status = "falha" if len(vazias) >= 3 else "atencao"
    return (
        _item(
            "secoes_vazias",
            "Seções preenchidas",
            status,
            f"{len(vazias)} seção(ões) sem conteúdo: {', '.join(vazias)}.",
            "Essas lacunas vêm do seu perfil. Complete-o em Perfil → Editar (certificações, "
            "formação, soft skills) e regere o currículo.",
        ),
        max(proporcao, 0.0),
    )


def _avaliar_verbos(bullets_exp: list[str]) -> tuple[dict, float]:
    if not bullets_exp:
        return (
            _item(
                "verbos_acao",
                "Verbos de ação",
                "atencao",
                "Não há itens em EXPERIÊNCIAS/PROJETOS para avaliar.",
                "Adicione experiências ou projetos ao perfil — é o que dá substância ao currículo.",
            ),
            0.0,
        )

    def comeca_com_verbo(b: str) -> bool:
        primeira = _sem_acento(b.split()[0].lower().strip(",.:;")) if b.split() else ""
        if primeira in {_sem_acento(v) for v in VERBOS_ACAO}:
            return True
        # Heurística: 1ª pessoa do pretérito costuma terminar em -ei / -i / -í.
        return bool(re.fullmatch(r"[a-z]{4,}(ei|i)", primeira))

    acertos = sum(1 for b in bullets_exp if comeca_com_verbo(b))
    razao = acertos / len(bullets_exp)

    if razao >= 0.8:
        status, corrigir = "ok", ""
    elif razao >= 0.5:
        status, corrigir = (
            "atencao",
            "Comece cada item com o que VOCÊ fez: 'Desenvolvi', 'Implementei', 'Automatizei'…",
        )
    else:
        status, corrigir = (
            "falha",
            "Reescreva os itens começando por um verbo de ação no passado. Troque 'Responsável por "
            "manutenção do site' por 'Mantive e evoluí o site institucional'.",
        )

    return (
        _item(
            "verbos_acao",
            "Verbos de ação",
            status,
            f"{acertos} de {len(bullets_exp)} itens começam com verbo de ação no passado.",
            corrigir,
        ),
        razao,
    )


def _avaliar_quantificacao(bullets_exp: list[str]) -> tuple[dict, float]:
    if not bullets_exp:
        return (
            _item(
                "quantificacao",
                "Resultados quantificados",
                "atencao",
                "Sem itens de experiência/projeto para avaliar.",
                "",
            ),
            0.0,
        )

    padrao = re.compile(r"\d+\s*(%|mil|k\b|h\b|horas|dias|semanas|meses|usuários|pessoas|vezes|x\b)|\d+", re.I)
    com_numero = sum(1 for b in bullets_exp if padrao.search(b))
    razao = com_numero / len(bullets_exp)

    if razao >= 0.5:
        status, corrigir = "ok", ""
    elif razao > 0:
        status, corrigir = (
            "atencao",
            "Quantifique mais itens: 'usado por ~30 colegas', 'reduziu o cadastro em 40%', "
            "'automatizou uma rotina de 2h por semana'.",
        )
    else:
        status, corrigir = (
            "falha",
            "Nenhum item tem número. Impacto medido é o que mais diferencia currículo júnior — "
            "mesmo estimativas ajudam ('cerca de 10 usuários').",
        )

    return (
        _item(
            "quantificacao",
            "Resultados quantificados",
            status,
            f"{com_numero} de {len(bullets_exp)} itens citam número ou impacto medido.",
            corrigir,
        ),
        razao,
    )


def _avaliar_limpeza(texto: str, linhas: list[str], indices: dict[str, int]) -> tuple[dict, float]:
    # O cabeçalho usa " | " legitimamente para separar links — não é tabela Markdown.
    inicio_corpo = indices.get("RESUMO", 0)
    corpo = "\n".join(linhas[inicio_corpo:])

    achados = [rotulo for padrao, rotulo in _MARKDOWN if re.search(padrao, corpo)]
    if not achados:
        return (
            _item("limpeza_ats", "Formatação compatível com ATS", "ok", "Texto limpo, sem marcação Markdown."),
            1.0,
        )
    return (
        _item(
            "limpeza_ats",
            "Formatação compatível com ATS",
            "falha",
            f"Marcação encontrada: {', '.join(achados)}.",
            "Sistemas de triagem leem o texto puro e mostram esses símbolos literalmente. "
            "Remova a marcação ou regere o currículo pela IA.",
        ),
        0.0,
    )


def _avaliar_tamanho(texto: str) -> tuple[dict, float]:
    n = len(texto)
    if 1500 <= n <= 5500:
        return (_item("tamanho", "Tamanho do currículo", "ok", f"{n} caracteres — cabe em cerca de 1 página."), 1.0)
    if n < 1500:
        return (
            _item(
                "tamanho",
                "Tamanho do currículo",
                "atencao",
                f"Apenas {n} caracteres — está enxuto demais.",
                "Enriqueça o perfil com mais detalhes de projetos e experiências, e regere.",
            ),
            0.4,
        )
    return (
        _item(
            "tamanho",
            "Tamanho do currículo",
            "atencao",
            f"{n} caracteres — provavelmente passa de 1 página.",
            "Para início de carreira, 1 página é o padrão esperado. Corte repetições e itens menos relevantes.",
        ),
        0.5,
    )


def _keywords_do_perfil(profile_json: dict | None) -> list[str]:
    """Palavras-chave técnicas do próprio perfil (stack declarada na triagem).

    Aceita o formato novo `[{"nome": ..., "nivel": ...}]` e o antigo `[str]` para
    perfis salvos antes do refactor da stack técnica.
    """
    stack = (profile_json or {}).get("stack_tecnica") or {}
    itens = list(stack.get("linguagens") or []) + list(stack.get("frameworks_ferramentas") or [])
    nomes: list[str] = []
    for item in itens:
        if isinstance(item, dict):
            nome = str(item.get("nome") or "").strip()
        else:
            nome = str(item or "").strip()
        if nome:
            nomes.append(nome)
    return nomes


def _avaliar_keywords(texto: str, competencias: list[str]) -> tuple[dict, float]:
    if not competencias:
        return (
            _item(
                "keywords",
                "Palavras-chave técnicas",
                "atencao",
                "Sem stack técnica no perfil para comparar.",
                "Preencha suas linguagens e ferramentas no perfil para o sistema avaliar as palavras-chave.",
            ),
            0.0,
        )

    texto_norm = _sem_acento(texto.lower())
    presentes = [c for c in competencias if _sem_acento(c.split(" ou ")[0].split("(")[0].strip().lower()) in texto_norm]
    razao = len(presentes) / len(competencias)

    status = "ok" if razao >= 0.5 else ("atencao" if razao > 0 else "falha")
    corrigir = (
        ""
        if status == "ok"
        else "Sistemas ATS filtram por palavra-chave. Cite no currículo as tecnologias do seu "
        "perfil que você realmente domina — sem inventar o que não tem."
    )
    return (
        _item(
            "keywords",
            "Palavras-chave técnicas",
            status,
            f"{len(presentes)} de {len(competencias)} tecnologias do seu perfil aparecem no texto.",
            corrigir,
        ),
        razao,
    )


def diagnosticar(curriculum_text: str, profile_json: dict | None = None) -> dict:
    """Avalia o currículo contra o contrato do prompt e devolve pontuação + itens.

    Retorna `{"pontuacao": 0-100, "itens": [...], "contagens": {...}}`. Cada item traz
    `status` (ok/atencao/falha), o que foi medido e como corrigir.
    """
    texto = (curriculum_text or "").strip()
    if not texto:
        return {"pontuacao": 0, "itens": [], "contagens": {}}

    linhas = _linhas_uteis(texto)
    indices = _indices_secoes(linhas)

    bullets_exp = _bullets(_corpo_da_secao(linhas, indices, "EXPERIÊNCIAS")) + _bullets(
        _corpo_da_secao(linhas, indices, "PROJETOS")
    )

    avaliacoes = {
        "estrutura": _avaliar_estrutura(linhas, indices),
        "cabecalho": _avaliar_cabecalho(linhas, indices),
        "secoes_vazias": _avaliar_secoes_vazias(linhas, indices),
        "verbos_acao": _avaliar_verbos(bullets_exp),
        "quantificacao": _avaliar_quantificacao(bullets_exp),
        "limpeza_ats": _avaliar_limpeza(texto, linhas, indices),
        "tamanho": _avaliar_tamanho(texto),
        "keywords": _avaliar_keywords(texto, _keywords_do_perfil(profile_json)),
    }

    pontuacao = sum(_PESOS[chave] * razao for chave, (_, razao) in avaliacoes.items())

    return {
        "pontuacao": round(pontuacao),
        "itens": [item for item, _ in avaliacoes.values()],
        "contagens": {
            "bullets_experiencia": len(bullets_exp),
            "secoes_encontradas": len(indices),
            "caracteres": len(texto),
        },
    }
