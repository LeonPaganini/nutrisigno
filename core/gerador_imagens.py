"""Orquestrador de geração das páginas do resultado NutriSigno."""

from __future__ import annotations

import logging
from typing import Dict

from .imagem1_nutricional import gerar_card_nutricional
from .imagem2_comportamental import gerar_card_comportamental

logger = logging.getLogger(__name__)


def gerar_paginas_resultado(payload_nutricional: Dict, payload_comportamental: Dict) -> Dict[str, bytes]:
    """Gera as páginas de resultado e retorna um dicionário com bytes PNG."""

    paginas: Dict[str, bytes] = {}
    try:
        paginas["pagina1"] = gerar_card_nutricional(payload_nutricional)
    except Exception:
        logger.exception("Falha ao gerar a página nutricional.")
        return paginas

    try:
        paginas["pagina2"] = gerar_card_comportamental(payload_comportamental)
    except Exception:
        logger.exception("Falha ao gerar a página comportamental.")

    return paginas
