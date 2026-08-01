"""Modelos Pydantic usados nas requisições e respostas da API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class StudentCreate(BaseModel):
    """Dados necessários para cadastrar um novo aluno."""

    nome: str = Field(min_length=1, max_length=200)
    email: EmailStr
    periodo: int = Field(ge=1, le=8, description="Período letivo atual (1 a 8)")
    senha: str = Field(min_length=8, max_length=128, description="Senha de acesso (mínimo 8 caracteres)")
    codigo_convite: str = Field(
        default="",
        max_length=100,
        description="Código de convite (obrigatório apenas quando INVITE_CODE está configurado).",
    )


class LoginRequest(BaseModel):
    """Credenciais usadas para autenticação."""

    email: EmailStr
    senha: str = Field(min_length=1)


class StudentRead(BaseModel):
    """Representação de um aluno retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    curso: str
    periodo: int
    created_at: datetime


class TriageMensagemEnvio(BaseModel):
    """Mensagem enviada pelo aluno durante a triagem."""

    mensagem: str = Field(min_length=1, max_length=5000, description="Texto da mensagem (1–5000 caracteres)")

    @field_validator("mensagem")
    @classmethod
    def _normalizar_mensagem(cls, valor: str) -> str:
        """Remove espaços das pontas e rejeita mensagens compostas só de espaços."""
        valor = valor.strip()
        if not valor:
            raise ValueError("A mensagem não pode ser vazia.")
        return valor


class TriageMensagemRead(BaseModel):
    """Mensagem do histórico de triagem retornada pela API."""

    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime


class TriageRespostaRead(BaseModel):
    """Resposta do mentor (Claude) a uma mensagem de triagem."""

    resposta: str


class StudentProfileRead(BaseModel):
    """Perfil estruturado do aluno gerado ao final da triagem."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    profile_json: dict
    created_at: datetime


class PDIRead(BaseModel):
    """Plano de Desenvolvimento Individual gerado para o aluno."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    pdi_json: dict
    created_at: datetime


