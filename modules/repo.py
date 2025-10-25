# modules/repo.py
from __future__ import annotations

import re
from datetime import datetime, date
from typing import Optional, Dict, Any

from sqlalchemy import Text, Date, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from dateutil import parser as dateparser

from .db import Base, session_scope, SessionLocal 

# -----------------------------------------------------------------------------
# MODELO
# -----------------------------------------------------------------------------
class Patient(Base):
    __tablename__ = "patients"

    pac_id: Mapped[str] = mapped_column(PGUUID(as_uuid=False), primary_key=True)
    name:   Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email:  Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    phone_norm: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    dob:        Mapped[date] = mapped_column(Date,  nullable=False, index=True)

    respostas:      Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    plano:          Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    plano_compacto: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    macros:         Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(Text, nullable=False, default="pendente_validacao")

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

# -----------------------------------------------------------------------------
# INIT (create_all)
# -----------------------------------------------------------------------------
def init_models() -> None:
    """Cria as tabelas caso não existam (MVP sem Alembic)."""
    from .db import engine
    Base.metadata.create_all(bind=engine)

# -----------------------------------------------------------------------------
# HELPERS DE NORMALIZAÇÃO
# -----------------------------------------------------------------------------
def normalize_phone(phone_raw: str) -> str:
    """Mantém apenas dígitos (compatível com DDD + 9 dígitos no BR)."""
    return re.sub(r"\D", "", phone_raw or "")

def parse_dob_to_date(dob_input: str) -> date:
    """
    Aceita formatos comuns (DD/MM/AAAA, AAAA-MM-DD, DD-MM-AAAA etc).
    Retorna datetime.date. Prioriza dayfirst.
    """
    s = (dob_input or "").strip()
    # tenta alguns formatos comuns antes do dateutil
    fmts = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # fallback tolerante
    dtx = dateparser.parse(s, dayfirst=True)
    if not dtx:
        raise ValueError("Data de nascimento inválida. Use DD/MM/AAAA.")
    return dtx.date()

# -----------------------------------------------------------------------------
# REPOSITÓRIO
# -----------------------------------------------------------------------------
def upsert_patient_payload(
    pac_id: Optional[str],
    respostas: Dict[str, Any],
    plano: Dict[str, Any],
    plano_compacto: Dict[str, Any],
    macros: Dict[str, Any],
    name: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """
    Cria ou atualiza o paciente com dados agregados (respostas + plano + macros).
    Retorna pac_id.
    """
    phone = normalize_phone(respostas.get("telefone", ""))
    if not phone:
        raise ValueError("Telefone ausente.")

    dob = parse_dob_to_date(respostas.get("data_nascimento", ""))

    with session_scope() as s:
        obj: Patient | None = s.get(Patient, pac_id) if pac_id else None

        if obj is None:
            obj = Patient(
                phone_norm=phone,
                dob=dob,
                respostas=respostas,
                plano=plano,
                plano_compacto=plano_compacto,
                macros=macros,
                status="pendente_validacao",
                name=name,
                email=email,
            )
            s.add(obj)
            s.flush()  # gera pac_id
        else:
            obj.phone_norm = phone
            obj.dob = dob
            obj.respostas = respostas
            obj.plano = plano
            obj.plano_compacto = plano_compacto
            obj.macros = macros
            if name is not None:
                obj.name = name
            if email is not None:
                obj.email = email

        return obj.pac_id



# modules/repo.py
from sqlalchemy import text
from dateutil import parser
from .db import SessionLocal


def get_by_phone_dob(telefone: str, dob_str: str):
    """Busca paciente pelo telefone (somente números) e data de nascimento DD/MM/AAAA."""
    telefone = "".join(ch for ch in telefone if ch.isdigit())

    try:
        dob = parser.parse(dob_str, dayfirst=True).date()
    except Exception:
        raise ValueError("Data inválida. Use o formato DD/MM/AAAA.")

    sql = text("""
        SELECT *
        FROM patients
        WHERE REPLACE(REPLACE(respostas->>'telefone', '-', ''), ' ', '') = :telefone
          AND (
            respostas->>'data_nascimento' = TO_CHAR(:dob::date, 'DD/MM/YYYY')
            OR respostas->>'data_nascimento' = TO_CHAR(:dob::date, 'YYYY-MM-DD')
          )
        LIMIT 1
    """)

    with SessionLocal() as s:
        row = s.execute(sql, {"telefone": telefone, "dob": dob}).mappings().first()
        return dict(row) if row else None
                
def get_by_pac_id(pac_id: str) -> Optional[Dict[str, Any]]:
    with session_scope() as s:
        obj = s.get(Patient, pac_id)
        if not obj:
            return None
        return {
            "pac_id": obj.pac_id,
            "name": obj.name,
            "email": obj.email,
            "respostas": obj.respostas,
            "plano_alimentar": obj.plano,
            "plano_alimentar_compacto": obj.plano_compacto,
            "macros": obj.macros,
            "status": obj.status,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }