"""Wrapper para chamadas ao modelo da Claude (triagem, geração de perfil, PDI e currículo).

Os prompts de sistema e os schemas de ferramenta (tool use) vivem em `app/prompts/` — aqui
fica apenas a lógica de cliente: singleton, retry, construção da requisição e leitura da
resposta. Os nomes dos prompts/ferramentas são reexportados abaixo por conveniência e
retrocompatibilidade (callers/testes que referenciem `claude_client.PROMPT_GERAR_PDI` etc.
continuam funcionando).
"""

import json
import logging
import time
from datetime import date
from typing import Any

import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.prompts import (
    FERRAMENTA_PDI,
    FERRAMENTA_PERFIL,
    PROMPT_GERAR_CURRICULO,
    PROMPT_GERAR_PDI,
    PROMPT_GERAR_PERFIL,
    PROMPT_SISTEMA_TRIAGEM,
)
from app.prompts import montar_prompt_triagem as _prompt_triagem
from app.prompts.analise_curriculo import FERRAMENTA_ANALISE_CURRICULO, PROMPT_ANALISE_CURRICULO
from app.prompts.analise_vaga import FERRAMENTA_EXTRAIR_VAGA, PROMPT_EXTRAIR_VAGA
from app.prompts.recomendacoes_vaga import FERRAMENTA_RECOMENDACOES_VAGA, PROMPT_RECOMENDACOES_VAGA

logger = logging.getLogger(__name__)

# Reexporta os nomes de prompts/ferramentas para retrocompatibilidade (ver docstring).
__all__ = [
    "PROMPT_SISTEMA_TRIAGEM",
    "PROMPT_GERAR_PERFIL",
    "FERRAMENTA_PERFIL",
    "PROMPT_GERAR_PDI",
    "FERRAMENTA_PDI",
    "PROMPT_GERAR_CURRICULO",
    "PROMPT_EXTRAIR_VAGA",
    "FERRAMENTA_EXTRAIR_VAGA",
    "PROMPT_RECOMENDACOES_VAGA",
    "FERRAMENTA_RECOMENDACOES_VAGA",
    "PROMPT_ANALISE_CURRICULO",
    "FERRAMENTA_ANALISE_CURRICULO",
    "conversar_triagem",
    "gerar_perfil_estruturado",
    "gerar_pdi",
    "gerar_curriculo",
    "extrair_requisitos_vaga",
    "gerar_recomendacoes_vaga",
    "analisar_curriculo",
]

# ---------------------------------------------------------------------------
# Cliente (singleton)
# ---------------------------------------------------------------------------

_cliente_cache: anthropic.Anthropic | None = None


def _cliente() -> anthropic.Anthropic:
    """Retorna o cliente Anthropic (criado uma única vez e reutilizado)."""
    global _cliente_cache
    if _cliente_cache is None:
        _cliente_cache = anthropic.Anthropic(
            api_key=get_settings().anthropic_api_key,
            # 45s: cabe folgado dentro do teto de ~100s do proxy do Render mesmo
            # somando 1 retry (45 + 1 + 45 = ~91s). Antes eram 60s x 3 tentativas
            # = ate ~183s, causando 502 + risco de o backend salvar e o aluno
            # reenviar (duplicacao silenciosa).
            timeout=45.0,
            # Retentativas ficam a cargo do tenacity (_RETRY) — evita retry duplicado.
            max_retries=0,
            # Habilita prompt caching (obrigatório para Haiku; Sonnet/Opus mais novos
            # suportam sem o header, mas incluir não causa erro em nenhum modelo).
            default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
    return _cliente_cache


# ---------------------------------------------------------------------------
# Decorator de retry para chamadas à API
#
# Aplica ate 2 tentativas com backoff exponencial (1s -> 2s, max 10s) apenas
# para erros transitorios: rate limit (429), falha/timeout de conexao e erros
# 5xx do servidor (inclui 529 "overloaded"). Erros permanentes (chave invalida,
# resposta malformada) propagam imediatamente sem retry.
# O cliente usa max_retries=0, entao esta e a unica camada de retentativas.
# Reduzido de 3 para 2 tentativas: com timeout=45s, cabe dentro do teto de
# ~100s do proxy do Render (45 + 1 + 45 = ~91s). Se falhar mesmo assim, o
# handler de anthropic.APIError devolve 503 amigavel e o aluno tenta de novo.
# ---------------------------------------------------------------------------

_RETRY = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError)
    ),
    reraise=True,
)

