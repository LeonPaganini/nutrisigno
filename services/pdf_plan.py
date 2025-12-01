"""Gerador de PDF premium do Plano Alimentar NutriSigno.

Este módulo aplica o layout editorial descrito no briefing, com páginas
estruturadas e componentes reutilizáveis (cards, tabelas e gráficos).

Onde alterar tema
-----------------
• Paleta: constantes ``LILAS_PEROLADO`` etc. abaixo.
• Tipografia: constantes ``TITLE_FONT``, ``SERIF_FONT`` e ``SANS_FONT``.
• Tamanhos de texto: dicionário ``FONT_SIZES`` e espaçamentos baseados em ``GRID``.
"""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


logger = logging.getLogger(__name__)


# Paleta NutriSigno
LILAS_PEROLADO = colors.HexColor("#E8DAFF")
ROXO_ASTRAL = colors.HexColor("#2D1E4A")
DOURADO_MISTICO = colors.HexColor("#E4C58A")
OFFWHITE_PEROLADO = colors.HexColor("#FAF8F3")
CINZA_VIOLETA = colors.HexColor("#B9A8D9")

# Tipografia principal
TITLE_FONT = "Times-Bold"
SERIF_FONT = "Times-Roman"
SERIF_BOLD = "Times-Bold"
SANS_FONT = "Helvetica"
SANS_BOLD = "Helvetica-Bold"


def _px(px_value: float) -> float:
    """Converte pixels (96dpi) para pontos usados no PDF."""

    return px_value * 72 / 96


# Grid e proporções
GRID = _px(8)
MARGIN = _px(96)
SECTION_GAP = GRID * 3

FONT_SIZES = {
    "hero": 90,
    "page_title": 50,
    "section": 30,
    "card_title": 20,
    "body": 16,
    "small": 13,
}


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


def _draw_background(c: canvas.Canvas, width: float, height: float, seed: float = 0.0) -> None:
    """Desenha gradiente lilás perolado com círculos suaves e estrelas."""

    steps = 28
    for i in range(steps):
        factor = i / (steps - 1)
        color = colors.Color(
            LILAS_PEROLADO.red * (1 - factor) + OFFWHITE_PEROLADO.red * factor,
            LILAS_PEROLADO.green * (1 - factor) + OFFWHITE_PEROLADO.green * factor,
            LILAS_PEROLADO.blue * (1 - factor) + OFFWHITE_PEROLADO.blue * factor,
        )
        c.setFillColor(color)
        c.rect(0, height * (1 - factor) - height / steps, width, height / steps + 1, stroke=0, fill=1)

    c.setFillColor(colors.Color(ROXO_ASTRAL.red, ROXO_ASTRAL.green, ROXO_ASTRAL.blue, alpha=0.06))
    c.circle(width * 0.18, height * 0.82, _px(250), fill=1, stroke=0)
    c.circle(width * 0.82, height * 0.2, _px(220), fill=1, stroke=0)

    c.setFillColor(colors.Color(DOURADO_MISTICO.red, DOURADO_MISTICO.green, DOURADO_MISTICO.blue, alpha=0.55))
    for i in range(4):
        angle = seed + i * math.pi / 2.4
        x = width * (0.2 + 0.6 * (i % 2)) + math.cos(angle) * GRID * 2
        y = height * (0.75 - 0.4 * (i // 2)) + math.sin(angle) * GRID * 3
        c.circle(x, y, GRID * 0.7, stroke=0, fill=1)


def _draw_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    border_color: colors.Color | None = None,
    fill_color: colors.Color | None = None,
) -> None:
    border_color = border_color or colors.Color(DOURADO_MISTICO.red, DOURADO_MISTICO.green, DOURADO_MISTICO.blue, alpha=0.55)
    fill_color = fill_color or colors.Color(1, 1, 1, alpha=0.16)
    c.saveState()
    c.setFillColor(fill_color)
    c.setStrokeColor(border_color)
    c.setLineWidth(1)
    c.roundRect(x, y, width, height, GRID * 1.5, stroke=1, fill=1)
    c.restoreState()


def _draw_page_title(c: canvas.Canvas, title: str, x: float, y: float) -> float:
    c.setFillColor(ROXO_ASTRAL)
    c.setFont(TITLE_FONT, FONT_SIZES["page_title"])
    c.drawString(x, y, title)
    return y - FONT_SIZES["page_title"] - SECTION_GAP


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
            }
        )
    return meals


