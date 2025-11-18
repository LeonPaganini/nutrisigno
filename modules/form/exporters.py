"""Utilities for exporting insights content."""

from __future__ import annotations

import io
from typing import Dict

from modules.share_image import gerar_imagem_share


def build_insights_pdf_bytes(insights: Dict[str, object]) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
    except Exception:
        return b"%PDF-1.4\n% fallback vazio"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 28 * cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "NutriSigno — Painel de Insights")
    y -= 1 * cm
    c.setFont("Helvetica", 10)
    for k, v in [
        ("IMC", f"{insights['bmi']} ({insights['bmi_category']})"),
        (
            "Hidratação",
            f"{insights['consumption']['water_liters']} / {insights['consumption']['recommended_liters']} L",
        ),
        ("Bristol", insights["bristol"]),
        ("Urina", insights["urine"]),
        ("Motivação/Estresse", f"{insights['motivacao']}/5 · {insights['estresse']}/5"),
        ("Insight do signo", insights["sign_hint"]),
    ]:
        c.drawString(2 * cm, y, f"{k}: {v}")
        y -= 0.8 * cm
        if y < 2 * cm:
            c.showPage()
            y = 28 * cm
    c.save()
    buf.seek(0)
    return buf.getvalue()


def build_share_png_bytes(share_data: Dict[str, object], formato: str = "story") -> bytes:
    """Proxy compatível para geração de PNGs compartilháveis."""

    return gerar_imagem_share(share_data, formato=formato)
