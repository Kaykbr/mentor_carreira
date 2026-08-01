"""Monta o contexto compartilhado do aluno (dados de Student) usado por PDI e currículo.

Centraliza dados do cadastro (nome, e-mail, curso, período) que hoje não fazem parte do
profile_json mas ajudam a calibrar o PDI e a enriquecer o cabeçalho/FORMAÇÃO do currículo.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import Student


@dataclass
class ContextoAluno:
    """Dados do cadastro do aluno relevantes para geração de PDI e currículo."""

    nome: str
    email: str
    curso: str
    periodo: int


def montar_contexto(db: Session, student_id: int) -> ContextoAluno | None:
    """Monta o `ContextoAluno` a partir do `Student`, ou `None` se o aluno não existir."""
    aluno = db.get(Student, student_id)
    if aluno is None:
        return None
    return ContextoAluno(nome=aluno.nome, email=aluno.email, curso=aluno.curso, periodo=aluno.periodo)


def enriquecer_contexto(contexto_dict: dict, profile_json: dict) -> dict:
    """Acrescenta ao contexto o enriquecimento determinístico comum a PDI e currículo.

    Preenche `nivel_experiencia` (calculado do perfil), `restricoes` (só valores
    preenchidos) e a data atual (`data_hoje`/`ano_atual`, para o modelo não "chutar" anos do
    passado no cronograma). Compartilhado por `pdi_service` e `curriculum_service` — ponto
    único para evoluir esse enriquecimento.
    """
    contexto_dict["nivel_experiencia"] = calcular_nivel_experiencia(profile_json)
    hoje = date.today()
    contexto_dict["data_hoje"] = hoje.isoformat()
    contexto_dict["ano_atual"] = hoje.year
    restricoes = {k: v for k, v in profile_json.get("restricoes", {}).items() if v}
    if restricoes:
        contexto_dict["restricoes"] = restricoes
    return contexto_dict


def calcular_nivel_experiencia(profile_json: dict) -> str:
    """Classifica o nível de experiência do aluno a partir do perfil estruturado.

    Atributo derivado compartilhado por PDI e currículo (ambos calibram a saída por este
    nível). Vive aqui, junto do contexto do aluno, para não acoplar um serviço ao privado
    do outro.
    """
    experiencias = profile_json.get("experiencias", [])
    tipos = {e.get("tipo", "") for e in experiencias}
    if "estagio" in tipos or "freela" in tipos:
        return "intermediario"
    if len(experiencias) >= 2:
        return "iniciante_com_projetos"
    if len(experiencias) == 1:
        return "iniciante"
    return "sem_experiencia"