def _format_meal_items(items: Iterable[Any]) -> str:
    return "; ".join(str(item) for item in items if item)


def _logo_path() -> Optional[Path]:
    candidate = Path(__file__).resolve().parent.parent / "assets" / "nutrisigno_logo.PNG"
    return candidate if candidate.exists() else None


def _draw_cover(
    c: canvas.Canvas, width: float, height: float, paciente_info: Dict[str, Any], signo: str, pac_id: str
) -> None:
    _draw_background(c, width, height, seed=len(pac_id))
    logo = _logo_path()
    if logo:
        img = ImageReader(str(logo))
        logo_w = _px(220)
        logo_h = logo_w * 0.32
        c.drawImage(img, (width - logo_w) / 2, height - MARGIN, width=logo_w, height=logo_h, mask="auto")

    safe_x = MARGIN
    y = height - MARGIN - _px(120)

    c.setFillColor(ROXO_ASTRAL)
    c.setFont(TITLE_FONT, FONT_SIZES["hero"])
    c.drawCentredString(width / 2, y, paciente_info.get("nome") or paciente_info.get("nome_completo") or "Paciente")
    y -= FONT_SIZES["hero"] + GRID * 2

    c.setFont(SERIF_FONT, FONT_SIZES["section"])
    c.setFillColor(CINZA_VIOLETA)
    c.drawCentredString(width / 2, y, "Plano Alimentar · Edição Premium")
    y -= FONT_SIZES["section"] + SECTION_GAP

    card_height = _px(260)
    card_width = width - 2 * MARGIN
    card_x = safe_x
    card_y = y - card_height
    _draw_card(c, card_x, card_y, card_width, card_height)

    inner_x = card_x + GRID * 3
    inner_y = y - GRID * 2
    c.setFillColor(ROXO_ASTRAL)
    c.setFont(SANS_BOLD, FONT_SIZES["section"])
    c.drawString(inner_x, inner_y, f"Signo: {signo}")
    inner_y -= FONT_SIZES["section"] + GRID

    idade = paciente_info.get("idade") or paciente_info.get("age")
    objetivo = paciente_info.get("objetivo") or paciente_info.get("meta_principal") or "Bem-estar contínuo"
    lines = [f"Idade: {idade} anos" if idade else "Idade não informada", f"Objetivo principal: {objetivo}"]
    for line in lines:
        inner_y = _draw_paragraph(
            c,
            line,
            inner_x,
            inner_y,
            card_width / 2,
            SANS_FONT,
            FONT_SIZES["body"],
            FONT_SIZES["body"] + GRID * 0.4,
            ROXO_ASTRAL,
            max_lines=2,
        )
        inner_y -= GRID * 0.3

    c.setFillColor(colors.Color(DOURADO_MISTICO.red, DOURADO_MISTICO.green, DOURADO_MISTICO.blue, alpha=0.85))
    c.setFont(TITLE_FONT, FONT_SIZES["hero"])
    c.drawRightString(card_x + card_width - GRID * 2, card_y + card_height / 2, signo[:3].upper())

    c.setFont(SANS_FONT, FONT_SIZES["small"])
    c.setFillColor(ROXO_ASTRAL)
    c.drawCentredString(width / 2, MARGIN - GRID * 2, "Nutrição personalizada com estética astral premium")
    c.showPage()


