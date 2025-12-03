"""Renderização profissional estilo aquarela (placeholder)."""
from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw

LOGGER = logging.getLogger(__name__)


def render_watercolor_post(
    texto_imagem: str,
    texto_complementar: str,
    caminho_logo: str | Path,
    output_path: str | Path,
) -> str:
    """Gera imagem profissional em aquarela ou exibe aviso placeholder."""

    st.warning("Módulo profissional de renderização ainda não implementado.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Placeholder simples para manter o fluxo funcional
    image = Image.new("RGB", (1080, 1080), "#f5edff")
    draw = ImageDraw.Draw(image)
    draw.text((60, 60), "Render Watercolor Placeholder", fill="#7b5ba7")
    wrapped_text = (texto_imagem or "").strip() or "Sem texto da imagem"
    draw.multiline_text((60, 140), wrapped_text, fill="#4b1f70")
    if texto_complementar:
        draw.multiline_text((60, 260), texto_complementar, fill="#6f3f9c")
    image.save(output)

    LOGGER.info("Placeholder profissional salvo em %s", output)
    return str(output)
