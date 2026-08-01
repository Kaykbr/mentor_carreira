"""Modelos ORM (SQLAlchemy) do projeto."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _agora() -> datetime:
    """Retorna o horário atual em UTC (usado como default de `created_at`)."""
    return datetime.now(timezone.utc)


class Student(Base):
    """Aluno cadastrado no sistema."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    curso: Mapped[str] = mapped_column(String(255), nullable=False, default="Sistemas de Informação")
    periodo: Mapped[int] = mapped_column(Integer, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    profile: Mapped["StudentProfile | None"] = relationship(back_populates="student", uselist=False)
    pdi: Mapped["PDI | None"] = relationship(back_populates="student", uselist=False)
    curriculum: Mapped["Curriculum | None"] = relationship(back_populates="student", uselist=False)
    curriculum_vagas: Mapped[list["CurriculumVaga"]] = relationship(back_populates="student")
    curriculum_analise: Mapped["CurriculumAnalise | None"] = relationship(back_populates="student", uselist=False)


class TriageMessage(Base):
    """Mensagem trocada durante a conversa de triagem (histórico mantido pelo servidor)."""

    __tablename__ = "triage_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)


class StudentProfile(Base):
    """Perfil estruturado do aluno, gerado a partir da triagem."""

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, unique=True)
    profile_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    student: Mapped["Student"] = relationship(back_populates="profile")


class PDI(Base):
    """Plano de Desenvolvimento Individual gerado para o aluno."""

    __tablename__ = "pdis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, unique=True)
    pdi_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    student: Mapped["Student"] = relationship(back_populates="pdi")


class Curriculum(Base):
    """Currículo em formato amigável para ATS gerado para o aluno."""

    __tablename__ = "curriculums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, unique=True)
    curriculum_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    student: Mapped["Student"] = relationship(back_populates="curriculum")


class CurriculumVaga(Base):
    """Currículo direcionado a uma vaga específica (N por aluno).

    Guarda a vaga original (`jd_text`), a análise de aderência + recomendações
    (`analise_json`) e o currículo otimizado para as palavras-chave da vaga.
    Diferente dos demais artefatos, NÃO tem constraint UNIQUE em `student_id`.
    """

    __tablename__ = "curriculum_vagas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    cargo: Mapped[str] = mapped_column(String(255), nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    analise_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    curriculum_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    student: Mapped["Student"] = relationship(back_populates="curriculum_vagas")


class CurriculumAnalise(Base):
    """Análise qualitativa do currículo base feita pela IA (1 por aluno).

    O diagnóstico determinístico (`curriculo_qualidade.diagnosticar`) é recalculado a
    cada exibição e NÃO fica aqui — só as dicas geradas pela IA, que custam uma chamada.
    `texto_hash` guarda o SHA-256 do currículo analisado: se o aluno editar ou regerar o
    texto depois, a interface detecta que a análise ficou defasada.
    """

    __tablename__ = "curriculum_analises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, unique=True)
    analise_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    texto_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    student: Mapped["Student"] = relationship(back_populates="curriculum_analise")