class CurriculumRead(BaseModel):
    """Currículo em formato amigável para ATS gerado para o aluno."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    curriculum_text: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Edição de Perfil (estrutura espelha o profile_json gerado pela IA)
# ---------------------------------------------------------------------------


class ObjetivoCarreiraEdit(BaseModel):
    """Objetivo de carreira editável (curto/médio prazo e áreas de interesse)."""

    curto_prazo: str = Field(default="", max_length=2000)
    medio_prazo: str = Field(default="", max_length=2000)
    areas_interesse: list[str] = Field(default_factory=list, max_length=50)


class ExperienciaEdit(BaseModel):
    """Uma experiência (estágio, freela, projeto, etc.) editável."""

    tipo: Literal["estagio", "freela", "projeto_pessoal", "projeto_academico", "voluntariado"] = (
        "projeto_pessoal"
    )
    titulo: str = Field(min_length=1, max_length=300)
    descricao: str = Field(default="", max_length=3000)
    periodo: str = Field(default="", max_length=200)
    tecnologias: list[str] = Field(default_factory=list, max_length=50)
    resultados: str = Field(default="", max_length=1000)


class DisciplinaEdit(BaseModel):
    """Uma disciplina relevante editável."""

    nome: str = Field(min_length=1, max_length=300)
    relevancia: str = Field(default="", max_length=2000)


class StackItemEdit(BaseModel):
    """Uma linguagem ou ferramenta com o nível declarado pelo aluno."""

    nome: str = Field(min_length=1, max_length=120)
    nivel: Literal["", "basico", "intermediario", "avancado"] = ""


class StackTecnicaEdit(BaseModel):
    """Stack técnica editável: cada linguagem e ferramenta tem o próprio nível."""

    linguagens: list[StackItemEdit] = Field(default_factory=list, max_length=100)
    frameworks_ferramentas: list[StackItemEdit] = Field(default_factory=list, max_length=100)


class RestricoesEdit(BaseModel):
    """Disponibilidade e restrições editáveis."""

    carga_horaria_disponivel: str = Field(default="", max_length=300)
    localizacao: str = Field(default="", max_length=300)
    modalidade_preferida: Literal["presencial", "remoto", "hibrido", "indiferente"] = "indiferente"
    outras: str = Field(default="", max_length=2000)


class FormacaoEdit(BaseModel):
    """Formação acadêmica complementar editável."""

    instituicao: str = Field(default="", max_length=300)
    previsao_conclusao: str = Field(default="", max_length=100)
    destaques_academicos: list[str] = Field(default_factory=list, max_length=20)


class CertificacaoEdit(BaseModel):
    """Uma certificação editável."""

    nome: str = Field(min_length=1, max_length=300)
    instituicao: str = Field(default="", max_length=300)
    ano: str = Field(default="", max_length=20)


class LinksEdit(BaseModel):
    """Links públicos (GitHub, LinkedIn, portfólio etc.) editáveis."""

    github: str = Field(default="", max_length=300)
    linkedin: str = Field(default="", max_length=300)
    portfolio: str = Field(default="", max_length=300)
    outro: str = Field(default="", max_length=300)


class AreaAfinidadeEdit(BaseModel):
    """Uma área de afinidade sugerida pela IA (área + porque combina com o aluno)."""

    area: str = Field(default="", max_length=120)
    porque: str = Field(default="", max_length=600)


class PerfilUpdate(BaseModel):
    """Perfil estruturado completo enviado ao salvar a edição do perfil."""

    objetivo_carreira: ObjetivoCarreiraEdit
    experiencias: list[ExperienciaEdit] = Field(default_factory=list, max_length=50)
    disciplinas_relevantes: list[DisciplinaEdit] = Field(default_factory=list, max_length=50)
    stack_tecnica: StackTecnicaEdit
    soft_skills: list[str] = Field(default_factory=list, max_length=50)
    restricoes: RestricoesEdit
    resumo_geral: str = Field(default="", max_length=4000)
    formacao: FormacaoEdit = Field(default_factory=FormacaoEdit)
    certificacoes: list[CertificacaoEdit] = Field(default_factory=list, max_length=20)
    links: LinksEdit = Field(default_factory=LinksEdit)
    areas_afinidade: list[AreaAfinidadeEdit] = Field(default_factory=list, max_length=8)


# ---------------------------------------------------------------------------
# Edição de PDI (campos estratégicos; o quadro Kanban é editado à parte)
# ---------------------------------------------------------------------------


class CompetenciaEdit(BaseModel):
    """Uma competência a desenvolver (nome + motivo) editável."""

    nome: str = Field(min_length=1, max_length=300)
    motivo: str = Field(default="", max_length=2000)


class CronogramaBlocoEdit(BaseModel):
    """Um bloco do cronograma (período, foco e atividades) editável."""

    periodo: str = Field(min_length=1, max_length=200)
    foco: str = Field(default="", max_length=500)
    atividades: list[str] = Field(default_factory=list, max_length=50)


class PDIUpdate(BaseModel):
    """Campos estratégicos do PDI enviados ao salvar a edição (sem o quadro)."""

    objetivo_geral: str = Field(default="", max_length=3000)
    metas_curto_prazo: list[str] = Field(default_factory=list, max_length=50)
    metas_medio_prazo: list[str] = Field(default_factory=list, max_length=50)
    competencias_a_desenvolver: list[CompetenciaEdit] = Field(default_factory=list, max_length=50)
    cronograma: list[CronogramaBlocoEdit] = Field(default_factory=list, max_length=20)


# ---------------------------------------------------------------------------
# Quadro Kanban do PDI
# ---------------------------------------------------------------------------


class QuadroCard(BaseModel):
    """Um card do quadro Kanban do PDI."""

    id: str = Field(min_length=1, max_length=64)
    texto: str = Field(min_length=1, max_length=500)
    coluna: Literal["a_fazer", "em_progresso", "concluido"]
    categoria: str = Field(default="", max_length=100)


class QuadroUpdate(BaseModel):
    """Estado completo do quadro Kanban enviado a cada movimento/edição de card."""

    cards: list[QuadroCard] = Field(default_factory=list, max_length=200)


# ---------------------------------------------------------------------------
# Edição de Currículo
# ---------------------------------------------------------------------------


class CurriculoUpdate(BaseModel):
    """Texto do currículo enviado ao salvar a edição."""

    curriculum_text: str = Field(min_length=1, max_length=20000)

    @field_validator("curriculum_text")
    @classmethod
    def _normalizar_texto(cls, valor: str) -> str:
        """Remove espaços das pontas e rejeita texto composto só de espaços."""
        valor = valor.strip()
        if not valor:
            raise ValueError("O currículo não pode ficar vazio.")
        return valor


# ---------------------------------------------------------------------------
# Análise de Vaga (JD Analyzer)
# ---------------------------------------------------------------------------


class AnaliseVagaInput(BaseModel):
    """Descrição de vaga colada pelo aluno para análise de aderência."""

    jd_text: str = Field(
        min_length=50,
        max_length=8000,
        description="Texto completo da descrição de vaga",
    )

    @field_validator("jd_text")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("A descrição da vaga não pode ser vazia.")
        return v