# ---------------------------------------------------------------------------
# Parâmetros de geração
# ---------------------------------------------------------------------------

# Teto de tokens de saída por tipo de chamada.
_MAX_TOKENS_CHAT = 1024          # resposta curta e conversacional na triagem
_MAX_TOKENS_ESTRUTURADO = 4096   # perfil, PDI e currículo (saídas mais longas)

# Temperatura baixa nas extrações estruturadas (perfil/PDI) → saída mais
# determinística e fiel ao schema. A triagem e o currículo usam o padrão do
# modelo (mais natural/criativo).
_TEMPERATURA_EXTRACAO = 0.0


# ---------------------------------------------------------------------------
# Helpers internos (centralizam chamada, logging e leitura da resposta)
# ---------------------------------------------------------------------------


def _log_chamada(contexto: str, modelo: str, resposta: Any, inicio: float) -> None:
    """Registra modelo, latência, consumo de tokens e acertos de cache de uma chamada."""
    uso = getattr(resposta, "usage", None)
    logger.info(
        "Claude %s (%s): %.1fs (tokens entrada=%s, saída=%s)",
        contexto,
        modelo,
        time.monotonic() - inicio,
        getattr(uso, "input_tokens", "?"),
        getattr(uso, "output_tokens", "?"),
    )
    cache_criado = getattr(uso, "cache_creation_input_tokens", 0) or 0
    cache_lido = getattr(uso, "cache_read_input_tokens", 0) or 0
    if cache_criado or cache_lido:
        logger.debug(
            "Claude %s — cache: criados=%d lidos=%d",
            contexto,
            cache_criado,
            cache_lido,
        )


def _resolver_modelo(override: str | None) -> str:
    """Retorna o modelo configurado para a operação, com fallback para CLAUDE_MODEL."""
    return override or get_settings().claude_model


_MESES_PT = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _bloco_data() -> dict[str, Any]:
    """Bloco de sistema com a data atual, injetado em TODAS as chamadas de IA.

    Sem isso o modelo assume o ano do próprio treinamento e gera datas defasadas (ex.:
    certificações em 2024). Vai como bloco extra no fim do `system`, depois do
    `cache_control` do prompt principal — então não invalida o cache (é um sufixo barato).
    """
    hoje = date.today()
    mes_pt = _MESES_PT[hoje.month - 1]
    texto = (
        f"CONTEXTO TEMPORAL (referência obrigatória para qualquer data que você gerar ou "
        f"registrar): hoje é {hoje.day} de {mes_pt} de {hoje.year} ({hoje.isoformat()}); "
        f"o mês atual é {mes_pt} de {hoje.year} e o ano atual é {hoje.year}. "
        f"REGRAS DURAS: (1) NUNCA gere uma data com ano anterior a {hoje.year}, sob nenhuma "
        f"hipótese; qualquer 2024 ou 2025 num cronograma é ERRO. "
        f"(2) Cronogramas, previsões e prazos partem SEMPRE do mês atual "
        f"({mes_pt} de {hoje.year}) para a frente; use rótulos como '{mes_pt}/{hoje.year} - "
        f"out/{hoje.year}', '0-3 meses' ou 'a partir de {mes_pt}/{hoje.year}'. "
        f"(3) Se um ano de certificação/experiência não foi informado pelo aluno, deixe o "
        f"campo em branco ('') — jamais chute um ano do passado. "
        f"(4) A única exceção é reproduzir literalmente um ano que o aluno explicitamente "
        f"informou (ex.: 'fiz o curso em 2023')."
    )
    return {"type": "text", "text": texto}


