"""Utilitários compartilhados entre os serviços de domínio.

Centraliza padrões repetidos (ex.: create-or-update por student_id) para
eliminar duplicação em profile_service, pdi_service e curriculum_service.
"""

from typing import Any, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


def upsert_registro(db: Session, model_class: Type[T], student_id: int, **campos: Any) -> T:
    """Cria ou atualiza um registro único identificado por student_id.

    Se não existir nenhum registro com aquele student_id, cria um novo
    passando os campos fornecidos via **kwargs.
    Se já existir, atualiza apenas os campos fornecidos via setattr.

    Ao final, faz commit e refresh — retorna o objeto atualizado.

    Exemplo:
        perfil = upsert_registro(db, StudentProfile, aluno_id, profile_json=dados)
        pdi    = upsert_registro(db, PDI, aluno_id, pdi_json=dados)
        cv     = upsert_registro(db, Curriculum, aluno_id, curriculum_text=texto)
    """
    registro = db.scalar(
        select(model_class).where(model_class.student_id == student_id)  # type: ignore[attr-defined]
    )
    if registro is None:
        registro = model_class(student_id=student_id, **campos)  # type: ignore[call-arg]
        db.add(registro)
    else:
        for chave, valor in campos.items():
            setattr(registro, chave, valor)
    db.commit()
    db.refresh(registro)
    return registro  # type: ignore[return-value]