def _draw_profile_page(
    c: canvas.Canvas, width: float, height: float, paciente_info: Dict[str, Any], plan_data: Dict[str, Any]
) -> None:
    _draw_background(c, width, height, seed=2.0)
    safe_x = MARGIN
    y = height - MARGIN
    y = _draw_page_title(c, "Perfil geral", safe_x, y)

    col_width = (width - 2 * MARGIN - GRID) / 2
    card_height = _px(150)
    metrics: List[Tuple[str, str, str]] = []

    bmi = _calc_bmi(paciente_info)
    metrics.append(("IMC", f"{bmi}" if bmi else "—", "Equilíbrio corporal e composição"))
    hydration = (plan_data.get("diet") or {}).get("hydration") or "Defina 35 ml/kg como ponto de partida"
    metrics.append(("Meta de hidratação", hydration, "Distribua ao longo do dia"))
    fiber = (plan_data.get("diet") or {}).get("fiber") or "Inclua fontes variadas de fibra em todas as refeições"
    metrics.append(("Fibras", fiber, "Bases vegetais e integrais"))
    objetivo = paciente_info.get("objetivo") or paciente_info.get("meta_principal") or "Bem-estar"
    metrics.append(("Objetivo principal", objetivo, "Foco diário"))

    card_y = y
    for idx, (title, value, detail) in enumerate(metrics):
        col = idx % 2
        if idx and col == 0:
            card_y -= card_height + GRID
        x = safe_x + col * (col_width + GRID)
        _draw_card(c, x, card_y - card_height, col_width, card_height)
        inner_x = x + GRID * 2
        inner_y = card_y - GRID * 1.5
        c.setFillColor(ROXO_ASTRAL)
        c.setFont(SANS_BOLD, FONT_SIZES["card_title"])
        c.drawString(inner_x, inner_y, title)
        inner_y -= FONT_SIZES["card_title"] + GRID * 0.6
        inner_y = _draw_paragraph(
            c,
            str(value),
            inner_x,
            inner_y,
            col_width - GRID * 4,
            SANS_FONT,
            FONT_SIZES["body"],
            FONT_SIZES["body"] + GRID * 0.4,
            ROXO_ASTRAL,
            max_lines=2,
        )
        inner_y -= GRID * 0.4
        _draw_paragraph(
            c,
            detail,
            inner_x,
            inner_y,
            col_width - GRID * 4,
            SANS_FONT,
            FONT_SIZES["small"],
            FONT_SIZES["small"] + GRID * 0.3,
            CINZA_VIOLETA,
            max_lines=2,
        )

    # Resumo astral
    block_y = card_y - card_height - SECTION_GAP
    block_height = _px(180)
    _draw_card(c, safe_x, block_y - block_height, width - 2 * MARGIN, block_height)
    inner_x = safe_x + GRID * 2
    inner_y = block_y - GRID * 1.5
    c.setFillColor(ROXO_ASTRAL)
    c.setFont(SANS_BOLD, FONT_SIZES["section"])
    c.drawString(inner_x, inner_y, "Resumo astral")
    inner_y -= FONT_SIZES["section"] + GRID
    signo = paciente_info.get("signo") or paciente_info.get("signo_nome") or "Signo"
    astro = paciente_info.get("resumo_astrologico") or (
        f"Inspirado em {signo}, priorize rituais de alimentação consciente e hidratação constante."
    )
    _draw_paragraph(
        c,
        astro,
        inner_x,
        inner_y,
        width - 2 * MARGIN - GRID * 4,
        SERIF_FONT,
        FONT_SIZES["body"],
        FONT_SIZES["body"] + GRID * 0.5,
        ROXO_ASTRAL,
        max_lines=5,
    )
    c.showPage()


def _ensure_space(
    c: canvas.Canvas,
    width: float,
    height: float,
    current_y: float,
    needed: float,
    seed: float,
    restart_section: Optional[str] = None,
) -> float:
    """Garante espaço útil; redesenha fundo e título ao quebrar a página."""

    if current_y - needed < MARGIN:
        c.showPage()
        _draw_background(c, width, height, seed=seed)
        if restart_section:
            title = restart_section
            start_y = height - MARGIN
            start_y = _draw_page_title(c, title, MARGIN, start_y)
            return start_y
        return height - MARGIN
    return current_y


