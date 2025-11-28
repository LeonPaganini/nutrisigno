"""Persistência de leads da calculadora de gordura corporal."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Float, Integer, Text, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, session_scope

log = logging.getLogger(__name__)

DEFAULT_ORIGEM = "calculadora_gordura_marinha"


@dataclass
class LeadPayload:
    """Dados mínimos capturados na calculadora de gordura corporal."""

    nome: str
    celular: str
    genero: str
    resultado_gordura: float
    altura_cm: Optional[float] = None
    cintura_cm: Optional[float] = None
    quadril_cm: Optional[float] = None
    abdomen_cm: Optional[float] = None
    pescoco_cm: Optional[float] = None
    origem: str = DEFAULT_ORIGEM


class CalculadoraLead(Base):
    """Modelo de leads provenientes da calculadora de % de gordura."""

    __tablename__ = "calculadora_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    celular: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    genero: Mapped[str] = mapped_column(Text, nullable=False)
    resultado_gordura: Mapped[float] = mapped_column(Float, nullable=False)
    altura_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    cintura_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    quadril_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    abdomen_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    pescoco_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    origem: Mapped[str] = mapped_column(Text, nullable=False, default=DEFAULT_ORIGEM)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


def _normalize_phone_digits(phone_raw: str) -> str:
    """Remove qualquer caractere que não seja dígito e limita a 20 caracteres."""

    digits = re.sub(r"\D", "", phone_raw or "").strip()
    return digits[:20]


def salvar_lead_calculadora(
    nome: str,
    celular: str,
    genero: str,
    resultado_gordura: float,
    dados_medidas: Optional[dict[str, Any]] = None,
    origem: str = DEFAULT_ORIGEM,
) -> int | None:
    """
    Salva no servidor os dados do lead gerados pela calculadora de % de gordura.

    Estruturei este ponto central para futuras integrações (ex.: Google Sheets).
    Basta adicionar a chamada de integração aqui sem alterar a UI.
    """

    payload = LeadPayload(
        nome=nome.strip(),
        celular=_normalize_phone_digits(celular),
        genero=genero,
        resultado_gordura=float(resultado_gordura),
        altura_cm=(dados_medidas or {}).get("altura_cm"),
        cintura_cm=(dados_medidas or {}).get("cintura_cm"),
        quadril_cm=(dados_medidas or {}).get("quadril_cm"),
        abdomen_cm=(dados_medidas or {}).get("abdomen_cm"),
        pescoco_cm=(dados_medidas or {}).get("pescoco_cm"),
        origem=origem,
    )

    try:
        with session_scope() as session:
            lead = CalculadoraLead(
                nome=payload.nome,
                celular=payload.celular,
                genero=payload.genero,
                resultado_gordura=payload.resultado_gordura,
                altura_cm=payload.altura_cm,
                cintura_cm=payload.cintura_cm,
                quadril_cm=payload.quadril_cm,
                abdomen_cm=payload.abdomen_cm,
                pescoco_cm=payload.pescoco_cm,
                origem=payload.origem,
            )
            session.add(lead)
            session.flush()
            lead_id = getattr(lead, "id", None)
    except Exception:  # pragma: no cover - apenas log
        log.exception("Falha ao salvar lead da calculadora")
        return None

    # Futuro: enviar payload também para Google Sheets / CRM (mantém ponto único).
    return lead_id
