"""Camada fina para operações de pagamento no banco."""
from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


def _load_repo_module():
    spec = importlib.util.find_spec("modules.repo")
    if not spec:
        log.warning("modules.repo não encontrado; funções de pagamento ficarão limitadas.")
        return None
    return importlib.import_module("modules.repo")


_repo = _load_repo_module()


def fetch_payment_by_pac_id(pac_id: str) -> Optional[Dict[str, Any]]:
    """Busca dados do paciente/pagamento via repo, se disponível."""
    if not _repo:
        return None

    try:
        data = _repo.get_by_pac_id(pac_id)
    except Exception as exc:  # pragma: no cover - defensivo
        log.exception("Falha ao buscar pagamento para %s: %s", pac_id, exc)
        return None

    if not data:
        return None

    return {
        "pac_id": data.get("pac_id"),
        "status_pagamento": data.get("status_pagamento") or "nao_encontrado",
        "metodo": "Mercado Pago",
        "valor": data.get("plano_alimentar", {}).get("valor")
        if isinstance(data.get("plano_alimentar"), dict)
        else None,
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "preference_id": data.get("preference_id"),
        "external_reference": data.get("external_reference"),
        "checkout_url": data.get("checkout_url"),
    }


def update_payment_status(pac_id: str, status: str) -> bool:
    """Atualiza o status_pagamento se o repo estiver disponível."""
    if not _repo:
        log.warning("Repo indisponível; não foi possível atualizar status para %s.", pac_id)
        return False

    try:
        return bool(_repo.update_payment_status(pac_id, status))
    except Exception as exc:  # pragma: no cover - defensivo
        log.exception("Erro ao atualizar status de pagamento: %s", exc)
        return False


def persist_checkout_metadata(pac_id: str, payload: Dict[str, Any]) -> None:
    """Persistência simples de metadados do checkout (se suportado)."""
    if not _repo:
        log.info("Repo indisponível; metadados de checkout apenas em memória/log.")
        return

    try:
        # O modelo atual não tem campos específicos; usamos update_payment_status para marcar pendente.
        status = payload.get("status_pagamento") or "pendente"
        _repo.update_payment_status(pac_id, status)
    except Exception as exc:  # pragma: no cover - defensivo
        log.exception("Falha ao persistir metadados de checkout: %s", exc)
