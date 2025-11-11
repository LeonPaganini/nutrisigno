"""Mapping utilities for the form."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .dto import FormDTO


def map_ui_to_dto(data: Dict[str, Any]) -> FormDTO:
    """Create a FormDTO from a UI dictionary."""

    known_fields = {
        "nome": data.get("nome", "").strip(),
        "email": data.get("email", "").strip(),
        "telefone": str(data.get("telefone", "")),
        "data_nascimento": str(data.get("data_nascimento", "")),
        "hora_nascimento": data.get("hora_nascimento"),
        "local_nascimento": data.get("local_nascimento"),
        "signo": data.get("signo"),
        "peso": _to_float_or_none(data.get("peso")),
        "altura": _to_float_or_none(data.get("altura")),
        "historico_saude": data.get("historico_saude"),
        "consumo_agua": _to_float_or_none(data.get("consumo_agua")),
        "nivel_atividade": data.get("nivel_atividade"),
        "tipo_fezes": data.get("tipo_fezes"),
        "cor_urina": data.get("cor_urina"),
        "motivacao": _to_int_or_none(data.get("motivacao")),
        "estresse": _to_int_or_none(data.get("estresse")),
        "habitos_alimentares": data.get("habitos_alimentares"),
        "energia_diaria": data.get("energia_diaria"),
        "impulsividade_alimentar": _to_int_or_none(data.get("impulsividade_alimentar")),
        "rotina_alimentar": _to_int_or_none(data.get("rotina_alimentar")),
        "observacoes": data.get("observacoes"),
    }
    extras = {k: v for k, v in data.items() if k not in known_fields}
    return FormDTO(**known_fields, extras=extras)


def dto_to_repo_payload(dto: FormDTO) -> Dict[str, Any]:
    """Prepare the payload expected by the repository layer."""

    respostas = dto.to_dict()
    respostas["telefone"] = str(respostas.get("telefone", ""))
    respostas["data_nascimento"] = str(respostas.get("data_nascimento", ""))
    payload = {
        "respostas": respostas,
        "name": dto.nome,
        "email": dto.email,
    }
    return payload


def _to_float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
