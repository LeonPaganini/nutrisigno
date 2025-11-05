# modules/repo.py
from __future__ import annotations

import re
import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any

from sqlalchemy import Text, Date, TIMESTAMP, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON as SQLJSON

from dateutil import parser as dateparser

from .db import Base, session_scope, SessionLocal, engine

UUID_TYPE = PGUUID(as_uuid=False) if engine.dialect.name != "sqlite" else Text
JSON_TYPE = JSONB if engine.dialect.name != "sqlite" else SQLJSON


# -----------------------------------------------------------------------------
# MODELO
# -----------------------------------------------------------------------------
class Patient(Base):
    __tablename__ = "patients"

    pac_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name:   Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email:  Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    phone_norm: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    dob:        Mapped[date] = mapped_column(Date,  nullable=False, index=True)

    respostas:      Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    plano:          Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    plano_compacto: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    macros:         Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(Text, nullable=False, default="pendente_validacao")

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


# -----------------------------------------------------------------------------
# INIT (create_all)
# -----------------------------------------------------------------------------
def init_models() -> None:
    """Cria as tabelas caso não existam (MVP sem Alembic)."""
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
    fmts = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    dtx = dateparser.parse(s, dayfirst=True)
    if not dtx:
        raise ValueError("Data de nascimento inválida. Use DD/MM/AAAA.")
    return dtx.date()

def to_br_date_str(d: date | datetime) -> str:
    """Converte para DD/MM/AAAA."""
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")


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


# -----------------------------------------------------------------------------
# CONSULTAS (sem erros de placeholder)
# -----------------------------------------------------------------------------
def get_by_phone_dob(telefone: str, dob_str: str):
    """
    Busca paciente pelo telefone e data de nascimento.
    Aceita DD/MM/AAAA e YYYY-MM-DD.
    Compatível com registros antigos e novos no JSON.
    """
    telefone = normalize_phone(telefone)
    dob = parse_dob_to_date(dob_str)

    sql = text("""
        SELECT pac_id
        FROM patients
        WHERE (
                phone_norm = :telefone
             OR REPLACE(REPLACE(respostas->>'telefone', '-', ''), ' ', '') = :telefone
              )
          AND (
                dob = :dob
             OR COALESCE(
                    to_date(respostas->>'data_nascimento', 'DD/MM/YYYY'),
                    to_date(respostas->>'data_nascimento', 'YYYY-MM-DD')
                ) = :dob
              )
        LIMIT 1
    """)

    with SessionLocal() as s:
        row = s.execute(sql, {"telefone": telefone, "dob": dob}).mappings().first()
        if not row:
            return None
    return get_by_pac_id(row["pac_id"])


def get_by_pac_id(pac_id: str) -> Optional[Dict[str, Any]]:
    """Busca paciente completo por pac_id (retorna dicionário pronto)."""
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


# -----------------------------------------------------------------------------
# UTILIDADE OPCIONAL DE DEBUG
# -----------------------------------------------------------------------------
def list_recent_patients(limit: int = 10):
    """Lista os últimos pacientes cadastrados (para debug)."""
    sql = text("""
        SELECT pac_id, name, phone_norm, dob, created_at
        FROM patients
        ORDER BY created_at DESC
        LIMIT :lim
    """)
    with SessionLocal() as s:
        rows = s.execute(sql, {"lim": limit}).mappings().all()
        return [dict(r) for r in rows]