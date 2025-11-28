"""Stub/MVP de integração de pagamentos (Mercado Pago)."""
from __future__ import annotations

import logging
import uuid
from typing import Dict, Any

log = logging.getLogger(__name__)


def create_checkout(pac_id: str, valor: float) -> Dict[str, Any]:
    """Cria um checkout fictício para desenvolvimento local.

    Em produção, este método deve chamar o SDK/HTTP do Mercado Pago para
    gerar um preference_id e uma URL de checkout real.
    """

    preference_id = f"pref-{uuid.uuid4()}"
    checkout_url = f"https://pay.mercadopago.com/checkout/{preference_id}?pac_id={pac_id}"

    log.info(
        "Checkout mock gerado para %s com valor R$ %.2f (preference_id=%s)",
        pac_id,
        valor,
        preference_id,
    )

    return {
        "ok": True,
        "msg": "Checkout mock gerado (stub).",
        "checkout_url": checkout_url,
        "preference_id": preference_id,
        "valor": valor,
        "method": "Mercado Pago",
    }
