"""Geração de PDF premium do plano nutricional seguindo o padrão NutriSigno."""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


logger = logging.getLogger(__name__)


# Paleta NutriSigno
LILAC = colors.HexColor("#E8DAFF")
DEEP_PURPLE = colors.HexColor("#2D1E4A")
GOLD = colors.HexColor("#E4C58A")
OFF_WHITE = colors.HexColor("#FAF8F3")
SOFT_GRAY = colors.HexColor("#B9A8D9")
TEXT_PRIMARY = colors.HexColor("#1F1F3D")
TEXT_MUTED = colors.HexColor("#4B4A5E")


def _px(px_value: float) -> float:
    """Converte pixels (96dpi) para pontos usados no PDF."""

    return px_value * 72 / 96


MARGIN = _px(120)
SECTION_GAP = _px(80)
GRID = _px(8)

FONT_SIZES = {
    "hero": 84,
    "page_title": 48,
    "subtitle": 30,
    "section": 24,
    "body": 18,
    "small": 14,
    "label": 12,
}


def _blend(color_a: colors.Color, color_b: colors.Color, factor: float) -> colors.Color:
    factor = max(0.0, min(1.0, factor))
    r = color_a.red + (color_b.red - color_a.red) * factor
    g = color_a.green + (color_b.green - color_a.green) * factor
    b = color_a.blue + (color_b.blue - color_a.blue) * factor
    return colors.Color(r, g, b)


def _draw_background(c: canvas.Canvas, width: float, height: float, seed: float = 0.0) -> None:
    steps = 22
    for i in range(steps):
        factor = i / (steps - 1)
        color = _blend(LILAC, OFF_WHITE, factor)
        c.setFillColor(color)
        c.rect(0, height * (1 - factor) - height / steps, width, height / steps + 1, stroke=0, fill=1)

    c.setFillColor(colors.Color(DEEP_PURPLE.red, DEEP_PURPLE.green, DEEP_PURPLE.blue, alpha=0.06))
    c.circle(width * 0.82, height * 0.82, _px(260), fill=1, stroke=0)
    c.circle(width * 0.22, height * 0.18, _px(190), fill=1, stroke=0)

    star_points = [
        (0.18 + 0.04 * math.sin(seed + i), 0.82 - 0.03 * math.cos(seed + i * 1.3))
        for i in range(14)
    ]
    c.setFillColor(colors.Color(GOLD.red, GOLD.green, GOLD.blue, alpha=0.35))
    for x_factor, y_factor in star_points:
        c.circle(width * x_factor, height * y_factor, _px(2.4), fill=1, stroke=0)


def _draw_glass_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float = _px(18),
    border_color: colors.Color = colors.Color(1, 1, 1, alpha=0.25),
) -> None:
    c.saveState()
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.12))
    c.setStrokeColor(border_color)
    c.setLineWidth(1)
    c.roundRect(x, y, width, height, radius, stroke=1, fill=1)
    c.restoreState()


def _draw_section_header(c: canvas.Canvas, title: str, x: float, y: float) -> float:
    c.setFillColor(GOLD)
    c.rect(x, y - GRID, GRID / 2, GRID * 2.5, fill=1, stroke=0)
    c.setFillColor(TEXT_PRIMARY)
    c.setFont("Helvetica-Bold", FONT_SIZES["section"])
    c.drawString(x + GRID, y + GRID * 0.5, title)
    return y - GRID * 3


def _wrap_text(text: str, max_width: float, font: str, size: int) -> List[str]:
    if not text:
        return []
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if pdfmetrics.stringWidth(candidate, font, size) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_paragraph(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font: str,
    size: int,
    leading: float,
    color: colors.Color,
    max_lines: Optional[int] = None,
) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    lines = _wrap_text(text, width, font, size)
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def _format_meal_items(items: Iterable[Any]) -> str:
    return ", ".join(str(item) for item in items if item)[:160]


