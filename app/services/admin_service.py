"""Lógica do painel de administração: métricas, diagnóstico e gestão de alunos.

Concentra as consultas agregadas (para as visualizações), o diagnóstico automático
do sistema e as operações de gestão (promover/rebaixar admin, excluir aluno). Mantém
as rotas (`app/routes/admin.py`) finas.
"""

import logging
from collections import Counter

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.config import SECRET_KEY_INSEGURA, get_settings
from app.models import PDI, Curriculum, CurriculumAnalise, CurriculumVaga, Student, StudentProfile, TriageMessage
from app.services.student_service import normalizar_email

logger = logging.getLogger(__name__)


def _conta_como_admin(aluno: Student, emails_admin: set[str]) -> bool:
    """Admin via flag no banco OU e-mail em ADMIN_EMAILS (mesma regra do guard)."""
    return bool(aluno.is_admin) or normalizar_email(aluno.email) in emails_admin


# ---------------------------------------------------------------------------
# Métricas / visualizações
# ---------------------------------------------------------------------------


def _ids_com_registro(db: Session, model_class) -> set[int]:
    """Conjunto de student_ids que possuem ao menos um registro do modelo dado."""
    return set(db.scalars(select(model_class.student_id)).all())


def obter_metricas(db: Session) -> dict:
    """Agrega os números do sistema e os dados para as representações visuais.

    Retorna KPIs, o funil de conclusão (cadastro → triagem → perfil → PDI → currículo),
    a distribuição por período letivo e os cadastros por mês.
    """
    alunos = list(db.scalars(select(Student).order_by(Student.created_at)).all())
    total = len(alunos)

    ids_triagem = _ids_com_registro(db, TriageMessage)
    ids_perfil = _ids_com_registro(db, StudentProfile)
    ids_pdi = _ids_com_registro(db, PDI)
    ids_curriculo = _ids_com_registro(db, Curriculum)

    com_triagem = len(ids_triagem)
    com_perfil = len(ids_perfil)
    com_pdi = len(ids_pdi)
    com_curriculo = len(ids_curriculo)
    emails_admin = get_settings().emails_admin
    admins = sum(1 for a in alunos if _conta_como_admin(a, emails_admin))

    # Funil: cada etapa com contagem e percentual relativo ao total de alunos.
    def _pct(n: int) -> int:
        return round(n / total * 100) if total else 0

    funil = [
        {"etapa": "Cadastrados", "valor": total, "pct": 100 if total else 0},
        {"etapa": "Iniciaram triagem", "valor": com_triagem, "pct": _pct(com_triagem)},
        {"etapa": "Perfil gerado", "valor": com_perfil, "pct": _pct(com_perfil)},
        {"etapa": "PDI gerado", "valor": com_pdi, "pct": _pct(com_pdi)},
        {"etapa": "Currículo gerado", "valor": com_curriculo, "pct": _pct(com_curriculo)},
    ]

    # Distribuição por período letivo (1..12).
    contagem_periodo = Counter(a.periodo for a in alunos)
    max_periodo = max(contagem_periodo.values()) if contagem_periodo else 0
    por_periodo = [
        {
            "periodo": p,
            "valor": contagem_periodo.get(p, 0),
            "pct": round(contagem_periodo.get(p, 0) / max_periodo * 100) if max_periodo else 0,
        }
        for p in range(1, 9)
    ]

    # Cadastros por mês (YYYY-MM), em ordem cronológica.
    contagem_mes: Counter = Counter()
    for a in alunos:
        if a.created_at is not None:
            contagem_mes[a.created_at.strftime("%Y-%m")] += 1
    max_mes = max(contagem_mes.values()) if contagem_mes else 0
    por_mes = [
        {"mes": mes, "valor": valor, "pct": round(valor / max_mes * 100) if max_mes else 0}
        for mes, valor in sorted(contagem_mes.items())
    ]

    return {
        "total": total,
        "com_triagem": com_triagem,
        "com_perfil": com_perfil,
        "com_pdi": com_pdi,
        "com_curriculo": com_curriculo,
        "admins": admins,
        "mensagens_triagem": db.scalar(select(func.count()).select_from(TriageMessage)) or 0,
        "funil": funil,
        "por_periodo": por_periodo,
        "por_mes": por_mes,
    }