def _chamar(
    contexto: str,
    *,
    modelo: str,
    system: str | list[dict[str, Any]],
    messages: list[dict[str, Any]],
    max_tokens: int,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | None = None,
    temperature: float | None = None,
) -> Any:
    """Executa uma chamada ao Claude com tempo e log centralizados.

    Mantém um único ponto de construção da requisição — toda chamada do módulo passa
    por aqui, então timeout, retry (via decorator das funções públicas) e logging ficam
    consistentes. O modelo é decidido pela função pública chamadora (ver
    `_resolver_modelo`), permitindo modelos diferentes por operação.

    A data atual é injetada aqui, num único ponto, para valer em TODAS as operações de IA
    (perfil, PDI, currículo, análise de vaga, etc.) — evita datas defasadas na saída.
    """
    # Normaliza `system` para lista e acrescenta o bloco de data no fim (após o
    # cache_control do prompt principal, para não quebrar o cache).
    system_blocos = [{"type": "text", "text": system}] if isinstance(system, str) else list(system)
    system_blocos = system_blocos + [_bloco_data()]

    parametros: dict[str, Any] = {
        "model": modelo,
        "max_tokens": max_tokens,
        "system": system_blocos,
        "messages": messages,
    }
    if tools is not None:
        parametros["tools"] = tools
    if tool_choice is not None:
        parametros["tool_choice"] = tool_choice
    if temperature is not None:
        parametros["temperature"] = temperature

    inicio = time.monotonic()
    resposta = _cliente().messages.create(**parametros)
    _log_chamada(contexto, modelo, resposta, inicio)
    return resposta


def _texto_da_resposta(resposta: Any, contexto: str) -> str:
    """Extrai e concatena os blocos de texto; falha se a resposta vier vazia."""
    texto = "".join(bloco.text for bloco in resposta.content if bloco.type == "text").strip()
    if not texto:
        raise RuntimeError(f"Claude retornou uma resposta vazia ({contexto}).")
    return texto


def _ferramenta_da_resposta(resposta: Any, contexto: str) -> dict[str, Any]:
    """Extrai o input do bloco `tool_use`; falha se o Claude não usar a ferramenta."""
    for bloco in resposta.content:
        if bloco.type == "tool_use":
            return bloco.input
    raise RuntimeError(
        f"Claude não retornou o bloco 'tool_use' esperado ({contexto}). "
        f"Conteúdo recebido: {[b.type for b in resposta.content]}"
    )


# ---------------------------------------------------------------------------
# Funções públicas (cada uma é uma operação de IA; retry via @_RETRY)
# ---------------------------------------------------------------------------


