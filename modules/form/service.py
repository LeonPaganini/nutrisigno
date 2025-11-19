"""Service layer for form operations."""

from __future__ import annotations

import logging
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Dict, Optional
from uuid import UUID

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency
    np = None

from modules import repo
from modules.results_context import compute_pilares_scores

from .dto import FormDTO
from .mapper import dto_to_repo_payload
from .normalization import canon_dob_to_br, canon_phone, normalize_dto
from .validators import validate_form

log = logging.getLogger(__name__)


def sanitize_payload(value: Any) -> Any:
    """Convert unsupported JSON objects to safe primitives."""

    if isinstance(value, dict):
        return {k: sanitize_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_payload(v) for v in value]
    if isinstance(value, tuple):
        return [sanitize_payload(v) for v in value]
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if np is not None and isinstance(value, np.datetime64):
        return str(np.datetime_as_string(value))
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if np is not None and isinstance(value, (np.integer, np.int64)):
        return int(value)
    if np is not None and isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


class FormService:
    """Coordinates validation and persistence of form data."""

    def __init__(self, repository=repo):
        self._repo = repository

    def save_from_form(
        self,
        dto: FormDTO,
        *,
        pac_id: str | None = None,
        plano: Dict[str, Any] | None = None,
        plano_compacto: Dict[str, Any] | None = None,
        macros: Dict[str, Any] | None = None,
    ) -> tuple[str, Dict[str, Optional[int]]]:
        """Persist form data through the repository and retorna os pilares."""

        normalized = normalize_dto(dto)
        log.info(
            "form.normalize phone=%s dob=%s",
            normalized.telefone,
            normalized.data_nascimento,
        )
        form_dict = normalized.to_dict()
        errors = validate_form(form_dict)
        if errors:
            log.info("form.validate.fail count=%s", len(errors))
            raise ValueError("; ".join(errors))
        log.info("form.validate.ok")

        payload = dto_to_repo_payload(normalized)
        payload["respostas"] = sanitize_payload(payload["respostas"])
        payload["respostas"]["telefone"] = canon_phone(payload["respostas"].get("telefone"))
        payload["respostas"]["data_nascimento"] = canon_dob_to_br(
            payload["respostas"].get("data_nascimento")
        )
        payload["plano"] = sanitize_payload(plano or {})
        payload["plano_compacto"] = sanitize_payload(plano_compacto or {})
        payload["macros"] = sanitize_payload(macros or {})

        pilares_scores = compute_pilares_scores(payload["respostas"])
        payload["plano_compacto"]["pilares_scores"] = pilares_scores

        log.info("form.persist.start pac_id=%s", pac_id)
        pac_id_out = self._repo.upsert_patient_payload(
            pac_id=pac_id,
            respostas=payload["respostas"],
            plano=payload["plano"],
            plano_compacto=payload["plano_compacto"],
            macros=payload["macros"],
            name=payload.get("name"),
            email=payload.get("email"),
        )
        log.info("form.persist.ok pac_id=%s", pac_id_out)
        return pac_id_out, pilares_scores

    def read_by_phone_dob(self, phone: str, dob: str):
        """Return persisted data by phone and date of birth."""

        phone_norm = canon_phone(phone)
        dob_norm = canon_dob_to_br(dob)
        log.info("form.read phone=%s dob=%s", phone_norm, dob_norm)
        return self._repo.get_by_phone_dob(phone_norm, dob_norm)
