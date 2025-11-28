"""Geração de PDF moderno do plano nutricional usando ReportLab."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

PRIMARY = colors.HexColor("#6D28D9")
SECONDARY = colors.HexColor("#A855F7")
GOLD = colors.HexColor("#D4AF37")
TEXT_PRIMARY = colors.HexColor("#1F1F3D")
TEXT_MUTED = colors.HexColor("#4B5563")


def _draw_header(c: canvas.Canvas, width: float, height: float, titulo: str, subtitulo: str) -> float:
    c.setFillColor(PRIMARY)
    c.rect(0, height - 3 * cm, width, 3 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 1.2 * cm, titulo)
    c.setFont("Helvetica", 12)
    c.drawString(2 * cm, height - 2.0 * cm, subtitulo)
    return height - 3.4 * cm


def _section_title(c: canvas.Canvas, x: float, y: float, title: str) -> float:
    c.setFillColor(GOLD)
    c.rect(x, y - 0.35 * cm, 0.25 * cm, 1.1 * cm, fill=1, stroke=0)
    c.setFillColor(TEXT_PRIMARY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 0.5 * cm, y + 0.25 * cm, title)
    return y - 1.2 * cm


def _bullet_list(c: canvas.Canvas, x: float, y: float, items: list[str], size: int = 10, leading: float = 14) -> float:
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", size)
    for item in items:
        c.circle(x, y + 0.12 * cm, 0.08 * cm, fill=1, stroke=0)
        c.drawString(x + 0.35 * cm, y, item)
        y -= leading / 72 * 72 / 2.54 * 0.393701 * cm
    return y


def _format_macro_section(plan_data: Dict[str, Any]) -> list[str]:
    diet = plan_data.get("diet") or {}
    hydration = diet.get("hydration")
    fiber = diet.get("fiber")
    total_kcal = diet.get("total_kcal")
    macros = []
    if total_kcal:
        macros.append(f"Meta calórica diária: {total_kcal} kcal")
    if hydration:
        macros.append(str(hydration))
    if fiber:
        macros.append(str(fiber))
    return macros


def _format_meals(plan_data: Dict[str, Any]) -> list[str]:
    meals = []
    diet = plan_data.get("diet") or {}
    for meal in diet.get("meals", [])[:5]:
        title = meal.get("title") or "Refeição"
        kcal = meal.get("kcal")
        items = meal.get("items") or []
        line = f"{title}: {', '.join(map(str, items))}" if items else title
        if kcal:
            line += f" ({kcal} kcal)"
        meals.append(line)
    return meals


def _format_notes(plan_data: Dict[str, Any]) -> list[str]:
    notes = plan_data.get("notes") or []
    if isinstance(notes, (list, tuple)):
        return [str(n) for n in notes][:4]
    if isinstance(notes, str):
        return [notes]
    return []


def gerar_pdf_plano(plan_data: Dict[str, Any], pac_id: str, paciente_info: Optional[Dict[str, Any]] = None) -> str:
    """Gera um PDF vertical em A4 com o plano nutricional.

    Parameters
    ----------
    plan_data:
        Dicionário com o plano gerado (ex.: resultado de ``openai_utils.generate_plan``).
    pac_id:
        Identificador do paciente, utilizado no nome do arquivo.
    paciente_info:
        Dicionário opcional com dados do paciente (nome, signo, objetivo, etc.).
    """

    paciente_info = paciente_info or {}
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{pac_id}.pdf")
    pdf_path = Path(temp_file.name)
    temp_file.close()

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    y = _draw_header(
        c,
        width,
        height,
        "Plano NutriSigno – Plano Alimentar Personalizado",
        "Resumo visual e prático para o seu dia a dia",
    )

    nome = paciente_info.get("nome") or paciente_info.get("nome_completo") or "Paciente"
    signo = paciente_info.get("signo") or paciente_info.get("signo_nome") or "—"
    objetivo = paciente_info.get("objetivo") or paciente_info.get("meta_principal") or "Bem-estar"

    y = _section_title(c, 2 * cm, y, "Dados principais")
    y = _bullet_list(
        c,
        2.2 * cm,
        y,
        [f"Nome: {nome}", f"Signo: {signo}", f"Objetivo: {objetivo}"],
    )
    y -= 0.4 * cm

    macro_lines = _format_macro_section(plan_data)
    if macro_lines:
        y = _section_title(c, 2 * cm, y, "Resumo calórico e macros")
        y = _bullet_list(c, 2.2 * cm, y, macro_lines)
        y -= 0.3 * cm

    meal_lines = _format_meals(plan_data)
    if meal_lines:
        y = _section_title(c, 2 * cm, y, "Estrutura do dia")
        y = _bullet_list(c, 2.2 * cm, y, meal_lines)
        y -= 0.3 * cm

    notes = _format_notes(plan_data)
    if notes:
        y = _section_title(c, 2 * cm, y, "Observações")
        y = _bullet_list(c, 2.2 * cm, y, notes)

    c.setFillColor(SECONDARY)
    c.rect(0, 0, width, 1.2 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 1.5 * cm, 0.55 * cm, "NutriSigno · Plano em 1 página")

    c.showPage()
    c.save()

    return str(pdf_path)