def _draw_plan_page(c: canvas.Canvas, width: float, height: float, meals: List[Dict[str, Any]], total_kcal: Optional[Any]) -> None:
    title = "Plano alimentar"
    if total_kcal:
        title = f"Plano alimentar · {total_kcal} kcal"

    _draw_background(c, width, height, seed=3.3)
    safe_x = MARGIN
    y = height - MARGIN
    y = _draw_page_title(c, title, safe_x, y)

    col_width = (width - 2 * MARGIN - GRID) / 2
    card_min_height = _px(180)
    card_y = y
    for idx, meal in enumerate(meals):
        content = _format_meal_items(meal.get("items") or []) or "Detalhes da refeição não informados"
        lines = _wrap_text(content, col_width - GRID * 4, SANS_FONT, FONT_SIZES["body"])
        estimated_height = (
            GRID * 2
            + FONT_SIZES["card_title"]
            + (FONT_SIZES["body"] + GRID * 0.4) * min(len(lines), 6)
            + (FONT_SIZES["small"] + GRID * 0.3)
            + GRID * 4
        )
        card_height = max(card_min_height, estimated_height)

        col = idx % 2
        if idx and col == 0:
            card_y -= card_height + GRID
        card_y = _ensure_space(
            c,
            width,
            height,
            card_y,
            card_height,
            seed=3.5 + idx,
            restart_section=title,
        )
        x = safe_x + col * (col_width + GRID)

        _draw_card(c, x, card_y - card_height, col_width, card_height)
        inner_x = x + GRID * 2
        inner_y = card_y - GRID * 1.5
        c.setFillColor(ROXO_ASTRAL)
        c.setFont(SANS_BOLD, FONT_SIZES["card_title"])
        c.drawString(inner_x, inner_y, meal.get("title") or "Refeição")
        inner_y -= FONT_SIZES["card_title"] + GRID * 0.6
        kcal = meal.get("kcal")
        if kcal:
            c.setFont(SANS_FONT, FONT_SIZES["body"])
            c.setFillColor(CINZA_VIOLETA)
            c.drawString(inner_x, inner_y, f"{kcal} kcal")
            inner_y -= FONT_SIZES["body"] + GRID * 0.6
        inner_y = _draw_paragraph(
            c,
            content,
            inner_x,
            inner_y,
            col_width - GRID * 4,
            SANS_FONT,
            FONT_SIZES["body"],
            FONT_SIZES["body"] + GRID * 0.4,
            ROXO_ASTRAL,
            max_lines=6,
        )
        inner_y -= GRID * 0.5
        c.setFont(SANS_FONT, FONT_SIZES["small"])
        c.setFillColor(CINZA_VIOLETA)
        c.drawString(inner_x, inner_y, "Equilíbrio · Fibras · Proteínas magras")

    c.showPage()