@_RETRY
def conversar_triagem(
    historico: list[dict[str, str]],
    nome_aluno: str | None = None,
    curso: str | None = None,
    periodo: int | None = None,
    nota_progresso: str = "",
) -> str:
    """Envia o histórico completo da triagem ao Claude e retorna a próxima fala do mentor.

    `historico` é uma lista `{"role": "user"|"assistant", "content": "..."}` com papéis
    já alternados (o serviço sanitiza antes de chamar). Texto livre, sem tool use.
    Se `nome_aluno` for informado, o prompt de sistema é personalizado com o nome; se
    `curso`/`periodo` também forem informados, o prompt é calibrado pelo período atual.
    `nota_progresso`, quando fornecida, é injetada no system prompt para orientar o mentor
    sobre quais dos 7 pontos já foram abordados (evita re-perguntar tópicos cobertos).
    """
    logger.debug("Chamando Claude para triagem (mensagens no histórico: %d)", len(historico))
    resposta = _chamar(
        "triagem",
        modelo=get_settings().claude_model,
        system=[{
            "type": "text",
            "text": _prompt_triagem(nome_aluno, curso, periodo, nota_progresso),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=historico,
        max_tokens=_MAX_TOKENS_CHAT,
    )
    return _texto_da_resposta(resposta, "triagem")


@_RETRY
def gerar_perfil_estruturado(historico: list[dict[str, str]]) -> dict[str, Any]:
    """Gera o `profile_json` estruturado a partir do histórico completo da triagem.

    Força o tool use (`salvar_perfil_aluno`) para garantir JSON aderente ao schema. Tarefa
    de análise determinística (temperature=0) — pode usar um modelo mais barato/rápido via
    `CLAUDE_MODEL_ANALISE`.
    """
    logger.debug("Gerando perfil estruturado (mensagens: %d)", len(historico))
    resposta = _chamar(
        "perfil",
        modelo=_resolver_modelo(get_settings().claude_model_analise),
        system=[{"type": "text", "text": PROMPT_GERAR_PERFIL, "cache_control": {"type": "ephemeral"}}],
        messages=historico,
        max_tokens=_MAX_TOKENS_ESTRUTURADO,
        tools=[FERRAMENTA_PERFIL],
        tool_choice={"type": "tool", "name": "salvar_perfil_aluno"},
        temperature=_TEMPERATURA_EXTRACAO,
    )
    return _ferramenta_da_resposta(resposta, "perfil")


@_RETRY
def gerar_pdi(profile_json: dict[str, Any], contexto_aluno: dict[str, Any] | None = None) -> dict[str, Any]:
    """Gera o PDI a partir do perfil estruturado, via tool use (`salvar_pdi`).

    `contexto_aluno`, se informado (ex.: `{"curso": ..., "periodo_atual": ...}`), traz \
dados adicionais do aluno usados para calibrar o cronograma pela fase do curso.

    Saída completa e de qualidade — usa `CLAUDE_MODEL_GERACAO` (com fallback para
    `CLAUDE_MODEL`).
    """
    logger.debug("Gerando PDI a partir do perfil estruturado")
    partes = [
        "Perfil estruturado do aluno (JSON):\n" + json.dumps(profile_json, ensure_ascii=False, indent=2)
    ]
    if contexto_aluno:
        partes.append(
            "\nContexto adicional do aluno:\n" + json.dumps(contexto_aluno, ensure_ascii=False, indent=2)
        )
    mensagens = [{"role": "user", "content": "\n".join(partes)}]
    resposta = _chamar(
        "PDI",
        modelo=_resolver_modelo(get_settings().claude_model_geracao),
        system=[{"type": "text", "text": PROMPT_GERAR_PDI, "cache_control": {"type": "ephemeral"}}],
        messages=mensagens,
        max_tokens=_MAX_TOKENS_ESTRUTURADO,
        tools=[FERRAMENTA_PDI],
        tool_choice={"type": "tool", "name": "salvar_pdi"},
        temperature=_TEMPERATURA_EXTRACAO,
    )
    return _ferramenta_da_resposta(resposta, "PDI")


@_RETRY
def gerar_curriculo(
    profile_json: dict[str, Any],
    pdi_json: dict[str, Any] | None = None,
    contexto_aluno: dict[str, Any] | None = None,
) -> str:
    """Gera o currículo (texto livre formatado para ATS) a partir do perfil e, se houver, do PDI.

    `contexto_aluno` (ex.: `{"nome": ..., "email": ..., "curso": ..., "periodo_atual": ...}`) \
fornece dados de contato e formação usados no cabeçalho e na seção FORMAÇÃO. Cards \
"concluído" do quadro Kanban do PDI (se houver) são extraídos como evidência recente de \
trabalho prático para PROJETOS/SKILLS.

    Saída completa e de qualidade — usa `CLAUDE_MODEL_GERACAO` (com fallback para
    `CLAUDE_MODEL`).
    """
    logger.debug("Gerando currículo (com PDI: %s)", pdi_json is not None)
    partes = ["Perfil estruturado do aluno (JSON):\n" + json.dumps(profile_json, ensure_ascii=False, indent=2)]

    if contexto_aluno is not None:
        partes.append(
            "\nDados de contato e formação do aluno (JSON):\n"
            + json.dumps(contexto_aluno, ensure_ascii=False, indent=2)
        )

    if pdi_json is not None:
        partes.append("\nPDI do aluno (JSON):\n" + json.dumps(pdi_json, ensure_ascii=False, indent=2))
        concluidos = [c["texto"] for c in pdi_json.get("quadro_kanban", []) if c.get("coluna") == "concluido"]
        if concluidos:
            partes.append(
                "\nAções de desenvolvimento já CONCLUÍDAS pelo aluno (evidências recentes "
                "de trabalho prático, podem enriquecer PROJETOS/SKILLS):\n"
                + "\n".join(f"- {texto}" for texto in concluidos)
            )

    resposta = _chamar(
        "currículo",
        modelo=_resolver_modelo(get_settings().claude_model_geracao),
        system=[{"type": "text", "text": PROMPT_GERAR_CURRICULO, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": "\n".join(partes)}],
        max_tokens=_MAX_TOKENS_ESTRUTURADO,
    )
    return _texto_da_resposta(resposta, "currículo")


@_RETRY
def extrair_requisitos_vaga(jd_text: str) -> dict[str, Any]:
    """Extrai requisitos estruturados de uma descrição de vaga via tool use."""
    logger.debug("Extraindo requisitos da vaga (%d chars)", len(jd_text))
    resposta = _chamar(
        "análise_vaga",
        modelo=_resolver_modelo(get_settings().claude_model_analise),
        system=[{"type": "text", "text": PROMPT_EXTRAIR_VAGA, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": jd_text}],
        max_tokens=_MAX_TOKENS_ESTRUTURADO,
        tools=[FERRAMENTA_EXTRAIR_VAGA],
        tool_choice={"type": "tool", "name": "salvar_requisitos_vaga"},
        temperature=_TEMPERATURA_EXTRACAO,
    )
    return _ferramenta_da_resposta(resposta, "análise_vaga")


@_RETRY
def gerar_recomendacoes_vaga(profile_json: dict[str, Any], analise: dict[str, Any]) -> dict[str, Any]:
    """Gera recomendações de competitividade para uma vaga, via tool use.

    Recebe o perfil do aluno e a análise de aderência já calculada (cargo, nível,
    score, competências categorizadas) e devolve resumo, pontos fortes, ações de
    melhoria, projetos de portfólio sugeridos e dicas competitivas.

    Saída orientativa de qualidade — usa `CLAUDE_MODEL_GERACAO` (com fallback para
    `CLAUDE_MODEL`).
    """
    logger.debug("Gerando recomendações de vaga (cargo=%s)", analise.get("cargo", ""))
    # Sem recursos_lacunas: são links do catálogo (ruído/custo para o modelo).
    analise_enxuta = {k: v for k, v in analise.items() if k != "recursos_lacunas"}
    conteudo = (
        "Perfil estruturado do aluno (JSON):\n"
        + json.dumps(profile_json, ensure_ascii=False, indent=2)
        + "\n\nAnálise de aderência do aluno à vaga (JSON):\n"
        + json.dumps(analise_enxuta, ensure_ascii=False, indent=2)
    )
    resposta = _chamar(
        "recomendações_vaga",
        modelo=_resolver_modelo(get_settings().claude_model_geracao),
        system=[{"type": "text", "text": PROMPT_RECOMENDACOES_VAGA, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": conteudo}],
        max_tokens=_MAX_TOKENS_ESTRUTURADO,
        tools=[FERRAMENTA_RECOMENDACOES_VAGA],
        tool_choice={"type": "tool", "name": "salvar_recomendacoes_vaga"},
        temperature=_TEMPERATURA_EXTRACAO,
    )
    return _ferramenta_da_resposta(resposta, "recomendações_vaga")


@_RETRY
def analisar_curriculo(
    curriculum_text: str,
    profile_json: dict[str, Any],
    diagnostico: dict[str, Any],
) -> dict[str, Any]:
    """Gera a análise qualitativa do currículo base, via tool use.

    Recebe o texto do currículo, o perfil e o **diagnóstico determinístico** já calculado
    por `curriculo_qualidade.diagnosticar` — assim o modelo não gasta tokens redetectando
    o que o código já mediu e foca no julgamento (escrita, priorização, posicionamento).

    Saída orientativa de qualidade — usa `CLAUDE_MODEL_GERACAO` (com fallback para
    `CLAUDE_MODEL`).
    """
    logger.debug("Analisando currículo (%d chars, pontuação=%s)", len(curriculum_text), diagnostico.get("pontuacao"))
    # Só os itens problemáticos: os "ok" não precisam de julgamento e viram ruído/custo.
    itens_criticos = [i for i in diagnostico.get("itens", []) if i.get("status") != "ok"]
    diagnostico_enxuto = {"pontuacao": diagnostico.get("pontuacao"), "itens_a_melhorar": itens_criticos}
    conteudo = (
        "Currículo atual do aluno:\n"
        + curriculum_text
        + "\n\nPerfil estruturado do aluno (JSON):\n"
        + json.dumps(profile_json, ensure_ascii=False, indent=2)
        + "\n\nDiagnóstico automático já calculado por regras (JSON):\n"
        + json.dumps(diagnostico_enxuto, ensure_ascii=False, indent=2)
    )
    resposta = _chamar(
        "análise_currículo",
        modelo=_resolver_modelo(get_settings().claude_model_geracao),
        system=[{"type": "text", "text": PROMPT_ANALISE_CURRICULO, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": conteudo}],
        max_tokens=_MAX_TOKENS_ESTRUTURADO,
        tools=[FERRAMENTA_ANALISE_CURRICULO],
        tool_choice={"type": "tool", "name": "salvar_analise_curriculo"},
        temperature=_TEMPERATURA_EXTRACAO,
    )
    return _ferramenta_da_resposta(resposta, "análise_currículo")