# ---------------------------------------------------------------------------
# Diagnóstico automático ("verificar tudo")
# ---------------------------------------------------------------------------

_TABELAS_ESPERADAS = [
    "students",
    "triage_messages",
    "student_profiles",
    "pdis",
    "curriculums",
    "curriculum_vagas",
    "curriculum_analises",
]


def obter_diagnostico(db: Session) -> list[dict]:
    """Executa verificações automáticas do sistema e retorna o status de cada uma.

    Cada item tem: nome, status ('ok' | 'aviso' | 'erro') e um detalhe legível.
    """
    settings = get_settings()
    checks: list[dict] = []

    # 1. Conexão com o banco
    try:
        db.execute(text("SELECT 1"))
        checks.append({"nome": "Banco de dados", "status": "ok", "detalhe": "Conexão respondendo."})
    except Exception as erro:  # pragma: no cover - difícil de simular em teste
        checks.append({"nome": "Banco de dados", "status": "erro", "detalhe": f"Falha: {erro}"})

    # 2. Tabelas criadas (inspeciona o mesmo engine da sessão atual)
    try:
        existentes = set(inspect(db.get_bind()).get_table_names())
        faltando = [t for t in _TABELAS_ESPERADAS if t not in existentes]
        if faltando:
            checks.append({"nome": "Esquema (tabelas)", "status": "erro", "detalhe": f"Faltando: {', '.join(faltando)}"})
        else:
            checks.append({"nome": "Esquema (tabelas)", "status": "ok", "detalhe": f"{len(_TABELAS_ESPERADAS)} tabelas presentes."})
    except Exception as erro:  # pragma: no cover
        checks.append({"nome": "Esquema (tabelas)", "status": "erro", "detalhe": str(erro)})

    # 3. Chave da Anthropic
    chave = settings.anthropic_api_key
    if not chave or chave in ("", "sk-test-dummy"):
        checks.append({"nome": "ANTHROPIC_API_KEY", "status": "aviso", "detalhe": "Ausente ou de teste — geração por IA indisponível."})
    else:
        checks.append({"nome": "ANTHROPIC_API_KEY", "status": "ok", "detalhe": "Configurada."})

    # 4. SECRET_KEY
    if settings.secret_key == SECRET_KEY_INSEGURA:
        checks.append({"nome": "SECRET_KEY", "status": "aviso", "detalhe": "Usando o valor padrão inseguro (troque em produção)."})
    else:
        checks.append({"nome": "SECRET_KEY", "status": "ok", "detalhe": "Personalizada."})

    # 5. Ambiente
    checks.append({"nome": "Ambiente (APP_ENV)", "status": "ok", "detalhe": settings.app_env})

    # 6. Cookie Secure
    if settings.session_https_only:
        checks.append({"nome": "Cookie de sessão (Secure)", "status": "ok", "detalhe": "Apenas HTTPS."})
    else:
        nivel = "aviso" if settings.app_env == "production" else "ok"
        checks.append({"nome": "Cookie de sessão (Secure)", "status": nivel, "detalhe": "Trafega por HTTP (ok em desenvolvimento)."})

    # 7. Admins configurados
    n_admins = db.scalar(select(func.count()).select_from(Student).where(Student.is_admin.is_(True))) or 0
    n_env = len(settings.emails_admin)
    if n_admins or n_env:
        checks.append({"nome": "Administradores", "status": "ok", "detalhe": f"{n_admins} no banco + {n_env} em ADMIN_EMAILS."})
    else:
        checks.append({"nome": "Administradores", "status": "aviso", "detalhe": "Nenhum admin configurado."})

    return checks


def resumo_diagnostico(checks: list[dict]) -> dict:
    """Conta quantas verificações estão em cada status."""
    contagem = Counter(c["status"] for c in checks)
    return {"ok": contagem.get("ok", 0), "aviso": contagem.get("aviso", 0), "erro": contagem.get("erro", 0)}


# ---------------------------------------------------------------------------
# Configuração (somente leitura, com segredos mascarados)
# ---------------------------------------------------------------------------


def _mascarar(valor: str) -> str:
    """Mascara um segredo, mostrando apenas pistas (início/fim)."""
    if not valor:
        return "(não definido)"
    if len(valor) <= 8:
        return "••••••"
    return f"{valor[:4]}••••{valor[-2:]}"