def _draw_substitutions_page(c: canvas.Canvas, width: float, height: float, substitutions: Dict[str, Any]) -> None:
    title = "Substituições inteligentes"
    safe_x = MARGIN

    def _start_table_page(seed: float) -> Tuple[float, float, float, float, float]:
        _draw_background(c, width, height, seed=seed)
        y_top = height - MARGIN
        y_top = _draw_page_title(c, title, safe_x, y_top)
        table_h = height - 2 * MARGIN
        _draw_card(c, safe_x, MARGIN, width - 2 * MARGIN, table_h)

        inner_start_x = safe_x + GRID * 2
        header_y = y_top - GRID
        col_meal_local = (width - 2 * MARGIN) * 0.22
        col_food_local = (width - 2 * MARGIN) * 0.24
        col_equiv_local = (width - 2 * MARGIN) - col_meal_local - col_food_local - GRID * 2

        c.setFont(SANS_BOLD, FONT_SIZES["body"])
        c.setFillColor(DOURADO_MISTICO)
        c.drawString(inner_start_x, header_y, "Refeição")
        c.drawString(inner_start_x + col_meal_local + GRID, header_y, "Alimento")
        c.drawString(inner_start_x + col_meal_local + col_food_local + GRID * 2, header_y, "Equivalentes")

        return (
            inner_start_x,
            header_y - FONT_SIZES["body"] - GRID,
            col_meal_local,
            col_food_local,
            col_equiv_local,
        )

    inner_x, inner_y, col_meal, col_food, col_equiv = _start_table_page(seed=4.4)
    diet_subs = substitutions or {}

    if not diet_subs:
        c.setFont(SANS_FONT, FONT_SIZES["body"])
        c.setFillColor(ROXO_ASTRAL)
        c.drawString(inner_x, inner_y, "Nenhuma substituição informada.")
    else:
        for idx, (meal, options) in enumerate(list(diet_subs.items())):
            meal_lines = _wrap_text(str(meal), col_meal, SANS_BOLD, FONT_SIZES["small"])
            if isinstance(options, dict):
                items = [f"{k}: {v}" for k, v in options.items()]
            elif isinstance(options, Sequence) and not isinstance(options, str):
                items = [str(v) for v in options]
            else:
                items = [str(options)]
            first_item = items[0] if items else "—"
            original_lines = _wrap_text(first_item, col_food, SANS_FONT, FONT_SIZES["small"])
            equivalents = "; ".join(items[1:]) if len(items) > 1 else "Veja opções livres"
            equiv_lines = _wrap_text(equivalents, col_equiv, SANS_FONT, FONT_SIZES["small"])
            line_count = max(len(meal_lines), len(original_lines), len(equiv_lines), 1)
            row_height = line_count * (FONT_SIZES["small"] + GRID * 0.35) + GRID

            if inner_y - row_height < MARGIN + GRID * 2:
                inner_x, inner_y, col_meal, col_food, col_equiv = _start_table_page(seed=4.5 + idx * 0.1)

            _draw_card(c, safe_x + GRID, inner_y - row_height + GRID * 0.4, width - 2 * MARGIN - GRID * 2, row_height)

            c.setFont(SANS_BOLD, FONT_SIZES["small"])
            c.setFillColor(ROXO_ASTRAL)
            y_line = inner_y - GRID * 0.2
            for line in meal_lines or [str(meal)]:
                c.drawString(inner_x + GRID, y_line, line)
                y_line -= FONT_SIZES["small"] + GRID * 0.35

            y_line = inner_y - GRID * 0.2
            c.setFont(SANS_FONT, FONT_SIZES["small"])
            c.setFillColor(ROXO_ASTRAL)
            for line in original_lines or ["—"]:
                c.drawString(inner_x + col_meal + GRID * 2, y_line, line)
                y_line -= FONT_SIZES["small"] + GRID * 0.35

            y_line = inner_y - GRID * 0.2
            c.setFillColor(CINZA_VIOLETA)
            for line in equiv_lines or [equivalents]:
                c.drawString(inner_x + col_meal + col_food + GRID * 3, y_line, line)
                y_line -= FONT_SIZES["small"] + GRID * 0.35

            inner_y -= row_height + GRID * 0.5

    note_y = max(MARGIN + GRID * 1.5, inner_y - GRID)
    if note_y < MARGIN + FONT_SIZES["small"] + GRID:
        inner_x, inner_y, col_meal, col_food, col_equiv = _start_table_page(seed=5.1)
        note_y = MARGIN + GRID * 1.5

    c.setFont(SANS_FONT, FONT_SIZES["small"])
    c.setFillColor(CINZA_VIOLETA)
    c.drawString(inner_x, note_y, "Observação: use as equivalências para variar mantendo o valor nutricional.")
    c.showPage()


