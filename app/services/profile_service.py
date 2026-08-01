"""Lógica de integração entre a triagem (chat) e o perfil estruturado do aluno."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Student, StudentProfile, TriageMessage
from app.services import claude_client
from app.services._base import upsert_registro
from app.services.texto import limpar_markdown

logger = logging.getLogger(__name__)

# Máximo de mensagens (user + assistant) armazenadas por aluno na triagem.
# Evita custo/contexto crescendo sem limite; ao atingir, o aluno é orientado a finalizar.
LIMITE_MENSAGENS_TRIAGEM = 100

# Palavras-chave usadas para detectar quais dos 7 pontos da triagem já foram abordados.
# A detecção varre os textos do assistente (perguntas feitas), não as respostas do aluno.
_PALAVRAS_TOPICO: dict[str, list[str]] = {
    "objetivo de carreira": ["objetivo", "carreira", "área de interesse", "futuro profissional", "trabalhar com"],
    "experiências": ["experiência", "estágio", "projeto", "freela", "desenvolveu", "trabalhou"],
    "disciplinas": ["disciplina", "matéria", "cursou", "aula", "faculdade"],
    "stack técnica": ["linguagem", "framework", "tecnologia", "stack", "ferramenta", "usa no dia"],
    "soft skills": ["habilidade", "soft skill", "comunicação", "equipe", "liderança"],
    "restrições práticas": ["disponibilidade", "horas", "modalidade", "presencial", "remoto", "carga horária"],
    "formação complementar": ["certificação", "linkedin", "github", "portfólio", "instituição", "previsão"],
}


def obter_historico(db: Session, student_id: int) -> list[TriageMessage]:
    """Retorna o histórico de mensagens de triagem de um aluno, em ordem cronológica."""
    consulta = (
        select(TriageMessage)
        .where(TriageMessage.student_id == student_id)
        .order_by(TriageMessage.id)
    )
    return list(db.scalars(consulta).all())


def _registrar_mensagem(db: Session, student_id: int, role: str, content: str) -> TriageMessage:
    """Persiste uma mensagem (do aluno ou do mentor) no histórico de triagem."""
    mensagem = TriageMessage(student_id=student_id, role=role, content=content)
    db.add(mensagem)
    db.commit()
    db.refresh(mensagem)
    return mensagem


def _historico_para_claude(
    mensagens: list[TriageMessage], max_mensagens: int | None = None
) -> list[dict[str, str]]:
    """Converte o histórico salvo no banco para o formato esperado pela API da Claude.

    Além da conversão, sana o histórico para que a chamada nunca seja rejeitada:
    - opcionalmente limita às últimas `max_mensagens` (janela de contexto do chat);
    - descarta mensagens vazias;
    - funde mensagens consecutivas do mesmo papel em um único turno (a API exige
      papéis alternados — sem isso, uma falha entre gravar a mensagem do aluno e
      obter a resposta deixaria o histórico inválido para sempre);
    - garante que a primeira mensagem seja do usuário.
    """
    if max_mensagens is not None:
        mensagens = mensagens[-max_mensagens:]

    resultado: list[dict[str, str]] = []
    for mensagem in mensagens:
        conteudo = (mensagem.content or "").strip()
        if not conteudo:
            continue
        role = mensagem.role if mensagem.role in ("user", "assistant") else "user"
        if resultado and resultado[-1]["role"] == role:
            resultado[-1]["content"] += "\n" + conteudo
        else:
            resultado.append({"role": role, "content": conteudo})

    while resultado and resultado[0]["role"] != "user":
        resultado.pop(0)
    return resultado


def _montar_nota_progresso(historico: list[TriageMessage]) -> str:
    """Gera nota de progresso determinística (sem chamada ao Claude) para injetar no system prompt.

    Varre os textos do assistente por palavras-chave dos 7 pontos da triagem e informa
    quais já foram iniciados. Retorna string vazia nos primeiros 4 turnos para não
    perturbar a saudação inicial.
    """
    qtd_user = sum(1 for m in historico if m.role == "user")
    qtd_assist = sum(1 for m in historico if m.role == "assistant")
    if qtd_user < 4:
        return ""

    textos_assist = " ".join(m.content.lower() for m in historico if m.role == "assistant")
    cobertos = [
        topico for topico, kws in _PALAVRAS_TOPICO.items()
        if any(kw in textos_assist for kw in kws)
    ]
    pendentes = [t for t in _PALAVRAS_TOPICO if t not in cobertos]

    linhas = [
        "--- Progresso da triagem (orientação interna — não mostre ao aluno) ---",
        f"Mensagens trocadas: {qtd_user} do aluno, {qtd_assist} do mentor.",
    ]
    if cobertos:
        linhas.append(f"Pontos já iniciados: {', '.join(cobertos)}.")
        linhas.append("NÃO repita perguntas sobre esses pontos; avance pelos pendentes.")
    if pendentes:
        linhas.append(f"Pontos ainda não abordados: {', '.join(pendentes)}.")
    return "\n".join(linhas)


def _contar_mensagens(db: Session, student_id: int) -> int:
    """Total de mensagens (aluno + mentor) já registradas na triagem do aluno."""
    return db.scalar(
        select(func.count()).select_from(TriageMessage).where(TriageMessage.student_id == student_id)
    ) or 0


def enviar_mensagem_triagem(db: Session, student_id: int, texto_aluno: str) -> str:
    """Registra a mensagem do aluno, consulta o Claude e registra/retorna a resposta do mentor.

    Levanta ValueError (→ HTTP 400 na rota) para mensagem vazia ou triagem no limite.
    A mensagem do aluno é persistida antes da chamada ao Claude: se a IA falhar, nada
    se perde — a sanitização do histórico mantém a conversa válida no próximo envio.
    """
    texto = (texto_aluno or "").strip()
    if not texto:
        raise ValueError("A mensagem não pode ser vazia.")

    if _contar_mensagens(db, student_id) >= LIMITE_MENSAGENS_TRIAGEM:
        raise ValueError(
            "A triagem atingiu o limite de mensagens. "
            "Clique em 'Finalizar triagem e gerar perfil' para concluir."
        )

    _registrar_mensagem(db, student_id, role="user", content=texto)

    historico_completo = obter_historico(db, student_id)
    historico = _historico_para_claude(historico_completo)  # histórico completo — sem limite de janela
    nota_progresso = _montar_nota_progresso(historico_completo)

    aluno = db.get(Student, student_id)
    nome_aluno = aluno.nome if aluno else None
    curso = aluno.curso if aluno else None
    periodo = aluno.periodo if aluno else None

    logger.info("Triagem: enviando mensagem ao Claude (student_id=%d, msgs=%d)", student_id, len(historico))
    resposta = claude_client.conversar_triagem(
        historico, nome_aluno=nome_aluno, curso=curso, periodo=periodo,
        nota_progresso=nota_progresso,
    )
    resposta = limpar_markdown(resposta)

    _registrar_mensagem(db, student_id, role="assistant", content=resposta)
    return resposta


def finalizar_triagem(db: Session, student_id: int) -> StudentProfile:
    """Gera o perfil estruturado a partir da conversa de triagem e salva (ou atualiza) no banco."""
    historico = _historico_para_claude(obter_historico(db, student_id))
    if not historico:
        raise ValueError("Não há conversa de triagem registrada para este aluno.")

    logger.info("Finalizando triagem e gerando perfil (student_id=%d, msgs=%d)", student_id, len(historico))
    profile_json = claude_client.gerar_perfil_estruturado(historico)
    _limpar_markdown_perfil(profile_json)

    perfil = upsert_registro(db, StudentProfile, student_id, profile_json=profile_json)
    logger.info("Perfil salvo/atualizado (student_id=%d)", student_id)
    return perfil


def _limpar_markdown_perfil(profile_json: dict) -> None:
    """Remove Markdown dos textos livres do perfil gerado pela IA (in-place)."""
    if isinstance(profile_json.get("resumo_geral"), str):
        profile_json["resumo_geral"] = limpar_markdown(profile_json["resumo_geral"])
    for area in profile_json.get("areas_afinidade") or []:
        if isinstance(area, dict):
            area["area"] = limpar_markdown(area.get("area", ""))
            area["porque"] = limpar_markdown(area.get("porque", ""))


# Chaves aditivas introduzidas após a primeira versão do profile_json. Perfis salvos
# antes dessa versão não têm essas chaves no JSON persistido.
_DEFAULTS_PERFIL_V2: dict = {
    "formacao": {"instituicao": "", "previsao_conclusao": "", "destaques_academicos": []},
    "certificacoes": [],
    "links": {"github": "", "linkedin": "", "portfolio": "", "outro": ""},
    "areas_afinidade": [],
}


def _normalizar_item_stack(item) -> dict:
    """Aceita item da stack como string OU dict {nome, nivel}; devolve sempre dict.

    Retrocompatível com o formato antigo (listas de string) — quando o item é uma
    string, o nível fica em branco. Perfis novos já vêm no formato dict.
    """
    if isinstance(item, str):
        return {"nome": item.strip(), "nivel": ""}
    if isinstance(item, dict):
        return {"nome": str(item.get("nome", "")).strip(), "nivel": item.get("nivel") or ""}
    return {"nome": "", "nivel": ""}


def _aplicar_defaults_perfil(profile_json: dict) -> dict:
    """Garante formacao/certificacoes/links e experiencias[].resultados em perfis salvos
    antes dessas chaves existirem. Não persiste — usado apenas em obter_perfil().

    Também normaliza `stack_tecnica.linguagens` e `stack_tecnica.frameworks_ferramentas`
    para o novo formato `[{"nome", "nivel"}]`. Perfis antigos (listas de string) são
    convertidos em tempo de leitura — sem migração de banco.
    """
    resultado = dict(profile_json)
    for chave, default in _DEFAULTS_PERFIL_V2.items():
        resultado.setdefault(chave, default)
    resultado["experiencias"] = [
        {**{"resultados": ""}, **exp} for exp in resultado.get("experiencias", [])
    ]
    stack = dict(resultado.get("stack_tecnica") or {})
    stack["linguagens"] = [_normalizar_item_stack(x) for x in (stack.get("linguagens") or []) if x]
    stack["frameworks_ferramentas"] = [
        _normalizar_item_stack(x) for x in (stack.get("frameworks_ferramentas") or []) if x
    ]
    # Remove o antigo `nivel_geral` — deixou de fazer parte do escopo.
    stack.pop("nivel_geral", None)
    resultado["stack_tecnica"] = stack
    return resultado


def obter_perfil(db: Session, student_id: int) -> StudentProfile | None:
    """Retorna o perfil estruturado salvo de um aluno, se existir.

    Aplica defaults para chaves aditivas (formacao/certificacoes/links/resultados) em
    perfis antigos, garantindo que templates e gerar_pdi/gerar_curriculo sempre recebam
    o profile_json com essas chaves presentes.
    """
    perfil = db.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id))
    if perfil is not None:
        perfil.profile_json = _aplicar_defaults_perfil(perfil.profile_json)
    return perfil


def atualizar_perfil(db: Session, student_id: int, profile_json: dict) -> StudentProfile:
    """Salva o perfil estruturado editado pelo aluno (sobrescreve o existente).

    Levanta ValueError se o aluno ainda não tem perfil gerado — só faz sentido editar
    um perfil que já foi produzido a partir da triagem.
    """
    if obter_perfil(db, student_id) is None:
        raise ValueError("O aluno ainda não possui perfil (conclua a triagem primeiro).")

    perfil = upsert_registro(db, StudentProfile, student_id, profile_json=profile_json)
    logger.info("Perfil editado para student_id=%d", student_id)
    return perfil


def aluno_existe(db: Session, student_id: int) -> bool:
    """Verifica se um aluno com o id informado está cadastrado."""
    return db.get(Student, student_id) is not None
