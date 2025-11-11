"""Validation rules for the form."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from .normalization import canon_phone, canon_dob_to_br


def _is_float(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_form(data: Dict[str, Any]) -> List[str]:
    """Return a list of domain validation errors."""

    errors: List[str] = []

    telefone = canon_phone(data.get("telefone"))
    if not telefone:
        errors.append("Telefone é obrigatório e deve conter apenas números.")

    try:
        dob = canon_dob_to_br(data.get("data_nascimento"))
        if not dob:
            errors.append("Data de nascimento é obrigatória.")
        else:
            datetime.strptime(dob, "%d/%m/%Y")
    except ValueError:
        errors.append("Data de nascimento inválida. Use DD/MM/AAAA ou YYYY-MM-DD.")

    peso = data.get("peso")
    if peso not in (None, ""):
        if not _is_float(peso) or not 0.0 < float(peso) <= 500.0:
            errors.append("Peso deve estar entre 0 e 500 kg.")

    altura = data.get("altura")
    if altura not in (None, ""):
        if not _is_float(altura) or not 0.0 < float(altura) <= 300.0:
            errors.append("Altura deve estar entre 0 e 300 cm.")

    motivacao = data.get("motivacao")
    if motivacao not in (None, ""):
        if not _is_float(motivacao) or not 1 <= int(float(motivacao)) <= 5:
            errors.append("Motivação deve estar entre 1 e 5.")

    estresse = data.get("estresse")
    if estresse not in (None, ""):
        if not _is_float(estresse) or not 1 <= int(float(estresse)) <= 5:
            errors.append("Estresse deve estar entre 1 e 5.")

    consumo_agua = data.get("consumo_agua")
    if consumo_agua not in (None, ""):
        if not _is_float(consumo_agua) or not 0.0 <= float(consumo_agua) <= 15.0:
            errors.append("Consumo de água deve estar entre 0 e 15 litros.")

    return errors