def _draw_radar(c: canvas.Canvas, center_x: float, center_y: float, radius: float, axes: List[Tuple[str, float]]) -> None:
    angle_step = 2 * math.pi / len(axes)
    c.setStrokeColor(colors.Color(ROXO_ASTRAL.red, ROXO_ASTRAL.green, ROXO_ASTRAL.blue, alpha=0.2))
    for scale in (0.35, 0.65, 1.0):
        c.circle(center_x, center_y, radius * scale, stroke=1, fill=0)

    c.setFillColor(colors.Color(LILAS_PEROLADO.red, LILAS_PEROLADO.green, LILAS_PEROLADO.blue, alpha=0.35))
    points: List[Tuple[float, float]] = []
    for idx, (_, value) in enumerate(axes):
        angle = -math.pi / 2 + idx * angle_step
        points.append((center_x + radius * value * math.cos(angle), center_y + radius * value * math.sin(angle)))
    if points:
        path = c.beginPath()
        path.moveTo(*points[0])
        for x, y in points[1:]:
            path.lineTo(x, y)
        path.close()
        c.drawPath(path, stroke=0, fill=1)

    c.setFillColor(DOURADO_MISTICO)
    for idx, (label, value) in enumerate(axes):
        angle = -math.pi / 2 + idx * angle_step
        point = (center_x + radius * value * math.cos(angle), center_y + radius * value * math.sin(angle))
        c.circle(*point, GRID * 0.7, stroke=0, fill=1)
        c.setFont(SANS_FONT, FONT_SIZES["small"])
        label_x = center_x + (radius + GRID * 2) * math.cos(angle)
        label_y = center_y + (radius + GRID * 2) * math.sin(angle)
        c.setFillColor(ROXO_ASTRAL)
        c.drawCentredString(label_x, label_y, label)


def _draw_graphs_page(
    c: canvas.Canvas,
    width: float,
    height: float,
    meals: List[Dict[str, Any]],
    hydration: Optional[str],
) -> None:
    _draw_background(c, width, height, seed=5.0)
    safe_x = MARGIN
    y = height - MARGIN
    y = _draw_page_title(c, "Visualizações", safe_x, y)

    content_width = width - 2 * MARGIN
    card_height = (height - 2 * MARGIN - GRID) / 2

    # Radar
    _draw_card(c, safe_x, y - card_height, content_width / 2 - GRID / 2, card_height)
    inner_x = safe_x + GRID * 2
    inner_y = y - GRID * 2
    c.setFont(SANS_BOLD, FONT_SIZES["card_title"])
    c.setFillColor(ROXO_ASTRAL)
    c.drawString(inner_x, inner_y, "Adequação nutricional")
    _draw_radar(
        c,
        inner_x + (content_width / 2 - GRID * 4) / 2,
        y - card_height / 2,
        _px(90),
        [
            ("Hidratação", 0.92 if hydration else 0.7),
            ("Fibras", 0.85 if hydration else 0.72),
            ("Variedade", min(1.0, max(0.65, len(meals) / 6))),
            ("Equilíbrio", 0.82),
        ],
    )

    # Distribuição calórica
    card2_x = safe_x + content_width / 2 + GRID / 2
    _draw_card(c, card2_x, y - card_height, content_width / 2 - GRID / 2, card_height)
    inner_x = card2_x + GRID * 2
    inner_y = y - GRID * 2
    c.setFont(SANS_BOLD, FONT_SIZES["card_title"])
    c.setFillColor(ROXO_ASTRAL)
    c.drawString(inner_x, inner_y, "Distribuição de calorias")
    inner_y -= FONT_SIZES["card_title"] + GRID
    total = sum(float(m.get("kcal") or 0) for m in meals) or 1
    bar_width = content_width / 2 - GRID * 6
    bar_height = GRID * 3.5
    for meal in meals[:5]:
        share = float(meal.get("kcal") or 0) / total
        share_width = bar_width * share
        c.setFillColor(colors.Color(ROXO_ASTRAL.red, ROXO_ASTRAL.green, ROXO_ASTRAL.blue, alpha=0.12))
        c.roundRect(inner_x, inner_y - bar_height + GRID * 0.6, bar_width, bar_height, GRID, stroke=0, fill=1)
        c.setFillColor(DOURADO_MISTICO)
        c.roundRect(inner_x, inner_y - bar_height + GRID * 0.6, share_width, bar_height, GRID, stroke=0, fill=1)
        c.setFont(SANS_FONT, FONT_SIZES["small"])
        c.setFillColor(ROXO_ASTRAL)
        c.drawString(inner_x, inner_y + GRID * 1.1, meal.get("title") or "Refeição")
        c.setFillColor(CINZA_VIOLETA)
        c.drawRightString(inner_x + bar_width, inner_y + GRID * 1.1, f"{int(share * 100)}%")
        inner_y -= bar_height + GRID * 2

    # Hidratação
    hydration_card_y = MARGIN
    _draw_card(c, safe_x, hydration_card_y, content_width, card_height - GRID)
    inner_x = safe_x + GRID * 2
    inner_y = hydration_card_y + card_height - GRID * 3
    c.setFont(SANS_BOLD, FONT_SIZES["card_title"])
    c.setFillColor(ROXO_ASTRAL)
    c.drawString(inner_x, inner_y, "Hidratação diária")
    inner_y -= FONT_SIZES["card_title"] + GRID
    hydration_text = hydration or "Defina uma meta individualizada e distribua ao longo do dia em blocos de 500 ml."
    _draw_paragraph(
        c,
        hydration_text,
        inner_x,
        inner_y,
        content_width - GRID * 4,
        SANS_FONT,
        FONT_SIZES["body"],
        FONT_SIZES["body"] + GRID * 0.4,
        ROXO_ASTRAL,
        max_lines=4,
    )
    c.showPage()


