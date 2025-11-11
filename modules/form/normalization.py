"""Normalization utilities for the form."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from typing import Any

from .dto import FormDTO

_PHONE_RE = re.compile(r"\D+")
_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_BR_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def canon_phone(value: Any) -> str:
    """Return only digits of a phone number."""

    digits = re.sub(_PHONE_RE, "", str(value or ""))
    digits = digits.lstrip("0")
    return digits or ""


def canon_dob_to_br(value: Any) -> str:
    """Normalize multiple date formats to DD/MM/YYYY."""

    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""

    match = _BR_DATE_RE.match(text)
    if match:
        return "{}/{}/{}".format(match.group(1), match.group(2), match.group(3))

    iso = _ISO_DATE_RE.match(text)
    if iso:
        return "{}/{}/{}".format(iso.group(3), iso.group(2), iso.group(1))

    # Try to parse via datetime heuristics
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError(f"data_nascimento inválida: {text}")


def normalize_dto(dto: FormDTO) -> FormDTO:
    """Return a new FormDTO with canonical phone and date values."""

    telefone = canon_phone(dto.telefone)
    data_nascimento = canon_dob_to_br(dto.data_nascimento)
    extras = dto.extras.copy()
    if "data_nascimento" in extras:
        extras["data_nascimento"] = canon_dob_to_br(extras["data_nascimento"])
    if "telefone" in extras:
        extras["telefone"] = canon_phone(extras["telefone"])
    return replace(dto, telefone=telefone, data_nascimento=data_nascimento, extras=extras)


def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize specific fields inside a dict."""

    data = dict(data)
    if "telefone" in data:
        data["telefone"] = canon_phone(data["telefone"])
    if "data_nascimento" in data:
        data["data_nascimento"] = canon_dob_to_br(data["data_nascimento"])
    return data