def obter_config(db: Session) -> list[dict]:
    """Retorna as configurações atuais para exibição (segredos mascarados, somente leitura)."""
    s = get_settings()
    return [
        {"chave": "APP_ENV", "valor": s.app_env, "sensivel": False},
        {"chave": "CLAUDE_MODEL", "valor": s.claude_model, "sensivel": False},
        {
            "chave": "CLAUDE_MODEL_ANALISE",
            "valor": s.claude_model_analise or f"(usa CLAUDE_MODEL: {s.claude_model})",
            "sensivel": False,
        },
        {
            "chave": "CLAUDE_MODEL_GERACAO",
            "valor": s.claude_model_geracao or f"(usa CLAUDE_MODEL: {s.claude_model})",
            "sensivel": False,
        },
        {"chave": "DATABASE_URL", "valor": s.database_url, "sensivel": False},
        {"chave": "SESSION_MAX_AGE", "valor": f"{s.session_max_age} s", "sensivel": False},
        {"chave": "SESSION_HTTPS_ONLY", "valor": str(s.session_https_only), "sensivel": False},
        {"chave": "ADMIN_EMAILS", "valor": ", ".join(sorted(s.emails_admin)) or "(nenhum)", "sensivel": False},
        {"chave": "ANTHROPIC_API_KEY", "valor": _mascarar(s.anthropic_api_key), "sensivel": True},
        {"chave": "SECRET_KEY", "valor": _mascarar(s.secret_key), "sensivel": True},
    ]


# ---------------------------------------------------------------------------
# Gestão de alunos
# ---------------------------------------------------------------------------


def listar_alunos(db: Session) -> list[dict]:
    """Lista todos os alunos com o status de cada etapa (para a tabela do admin)."""
    alunos = list(db.scalars(select(Student).order_by(Student.created_at.desc())).all())
    ids_triagem = _ids_com_registro(db, TriageMessage)
    ids_perfil = _ids_com_registro(db, StudentProfile)
    ids_pdi = _ids_com_registro(db, PDI)
    ids_curriculo = _ids_com_registro(db, Curriculum)

    return [
        {
            "aluno": a,
            "tem_triagem": a.id in ids_triagem,
            "tem_perfil": a.id in ids_perfil,
            "tem_pdi": a.id in ids_pdi,
            "tem_curriculo": a.id in ids_curriculo,
        }
        for a in alunos
    ]


def obter_aluno_detalhe(db: Session, student_id: int) -> dict | None:
    """Retorna o aluno e o estado de cada artefato, ou None se não existir."""
    aluno = db.get(Student, student_id)
    if aluno is None:
        return None
    n_mensagens = db.scalar(
        select(func.count()).select_from(TriageMessage).where(TriageMessage.student_id == student_id)
    ) or 0
    return {
        "aluno": aluno,
        "perfil": db.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id)),
        "pdi": db.scalar(select(PDI).where(PDI.student_id == student_id)),
        "curriculo": db.scalar(select(Curriculum).where(Curriculum.student_id == student_id)),
        "n_mensagens": n_mensagens,
    }


def definir_admin(db: Session, student_id: int, valor: bool) -> Student | None:
    """Promove (valor=True) ou rebaixa (valor=False) um aluno a administrador."""
    aluno = db.get(Student, student_id)
    if aluno is None:
        return None
    aluno.is_admin = valor
    db.commit()
    db.refresh(aluno)
    logger.info("Admin %s para student_id=%d", "concedido" if valor else "removido", student_id)
    return aluno


def excluir_aluno(db: Session, student_id: int) -> bool:
    """Exclui o aluno e todos os seus dados (triagem, perfil, PDI, currículos).

    Retorna True se excluiu, False se o aluno não existia.
    """
    aluno = db.get(Student, student_id)
    if aluno is None:
        return False
    for model_class in (TriageMessage, StudentProfile, PDI, Curriculum, CurriculumVaga, CurriculumAnalise):
        for registro in db.scalars(select(model_class).where(model_class.student_id == student_id)).all():
            db.delete(registro)
    db.delete(aluno)
    db.commit()
    logger.info("Aluno excluído: id=%d", student_id)
    return True
