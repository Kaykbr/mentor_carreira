"""Lógica de geração, edição e persistência do PDI (Plano de Desenvolvimento Individual)."""

import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PDI
from app.services import claude_client, contexto_aluno, profile_service
from app.services._base import upsert_registro
from app.services.texto import limpar_markdown

logger = logging.getLogger(__name__)

# Colunas válidas do quadro Kanban (mantém em sincronia com o schema QuadroCard).
COLUNAS_QUADRO = ("a_fazer", "em_progresso", "concluido")

# Campos estratégicos editáveis do PDI (o quadro e as ações originais são preservados).
_CAMPOS_EDITAVEIS = (
    "objetivo_geral",
    "metas_curto_prazo",
    "metas_medio_prazo",
    "competencias_a_desenvolver",
    "cronograma",
)


def _montar_quadro(acoes: list[str]) -> list[dict]:
    """Cria os cards do quadro Kanban a partir das ações recomendadas.

    Cada ação vira um card na coluna 'a_fazer'. O id é estável (gerado uma vez na
    materialização) para permitir mover/editar/excluir o card e persistir o estado.
    """
    cards: list[dict] = []
    for acao in acoes or []:
        texto = (acao or "").strip()
        if not texto:
            continue
        cards.append(
            {
                "id": uuid4().hex[:8],
                "texto": texto,
                "coluna": "a_fazer",
                "categoria": "Ação recomendada",
            }
        )
    return cards


def gerar_pdi(db: Session, student_id: int) -> PDI:
    """Gera o PDI a partir do perfil estruturado do aluno e salva (ou atualiza) no banco.

    Após a geração pela IA, materializa o `quadro_kanban` a partir das ações
    recomendadas (todos os cards começam em 'a_fazer'). Regenerar o PDI reseta o
    quadro — conteúdo novo da IA significa um quadro novo.
    """
    perfil = profile_service.obter_perfil(db, student_id)
    if perfil is None:
        raise ValueError("O aluno ainda não possui perfil estruturado (conclua a triagem primeiro).")

    logger.info("Gerando PDI para student_id=%d", student_id)
    contexto = contexto_aluno.montar_contexto(db, student_id)
    contexto_dict = {"curso": contexto.curso, "periodo_atual": contexto.periodo} if contexto else {}

    # O PDI é ancorado no que o aluno trouxe na triagem: o próprio perfil (objetivos,
    # stack, experiências e áreas de afinidade) é passado como base. Sem trilha/radar.
    contexto_dict = contexto_aluno.enriquecer_contexto(contexto_dict, perfil.profile_json)

    pdi_json = claude_client.gerar_pdi(perfil.profile_json, contexto_aluno=contexto_dict)
    _limpar_markdown_pdi(pdi_json)
    pdi_json["quadro_kanban"] = _montar_quadro(pdi_json.get("acoes_recomendadas", []))
    pdi = upsert_registro(db, PDI, student_id, pdi_json=pdi_json)
    logger.info("PDI salvo/atualizado para student_id=%d", student_id)
    return pdi


def _limpar_markdown_pdi(pdi_json: dict) -> None:
    """Remove Markdown dos textos livres do PDI gerado pela IA (in-place)."""
    if isinstance(pdi_json.get("objetivo_geral"), str):
        pdi_json["objetivo_geral"] = limpar_markdown(pdi_json["objetivo_geral"])
    for chave in ("metas_curto_prazo", "metas_medio_prazo", "acoes_recomendadas"):
        valor = pdi_json.get(chave)
        if isinstance(valor, list):
            pdi_json[chave] = [limpar_markdown(x) if isinstance(x, str) else x for x in valor]
    for meta in pdi_json.get("competencias_a_desenvolver") or []:
        if isinstance(meta, dict):
            if isinstance(meta.get("nome"), str):
                meta["nome"] = limpar_markdown(meta["nome"])
            if isinstance(meta.get("motivo"), str):
                meta["motivo"] = limpar_markdown(meta["motivo"])
    for bloco in pdi_json.get("cronograma") or []:
        if isinstance(bloco, dict):
            if isinstance(bloco.get("foco"), str):
                bloco["foco"] = limpar_markdown(bloco["foco"])
            if isinstance(bloco.get("atividades"), list):
                bloco["atividades"] = [
                    limpar_markdown(a) if isinstance(a, str) else a for a in bloco["atividades"]
                ]


def atualizar_pdi(db: Session, student_id: int, campos: dict) -> PDI:
    """Atualiza os campos estratégicos do PDI (objetivo, metas, competências, cronograma).

    Faz merge sobre o `pdi_json` existente, preservando `acoes_recomendadas` e o
    `quadro_kanban` (o quadro é editado pelo seu próprio fluxo). Levanta ValueError
    se o aluno ainda não tem PDI gerado.
    """
    pdi = obter_pdi(db, student_id)
    if pdi is None:
        raise ValueError("O aluno ainda não possui PDI (gere o PDI primeiro).")

    pdi_json = dict(pdi.pdi_json)
    for chave in _CAMPOS_EDITAVEIS:
        if chave in campos:
            pdi_json[chave] = campos[chave]

    pdi = upsert_registro(db, PDI, student_id, pdi_json=pdi_json)
    logger.info("PDI editado para student_id=%d", student_id)
    return pdi


def atualizar_quadro(db: Session, student_id: int, cards: list[dict]) -> PDI:
    """Substitui o estado do quadro Kanban (`quadro_kanban`) no `pdi_json`.

    Recebe a lista completa de cards (já validada pelo schema QuadroUpdate). Levanta
    ValueError se o aluno ainda não tem PDI ou se algum card tem coluna inválida
    (defesa em profundidade — o schema já valida na borda).
    """
    pdi = obter_pdi(db, student_id)
    if pdi is None:
        raise ValueError("O aluno ainda não possui PDI (gere o PDI primeiro).")

    for card in cards:
        if card.get("coluna") not in COLUNAS_QUADRO:
            raise ValueError(f"Coluna inválida no quadro: {card.get('coluna')!r}.")

    pdi_json = dict(pdi.pdi_json)
    pdi_json["quadro_kanban"] = cards
    pdi = upsert_registro(db, PDI, student_id, pdi_json=pdi_json)
    logger.info("Quadro Kanban do PDI atualizado para student_id=%d (%d cards)", student_id, len(cards))
    return pdi


def garantir_quadro(db: Session, student_id: int) -> PDI | None:
    """Garante que o PDI tenha um `quadro_kanban` materializado.

    Retrocompatibilidade: PDIs gerados antes do quadro existir (ou com o quadro
    vazio) recebem os cards a partir das ações recomendadas na primeira visita,
    persistindo o resultado. Retorna o PDI (atualizado se necessário) ou None.
    """
    pdi = obter_pdi(db, student_id)
    if pdi is None or pdi.pdi_json.get("quadro_kanban"):
        return pdi

    pdi_json = dict(pdi.pdi_json)
    pdi_json["quadro_kanban"] = _montar_quadro(pdi_json.get("acoes_recomendadas", []))
    return upsert_registro(db, PDI, student_id, pdi_json=pdi_json)


def obter_pdi(db: Session, student_id: int) -> PDI | None:
    """Retorna o PDI salvo de um aluno, se existir."""
    return db.scalar(select(PDI).where(PDI.student_id == student_id))