def _draw_conclusion_page(
    c: canvas.Canvas,
    width: float,
    height: float,
    paciente_info: Dict[str, Any],
    notes: List[str],
) -> None:
    _draw_background(c, width, height, seed=6.2)
    safe_x = MARGIN
    y = height - MARGIN
    y = _draw_page_title(c, "Conclusão & recomendações", safe_x, y)

    card_height = height - 2 * MARGIN
    _draw_card(c, safe_x, MARGIN, width - 2 * MARGIN, card_height)
    inner_x = safe_x + GRID * 2
    inner_y = y - GRID * 2
    c.setFont(SANS_BOLD, FONT_SIZES["section"])
    c.setFillColor(ROXO_ASTRAL)
    c.drawString(inner_x, inner_y, "Passos práticos")
    inner_y -= FONT_SIZES["section"] + GRID

    recommendations = notes or [
        "Mantenha intervalos regulares entre refeições para estabilidade energética.",
        "Priorize proteínas magras e fibras para saciedade prolongada.",
        "Use o plano como guia e ajuste as porções à sua rotina diária.",
    ]
    for rec in recommendations[:6]:
        inner_y = _draw_paragraph(
            c,
            f"• {rec}",
            inner_x,
            inner_y,
            width - 2 * MARGIN - GRID * 4,
            SERIF_FONT,
            FONT_SIZES["body"],
            FONT_SIZES["body"] + GRID * 0.4,
            ROXO_ASTRAL,
            max_lines=3,
        )
        inner_y -= GRID * 0.6

    c.setFont(SANS_BOLD, FONT_SIZES["small"])
    c.setFillColor(DOURADO_MISTICO)
    c.drawRightString(width - MARGIN, MARGIN - GRID * 0.6, "NutriSigno · Lifestyle astral equilibrado")
    c.showPage()


def gerar_pdf_plano(plan_data: Dict[str, Any], pac_id: str, paciente_info: Optional[Dict[str, Any]] = None) -> str:
    """Gera um PDF premium de seis páginas seguindo a hierarquia editorial."""

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
        logger.exception("Falha ao desenhar a página de gráficos; seguindo sem essa página.")
    _draw_conclusion_page(c, width, height, paciente_info, notes or [])

    c.save()
    return str(pdf_path)


__all__ = ["gerar_pdf_plano"]