def _calc_bmi(paciente_info: Dict[str, Any]) -> Optional[float]:
    try:
        peso = float(paciente_info.get("peso") or paciente_info.get("peso_kg"))
        altura_raw = paciente_info.get("altura") or paciente_info.get("altura_m") or paciente_info.get("altura_cm")
        altura_m = float(altura_raw)
        if altura_m > 3:
            altura_m = altura_m / 100
        if altura_m <= 0:
            return None
        return round(peso / (altura_m**2), 1)
    except (TypeError, ValueError):
        return None


def _extract_meal_data(plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    meals: List[Dict[str, Any]] = []
    diet = plan_data.get("diet") or {}
    for meal in diet.get("meals", []) or []:
        meals.append(
            {
                "title": meal.get("title") or "Refeição",
                "kcal": meal.get("kcal"),
                "items": meal.get("items") or [],
                "quantity": meal.get("quantity"),
            }
        )
    return meals


def _draw_cover(
    c: canvas.Canvas, width: float, height: float, paciente_info: Dict[str, Any], signo: str, pac_id: str
) -> None:
    _draw_background(c, width, height, seed=len(pac_id))
    safe_x = MARGIN
    y = height - MARGIN

    c.setFont("Times-Bold", FONT_SIZES["hero"])
    c.setFillColor(DEEP_PURPLE)
    c.drawString(safe_x, y, "Plano Alimentar")
    y -= FONT_SIZES["hero"] + GRID * 2

    c.setFont("Times-Italic", FONT_SIZES["subtitle"])
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(safe_x, y, "NutriSigno · Edição Premium")
    y -= FONT_SIZES["subtitle"] + SECTION_GAP / 4

    card_height = _px(280)
    _draw_glass_card(c, safe_x, y - card_height, width - 2 * MARGIN, card_height)

    inner_x = safe_x + GRID * 3
    inner_y = y - GRID * 2
    c.setFont("Helvetica-Bold", FONT_SIZES["subtitle"])
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(inner_x, inner_y, paciente_info.get("nome") or paciente_info.get("nome_completo") or "Paciente")
    inner_y -= FONT_SIZES["subtitle"] + GRID

    c.setFont("Helvetica", FONT_SIZES["body"])
    idade = paciente_info.get("idade") or paciente_info.get("age")
    idade_text = f"{idade} anos" if idade else "Idade não informada"
    objetivo = paciente_info.get("objetivo") or paciente_info.get("meta_principal") or "Bem-estar"
    info_lines = [f"Signo: {signo}", idade_text, f"Objetivo principal: {objetivo}"]
    for line in info_lines:
        c.setFillColor(TEXT_MUTED)
        c.drawString(inner_x, inner_y, line)
        inner_y -= FONT_SIZES["body"] + GRID * 0.6

    c.setFillColor(colors.Color(GOLD.red, GOLD.green, GOLD.blue, alpha=0.85))
    c.setFont("Helvetica-Bold", FONT_SIZES["hero"])
    c.drawRightString(width - MARGIN - GRID * 2, y + card_height / 2, signo[:3].upper() or "AST")

    tagline = "Nutrição personalizada com estética astral premium"
    c.setFillColor(TEXT_PRIMARY)
    c.setFont("Helvetica", FONT_SIZES["body"])
    c.drawString(safe_x, MARGIN - GRID * 2, tagline)
    c.showPage()


def _draw_profile_page(
    c: canvas.Canvas,
    width: float,
    height: float,
    paciente_info: Dict[str, Any],
    plan_data: Dict[str, Any],
) -> None:
    _draw_background(c, width, height, seed=2.1)
    safe_x = MARGIN
    safe_y = height - MARGIN

    safe_y = _draw_section_header(c, "Perfil geral", safe_x, safe_y)

    col_width = (width - 2 * MARGIN - GRID) / 2
    card_height = _px(220)

    # Métricas principais
    card_y = safe_y - card_height
    _draw_glass_card(c, safe_x, card_y, col_width, card_height)
    inner_x = safe_x + GRID * 2
    inner_y = safe_y - GRID * 2
    bmi = _calc_bmi(paciente_info)
    bmi_text = f"IMC: {bmi}" if bmi else "IMC: —"
    _draw_paragraph(
        c,
        bmi_text,
        inner_x,
        inner_y,
        col_width - GRID * 3,
        "Helvetica-Bold",
        FONT_SIZES["subtitle"],
        FONT_SIZES["subtitle"] + GRID * 0.3,
        TEXT_PRIMARY,
    )
    inner_y -= FONT_SIZES["subtitle"] + GRID
    hydration = (plan_data.get("diet") or {}).get("hydration") or "Hidratação: personalize a meta diária"
    fiber = (plan_data.get("diet") or {}).get("fiber") or "Inclua fibras variadas em cada refeição"
    _draw_paragraph(
        c,
        hydration,
        inner_x,
        inner_y,
        col_width - GRID * 3,
        "Helvetica",
        FONT_SIZES["body"],
        FONT_SIZES["body"] + GRID * 0.3,
        TEXT_MUTED,
        max_lines=3,
    )
    inner_y -= FONT_SIZES["body"] * 3
    _draw_paragraph(
        c,
        fiber,
        inner_x,
        inner_y,
        col_width - GRID * 3,
        "Helvetica",
        FONT_SIZES["body"],
        FONT_SIZES["body"] + GRID * 0.3,
        TEXT_MUTED,
        max_lines=2,
    )

    # Astro + resumo
    card2_x = safe_x + col_width + GRID
    _draw_glass_card(c, card2_x, card_y, col_width, card_height)
    inner_y = safe_y - GRID * 2
    inner_x = card2_x + GRID * 2
    c.setFont("Helvetica-Bold", FONT_SIZES["subtitle"])
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(inner_x, inner_y, "Resumo astral")
    inner_y -= FONT_SIZES["subtitle"] + GRID
    signo = paciente_info.get("signo") or paciente_info.get("signo_nome") or "Signo"
    astro_hint = paciente_info.get("resumo_astrologico") or f"Inspirado em {signo}: favoreça rotina equilibrada e hidratação constante."
    inner_y = _draw_paragraph(
        c,
        astro_hint,
        inner_x,
        inner_y,
        col_width - GRID * 3,
        "Helvetica",
        FONT_SIZES["body"],
        FONT_SIZES["body"] + GRID * 0.5,
        TEXT_MUTED,
        max_lines=5,
    )

    c.showPage()


def _draw_plan_page(c: canvas.Canvas, width: float, height: float, meals: List[Dict[str, Any]], total_kcal: Optional[Any]) -> None:
    _draw_background(c, width, height, seed=3.3)
    safe_x = MARGIN
    y = height - MARGIN
    title = "Plano alimentar"
    if total_kcal:
        title = f"Plano alimentar · {total_kcal} kcal"
    y = _draw_section_header(c, title, safe_x, y)

    col_width = (width - 2 * MARGIN - GRID) / 2
    card_y = y
    for idx, meal in enumerate(meals):
        title = meal.get("title") or "Refeição"
        items = _format_meal_items(meal.get("items") or [])
        kcal = meal.get("kcal")
        card_height = _px(190)
        col = idx % 2
        if idx and col == 0:
            card_y -= card_height + GRID
        x = safe_x + col * (col_width + GRID)
        if card_y - card_height < MARGIN:
            c.showPage()
            _draw_background(c, width, height, seed=3.3 + idx)
            y = height - MARGIN
            y = _draw_section_header(c, "Plano alimentar (continuação)", safe_x, y)
            card_y = y
        _draw_glass_card(c, x, card_y - card_height, col_width, card_height)
        inner_x = x + GRID * 2
        inner_y = card_y - GRID * 2
        c.setFont("Helvetica-Bold", FONT_SIZES["subtitle"])
        c.setFillColor(TEXT_PRIMARY)
        c.drawString(inner_x, inner_y, title)
        inner_y -= FONT_SIZES["subtitle"] + GRID
        if kcal:
            c.setFont("Helvetica", FONT_SIZES["body"])
            c.setFillColor(TEXT_MUTED)
            c.drawString(inner_x, inner_y, f"{kcal} kcal")
            inner_y -= FONT_SIZES["body"] + GRID
        inner_y = _draw_paragraph(
            c,
            items or "Detalhes da refeição não informados",
            inner_x,
            inner_y,
            col_width - GRID * 3,
            "Helvetica",
            FONT_SIZES["body"],
            FONT_SIZES["body"] + GRID * 0.4,
            TEXT_MUTED,
            max_lines=5,
        )
    c.showPage()


def _draw_substitutions_page(c: canvas.Canvas, width: float, height: float, substitutions: Dict[str, Any]) -> None:
    _draw_background(c, width, height, seed=4.4)
    safe_x = MARGIN
    y = height - MARGIN
    y = _draw_section_header(c, "Substituições inteligentes", safe_x, y)

    card_height = height - 2 * MARGIN - GRID
    _draw_glass_card(c, safe_x, MARGIN, width - 2 * MARGIN, card_height)
    inner_x = safe_x + GRID * 2
    inner_y = y - GRID
    c.setFont("Helvetica-Bold", FONT_SIZES["body"])
    c.setFillColor(GOLD)
    c.drawString(inner_x, inner_y, "Refeição")
    c.drawString(inner_x + (width - 2 * MARGIN) * 0.28, inner_y, "Equivalências")
    inner_y -= FONT_SIZES["body"] + GRID

    diet_subs = substitutions or {}
    if not diet_subs:
        c.setFont("Helvetica", FONT_SIZES["body"])
        c.setFillColor(TEXT_MUTED)
        c.drawString(inner_x, inner_y, "Nenhuma substituição informada.")
    else:
        for meal, options in list(diet_subs.items())[:10]:
            c.setFont("Helvetica-Bold", FONT_SIZES["body"])
            c.setFillColor(TEXT_PRIMARY)
            c.drawString(inner_x, inner_y, str(meal))
            c.setFont("Helvetica", FONT_SIZES["small"])
            c.setFillColor(TEXT_MUTED)
            joined = "; ".join(str(o) for o in options)[:180]
            inner_y = _draw_paragraph(
                c,
                joined,
                inner_x + (width - 2 * MARGIN) * 0.28,
                inner_y,
                (width - 2 * MARGIN) * 0.68 - GRID * 3,
                "Helvetica",
                FONT_SIZES["small"],
                FONT_SIZES["small"] + GRID * 0.4,
                TEXT_MUTED,
                max_lines=3,
            )
            inner_y -= GRID

    c.showPage()


def _draw_graphs_page(
    c: canvas.Canvas,
    width: float,
    height: float,
    meals: List[Dict[str, Any]],
    hydration: Optional[str],
) -> None:
    _draw_background(c, width, height, seed=5.5)
    safe_x = MARGIN
    y = height - MARGIN
    y = _draw_section_header(c, "Visualizações", safe_x, y)

    content_width = width - 2 * MARGIN
    card_height = (height - 2 * MARGIN - GRID) / 2

    # Radar simples
    _draw_glass_card(c, safe_x, y - card_height, content_width / 2 - GRID / 2, card_height)
    inner_x = safe_x + GRID * 2
    inner_y = y - GRID * 2
    c.setFont("Helvetica-Bold", FONT_SIZES["body"])
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(inner_x, inner_y, "Adequação nutricional")
    center_x = inner_x + (content_width / 2 - GRID * 4) / 2
    center_y = y - card_height / 2
    radius = _px(90)
    axes = [
        ("Hidratação", 0.9 if hydration else 0.65),
        ("Fibras", 0.85 if hydration else 0.7),
        ("Variedade", min(1.0, max(0.6, len(meals) / 5))),
        ("Equilíbrio", 0.82),
    ]
    angle_step = 2 * math.pi / len(axes)
    c.setStrokeColor(colors.Color(DEEP_PURPLE.red, DEEP_PURPLE.green, DEEP_PURPLE.blue, alpha=0.25))
    for scale in (0.4, 0.7, 1.0):
        c.circle(center_x, center_y, radius * scale, stroke=1, fill=0)
    plotted: List[Tuple[str, Tuple[float, float], float]] = []
    c.setFillColor(colors.Color(GOLD.red, GOLD.green, GOLD.blue, alpha=0.3))
    for idx, (label, value) in enumerate(axes):
        angle = -math.pi / 2 + idx * angle_step
        point = (center_x + radius * value * math.cos(angle), center_y + radius * value * math.sin(angle))
        plotted.append((label, point, angle))
    polygon_points = [p for _, p, _ in plotted]
    if polygon_points:
        path = c.beginPath()
        first_x, first_y = polygon_points[0]
        path.moveTo(first_x, first_y)
        for x, y in polygon_points[1:]:
            path.lineTo(x, y)
        path.close()
        c.drawPath(path, stroke=0, fill=1)
    c.setFillColor(GOLD)
    for label, point, angle in plotted:
        c.circle(*point, GRID * 0.8, stroke=0, fill=1)
        c.setFont("Helvetica", FONT_SIZES["label"])
        c.setFillColor(TEXT_MUTED)
        label_x = center_x + (radius + GRID * 2) * math.cos(angle)
        label_y = center_y + (radius + GRID * 2) * math.sin(angle)
        c.drawCentredString(label_x, label_y, label)

    # Distribuição calórica
    card2_x = safe_x + content_width / 2 + GRID / 2
    _draw_glass_card(c, card2_x, y - card_height, content_width / 2 - GRID / 2, card_height)
    inner_x = card2_x + GRID * 2
    inner_y = y - GRID * 2
    c.setFont("Helvetica-Bold", FONT_SIZES["body"])
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(inner_x, inner_y, "Distribuição de calorias")
    inner_y -= FONT_SIZES["body"] + GRID
    total = sum(float(m.get("kcal") or 0) for m in meals) or 1
    bar_width = content_width / 2 - GRID * 6
    bar_height = GRID * 4
    for meal in meals[:5]:
        share = float(meal.get("kcal") or 0) / total
        share_width = bar_width * share
        c.setFillColor(colors.Color(DEEP_PURPLE.red, DEEP_PURPLE.green, DEEP_PURPLE.blue, alpha=0.18))
        c.roundRect(inner_x, inner_y - bar_height + GRID * 0.8, bar_width, bar_height, GRID, stroke=0, fill=1)
        c.setFillColor(colors.Color(GOLD.red, GOLD.green, GOLD.blue, alpha=0.65))
        c.roundRect(inner_x, inner_y - bar_height + GRID * 0.8, share_width, bar_height, GRID, stroke=0, fill=1)
        c.setFillColor(TEXT_PRIMARY)
        c.setFont("Helvetica", FONT_SIZES["small"])
        c.drawString(inner_x, inner_y + GRID * 1.2, meal.get("title") or "Refeição")
        c.setFillColor(TEXT_MUTED)
        c.drawRightString(inner_x + bar_width, inner_y + GRID * 1.2, f"{int(share * 100)}%")
        inner_y -= bar_height + GRID * 2

    # Hidratação
    hydration_card_y = MARGIN
    _draw_glass_card(c, safe_x, hydration_card_y, content_width, card_height - GRID)
    inner_x = safe_x + GRID * 2
    inner_y = hydration_card_y + card_height - GRID * 3
    c.setFont("Helvetica-Bold", FONT_SIZES["body"])
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(inner_x, inner_y, "Hidratação diária")
    inner_y -= FONT_SIZES["body"] + GRID
    c.setFont("Helvetica", FONT_SIZES["body"])
    c.setFillColor(TEXT_MUTED)
    hydration_text = hydration or "Defina uma meta de ingestão hídrica e distribua ao longo do dia."
    inner_y = _draw_paragraph(
        c,
        hydration_text,
        inner_x,
        inner_y,
        content_width - GRID * 4,
        "Helvetica",
        FONT_SIZES["body"],
        FONT_SIZES["body"] + GRID * 0.4,
        TEXT_MUTED,
        max_lines=3,
    )

    c.showPage()


def _draw_conclusion_page(
    c: canvas.Canvas,
    width: float,
    height: float,
    paciente_info: Dict[str, Any],
    notes: List[str],
) -> None:
    _draw_background(c, width, height, seed=6.6)
    safe_x = MARGIN
    y = height - MARGIN
    y = _draw_section_header(c, "Conclusão & recomendações", safe_x, y)

    card_height = height - 2 * MARGIN
    _draw_glass_card(c, safe_x, MARGIN, width - 2 * MARGIN, card_height)
    inner_x = safe_x + GRID * 2
    inner_y = y - GRID * 2
    c.setFont("Helvetica-Bold", FONT_SIZES["subtitle"])
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(inner_x, inner_y, "Passos práticos")
    inner_y -= FONT_SIZES["subtitle"] + GRID
    recommendations = notes or [
        "Mantenha intervalo regular entre refeições para estabilidade energética.",
        "Priorize proteínas magras e fibras para saciedade prolongada.",
        "Use o plano como guia, adaptando porções à sua rotina diária.",
    ]
    for rec in recommendations[:5]:
        inner_y = _draw_paragraph(
            c,
            f"• {rec}",
            inner_x,
            inner_y,
            width - 2 * MARGIN - GRID * 4,
            "Helvetica",
            FONT_SIZES["body"],
            FONT_SIZES["body"] + GRID * 0.4,
            TEXT_MUTED,
            max_lines=2,
        )
        inner_y -= GRID * 0.5

    c.setFont("Helvetica-Bold", FONT_SIZES["body"])
    c.setFillColor(GOLD)
    c.drawRightString(width - MARGIN, MARGIN - GRID * 0.5, "NutriSigno · Lifestyle astral equilibrado")
    c.showPage()


def gerar_pdf_plano(plan_data: Dict[str, Any], pac_id: str, paciente_info: Optional[Dict[str, Any]] = None) -> str:
    """Gera um PDF premium em múltiplas páginas com estética NutriSigno."""

    paciente_info = paciente_info or {}
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{pac_id}.pdf")
    pdf_path = Path(temp_file.name)
    temp_file.close()

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    signo = paciente_info.get("signo") or paciente_info.get("signo_nome") or "Signo"
    meals = _extract_meal_data(plan_data)
    total_kcal = (plan_data.get("diet") or {}).get("total_kcal")
    substitutions = (plan_data.get("diet") or {}).get("substitutions") or {}
    notes = plan_data.get("notes") if isinstance(plan_data.get("notes"), list) else []
    hydration = (plan_data.get("diet") or {}).get("hydration")

    _draw_cover(c, width, height, paciente_info, signo, pac_id)
    _draw_profile_page(c, width, height, paciente_info, plan_data)
    _draw_plan_page(c, width, height, meals, total_kcal)
    _draw_substitutions_page(c, width, height, substitutions)
    try:
        _draw_graphs_page(c, width, height, meals, hydration)
    except Exception:
        logger.exception(
            "Falha ao desenhar a página de gráficos no PDF, seguindo sem esta página."
        )
    _draw_conclusion_page(c, width, height, paciente_info, notes or [])

    c.save()

    return str(pdf_path)
