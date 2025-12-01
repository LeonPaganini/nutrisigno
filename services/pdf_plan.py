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
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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

# Tipografia principal (usando nomes sugeridos; se não encontrados, Helvetica/Times são usados como fallback)
PRIMARY_SERIF = "CormorantGaramond-SemiBold"
PRIMARY_SERIF_BOLD = "CormorantGaramond-Bold"
PRIMARY_SANS = "Inter-Regular"
PRIMARY_SANS_BOLD = "Inter-SemiBold"


def _font_or_fallback(primary: str, fallback: str) -> str:
    """Garante que a fonte exista, caso contrário retorna fallback."""

    try:
        if primary in pdfmetrics.getRegisteredFontNames():
            return primary
    except Exception:
        pass
    return fallback


TITLE_FONT = _font_or_fallback(PRIMARY_SERIF_BOLD, "Times-Bold")
SERIF_FONT = _font_or_fallback(PRIMARY_SERIF, "Times-Roman")
SERIF_BOLD = TITLE_FONT
SANS_FONT = _font_or_fallback(PRIMARY_SANS, "Helvetica")
SANS_BOLD = _font_or_fallback(PRIMARY_SANS_BOLD, "Helvetica-Bold")

# Estilos centralizados
styles = getSampleStyleSheet()
TITLE = ParagraphStyle(
    "TITLE",
    parent=styles["Normal"],
    fontName=TITLE_FONT,
    fontSize=28,
    leading=32,
    textColor=ROXO_ASTRAL,
)

SECTION_TITLE = ParagraphStyle(
    "SECTION_TITLE",
    parent=styles["Normal"],
    fontName=_font_or_fallback(PRIMARY_SERIF_BOLD, "Times-Bold"),
    fontSize=18,
    leading=22,
    textColor=ROXO_ASTRAL,
    spaceAfter=8,
)

CARD_LABEL = ParagraphStyle(
    "CARD_LABEL",
    parent=styles["Normal"],
    fontName=SANS_BOLD,
    fontSize=11,
    leading=13,
    textColor=ROXO_ASTRAL,
)

BODY = ParagraphStyle(
    "BODY",
    parent=styles["Normal"],
    fontName=SANS_FONT,
    fontSize=10,
    leading=13,
    textColor=ROXO_ASTRAL,
)

SMALL_NOTE = ParagraphStyle(
    "SMALL_NOTE",
    parent=styles["Normal"],
    fontName=SANS_FONT,
    fontSize=9,
    leading=11,
    textColor=ROXO_ASTRAL,
)

COVER_NAME = ParagraphStyle(
    "COVER_NAME",
    parent=SECTION_TITLE,
    fontSize=24,
    leading=28,
)


def _px(px_value: float) -> float:
    """Converte pixels (96dpi) para pontos usados no PDF."""

    return px_value * 72 / 96


# Grid e proporções
GRID = _px(8)
PAGE_MARGIN = 48
BLOCK_SPACING = 24
CARD_PADDING = 12


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
    style: ParagraphStyle,
    max_lines: Optional[int] = None,
) -> float:
    """Renderiza texto simples usando um estilo centralizado."""

    c.setFont(style.fontName, style.fontSize)
    c.setFillColor(style.textColor)
    lines = _wrap_text(text, width, style.fontName, style.fontSize)
    if max_lines is not None:
        lines = lines[: max(0, max_lines)]
    for line in lines:
        c.drawString(x, y, line)
        y -= style.leading
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
    """Título de página com hierarquia premium."""

    c.setFillColor(TITLE.textColor)
    c.setFont(TITLE.fontName, TITLE.fontSize)
    c.drawString(x, y, title)
    return y - TITLE.leading - BLOCK_SPACING


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
        c.drawImage(img, (width - logo_w) / 2, height - PAGE_MARGIN - logo_h / 2, width=logo_w, height=logo_h, mask="auto")

    safe_x = PAGE_MARGIN
    y = height - PAGE_MARGIN - _px(80)

    # Título editorial
    c.setFont(TITLE.fontName, TITLE.fontSize)
    c.setFillColor(TITLE.textColor)
    c.drawCentredString(width / 2, y, "Plano Alimentar · Edição Premium")
    y -= TITLE.leading + BLOCK_SPACING

    # Nome do paciente
    c.setFont(COVER_NAME.fontName, COVER_NAME.fontSize)
    c.setFillColor(COVER_NAME.textColor)
    c.drawCentredString(
        width / 2, y, paciente_info.get("nome") or paciente_info.get("nome_completo") or "Paciente"
    )
    y -= COVER_NAME.leading + BLOCK_SPACING

    # Linha informativa com dados reais
    idade = paciente_info.get("idade") or paciente_info.get("age")
    objetivo = paciente_info.get("objetivo") or paciente_info.get("meta_principal") or "Bem-estar contínuo"
    info_line = f"Signo: {signo} | Idade: {idade or '—'} | Objetivo principal: {objetivo}"
    c.setFont(BODY.fontName, BODY.fontSize)
    c.setFillColor(BODY.textColor)
    c.drawCentredString(width / 2, y, info_line)
    y -= BODY.leading + BLOCK_SPACING

    # Selo discreto
    c.setFont(SMALL_NOTE.fontName, SMALL_NOTE.fontSize)
    c.setFillColor(CINZA_VIOLETA)
    c.drawCentredString(width / 2, PAGE_MARGIN, "Nutrição personalizada com estética astral premium")
    c.showPage()


def _draw_profile_page(
    c: canvas.Canvas, width: float, height: float, paciente_info: Dict[str, Any], plan_data: Dict[str, Any]
) -> None:
    _draw_background(c, width, height, seed=2.0)
    safe_x = PAGE_MARGIN
    y = height - PAGE_MARGIN
    y = _draw_page_title(c, "Perfil geral", safe_x, y)

    card_width = width - 2 * PAGE_MARGIN
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
    for title, value, detail in metrics:
        card_height = _px(120)
        _draw_card(c, safe_x, card_y - card_height, card_width, card_height)
        inner_x = safe_x + CARD_PADDING
        inner_y = card_y - CARD_PADDING
        c.setFont(CARD_LABEL.fontName, CARD_LABEL.fontSize)
        c.setFillColor(CARD_LABEL.textColor)
        c.drawString(inner_x, inner_y, title)
        inner_y -= CARD_LABEL.leading + GRID * 0.25
        inner_y = _draw_paragraph(c, str(value), inner_x, inner_y, card_width - CARD_PADDING * 2, BODY, max_lines=2)
        inner_y -= GRID * 0.2
        _draw_paragraph(c, detail, inner_x, inner_y, card_width - CARD_PADDING * 2, SMALL_NOTE, max_lines=2)
        card_y -= card_height + BLOCK_SPACING

    # Resumo astral
    block_height = _px(160)
    _draw_card(c, safe_x, card_y - block_height, card_width, block_height)
    inner_x = safe_x + CARD_PADDING
    inner_y = card_y - CARD_PADDING
    c.setFont(SECTION_TITLE.fontName, SECTION_TITLE.fontSize)
    c.setFillColor(SECTION_TITLE.textColor)
    c.drawString(inner_x, inner_y, "Resumo astral")
    inner_y -= SECTION_TITLE.leading
    signo = paciente_info.get("signo") or paciente_info.get("signo_nome") or "Signo"
    astro = paciente_info.get("resumo_astrologico") or (
        f"Inspirado em {signo}, priorize rituais de alimentação consciente e hidratação constante."
    )
    _draw_paragraph(c, astro, inner_x, inner_y, card_width - CARD_PADDING * 2, BODY, max_lines=5)
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

    if current_y - needed < PAGE_MARGIN:
        c.showPage()
        _draw_background(c, width, height, seed=seed)
        if restart_section:
            title = restart_section
            start_y = height - PAGE_MARGIN
            start_y = _draw_page_title(c, title, PAGE_MARGIN, start_y)
            return start_y
        return height - PAGE_MARGIN
    return current_y


def _draw_plan_page(c: canvas.Canvas, width: float, height: float, meals: List[Dict[str, Any]], total_kcal: Optional[Any]) -> None:
    title = "Plano alimentar"
    if total_kcal:
        title = f"Plano alimentar · {total_kcal} kcal"

    _draw_background(c, width, height, seed=3.3)
    safe_x = PAGE_MARGIN
    y = height - PAGE_MARGIN
    y = _draw_page_title(c, title, safe_x, y)

    card_width = width - 2 * PAGE_MARGIN
    for idx, meal in enumerate(meals or []):
        content = _format_meal_items(meal.get("items") or []) or "Detalhes da refeição não informados"
        content_lines = _wrap_text(content, card_width - CARD_PADDING * 2, BODY.fontName, BODY.fontSize)
        line_height = BODY.leading
        base_height = CARD_PADDING * 2 + CARD_LABEL.leading + BLOCK_SPACING / 2
        if meal.get("kcal"):
            base_height += BODY.leading + BLOCK_SPACING / 4
        card_height = base_height + line_height * min(len(content_lines), 10) + SMALL_NOTE.leading

        y = _ensure_space(c, width, height, y, card_height + BLOCK_SPACING, seed=3.5 + idx, restart_section=title)
        _draw_card(c, safe_x, y - card_height, card_width, card_height)
        inner_x = safe_x + CARD_PADDING
        inner_y = y - CARD_PADDING
        c.setFont(CARD_LABEL.fontName, CARD_LABEL.fontSize)
        c.setFillColor(CARD_LABEL.textColor)
        c.drawString(inner_x, inner_y, (meal.get("title") or "Refeição").upper())
        inner_y -= CARD_LABEL.leading + BLOCK_SPACING / 4
        kcal = meal.get("kcal")
        if kcal:
            c.setFont(SANS_BOLD, BODY.fontSize)
            c.setFillColor(BODY.textColor)
            c.drawString(inner_x, inner_y, f"{kcal} kcal")
            inner_y -= BODY.leading + BLOCK_SPACING / 4
        inner_y = _draw_paragraph(c, content, inner_x, inner_y, card_width - CARD_PADDING * 2, BODY, max_lines=10)
        inner_y -= BLOCK_SPACING / 4
        c.setFont(SMALL_NOTE.fontName, SMALL_NOTE.fontSize)
        c.setFillColor(CINZA_VIOLETA)
        c.drawString(inner_x, inner_y, "Equilíbrio · Fibras · Proteínas magras")
        y = y - card_height - BLOCK_SPACING

    if not meals:
        _draw_card(c, safe_x, y - _px(120), card_width, _px(120))
        inner_y = y - CARD_PADDING
        _draw_paragraph(
            c,
            "Plano não contém refeições cadastradas (mockup para testes de UI).",
            safe_x + CARD_PADDING,
            inner_y,
            card_width - CARD_PADDING * 2,
            SMALL_NOTE,
        )

    c.showPage()


def _draw_substitutions_page(c: canvas.Canvas, width: float, height: float, substitutions: Dict[str, Any]) -> None:
    title = "Substituições inteligentes"
    safe_x = PAGE_MARGIN

    def _start_table_page(seed: float) -> Tuple[float, float, float, float, float]:
        _draw_background(c, width, height, seed=seed)
        y_top = height - PAGE_MARGIN
        y_top = _draw_page_title(c, title, safe_x, y_top)
        table_h = height - 2 * PAGE_MARGIN
        _draw_card(c, safe_x, PAGE_MARGIN, width - 2 * PAGE_MARGIN, table_h)

        inner_start_x = safe_x + CARD_PADDING
        header_y = y_top - CARD_PADDING
        col_meal_local = (width - 2 * PAGE_MARGIN) * 0.2
        col_food_local = (width - 2 * PAGE_MARGIN) * 0.3
        col_equiv_local = (width - 2 * PAGE_MARGIN) - col_meal_local - col_food_local - CARD_PADDING

        c.setFont(CARD_LABEL.fontName, CARD_LABEL.fontSize)
        c.setFillColor(DOURADO_MISTICO)
        c.drawString(inner_start_x, header_y, "Refeição")
        c.drawString(inner_start_x + col_meal_local, header_y, "Alimento")
        c.drawString(inner_start_x + col_meal_local + col_food_local, header_y, "Equivalentes")

        return (
            inner_start_x,
            header_y - CARD_LABEL.leading - BLOCK_SPACING / 2,
            col_meal_local,
            col_food_local,
            col_equiv_local,
        )

    inner_x, inner_y, col_meal, col_food, col_equiv = _start_table_page(seed=4.4)
    diet_subs = substitutions or {}

    if not diet_subs:
        _draw_paragraph(
            c,
            "Nenhuma substituição informada (mockup para testes de UI).",
            inner_x,
            inner_y,
            width - 2 * PAGE_MARGIN - CARD_PADDING,
            SMALL_NOTE,
        )
    else:
        for idx, (meal, options) in enumerate(list(diet_subs.items())):
            if isinstance(options, dict):
                items = [f"{k}: {v}" for k, v in options.items()]
            elif isinstance(options, Sequence) and not isinstance(options, str):
                items = [str(v) for v in options]
            else:
                items = [str(options)]
            meal_lines = _wrap_text(str(meal), col_meal - CARD_PADDING, CARD_LABEL.fontName, CARD_LABEL.fontSize)
            original_lines = _wrap_text(items[0] if items else "—", col_food - CARD_PADDING, BODY.fontName, BODY.fontSize)
            equivalents = "; ".join(items[1:]) if len(items) > 1 else "Veja opções livres"
            equiv_lines = _wrap_text(equivalents, col_equiv - CARD_PADDING, BODY.fontName, BODY.fontSize)
            line_count = max(len(meal_lines), len(original_lines), len(equiv_lines), 1)
            row_height = line_count * BODY.leading + CARD_PADDING

            if inner_y - row_height < PAGE_MARGIN + BLOCK_SPACING:
                inner_x, inner_y, col_meal, col_food, col_equiv = _start_table_page(seed=4.5 + idx * 0.1)

            _draw_card(c, safe_x + CARD_PADDING / 2, inner_y - row_height, width - 2 * PAGE_MARGIN - CARD_PADDING, row_height)

            c.setFont(CARD_LABEL.fontName, CARD_LABEL.fontSize)
            c.setFillColor(CARD_LABEL.textColor)
            y_line = inner_y - CARD_PADDING / 2
            for line in meal_lines or [str(meal)]:
                c.drawString(inner_x, y_line, line)
                y_line -= BODY.leading

            y_line = inner_y - CARD_PADDING / 2
            c.setFont(BODY.fontName, BODY.fontSize)
            c.setFillColor(BODY.textColor)
            for line in original_lines or ["—"]:
                c.drawString(inner_x + col_meal, y_line, line)
                y_line -= BODY.leading

            y_line = inner_y - CARD_PADDING / 2
            c.setFillColor(CINZA_VIOLETA)
            for line in equiv_lines or [equivalents]:
                c.drawString(inner_x + col_meal + col_food, y_line, line)
                y_line -= BODY.leading

            inner_y -= row_height + BLOCK_SPACING / 2

    note_y = max(PAGE_MARGIN + BLOCK_SPACING, inner_y - BLOCK_SPACING)
    if note_y < PAGE_MARGIN + SMALL_NOTE.leading:
        inner_x, inner_y, col_meal, col_food, col_equiv = _start_table_page(seed=5.1)
        note_y = PAGE_MARGIN + BLOCK_SPACING

    _draw_paragraph(
        c,
        "Observação: use as equivalências para variar mantendo o valor nutricional.",
        inner_x,
        note_y,
        width - 2 * PAGE_MARGIN - CARD_PADDING,
        SMALL_NOTE,
    )
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
        c.setFont(SMALL_NOTE.fontName, SMALL_NOTE.fontSize)
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
    safe_x = PAGE_MARGIN
    y = height - PAGE_MARGIN
    y = _draw_page_title(c, "Visualizações", safe_x, y)

    content_width = width - 2 * PAGE_MARGIN

    # Adequação nutricional com interpretação
    radar_height = _px(220)
    _draw_card(c, safe_x, y - radar_height, content_width, radar_height)
    inner_x = safe_x + CARD_PADDING
    inner_y = y - CARD_PADDING
    c.setFont(CARD_LABEL.fontName, CARD_LABEL.fontSize)
    c.setFillColor(CARD_LABEL.textColor)
    c.drawString(inner_x, inner_y, "Adequação nutricional")
    _draw_radar(
        c,
        safe_x + content_width / 2,
        y - radar_height / 2,
        _px(80),
        [
            ("Hidratação", 0.92 if hydration else 0.7),
            ("Fibras", 0.85 if hydration else 0.72),
            ("Variedade", min(1.0, max(0.65, len(meals) / 6))),
            ("Equilíbrio", 0.82),
        ],
    )
    inner_y = y - radar_height + CARD_PADDING
    interpret_text = (
        "Sua adequação geral está em nível bom, com pontos fortes em variedade e distribuição de calorias. "
        "Pontos de atenção: hidratação e fibras, que ainda não atingem plenamente a meta diária."
    )
    _draw_paragraph(c, interpret_text, inner_x, inner_y, content_width - CARD_PADDING * 2, BODY, max_lines=3)
    y = y - radar_height - BLOCK_SPACING

    # Distribuição calórica
    bar_card_height = _px(220)
    _draw_card(c, safe_x, y - bar_card_height, content_width, bar_card_height)
    inner_x = safe_x + CARD_PADDING
    inner_y = y - CARD_PADDING
    c.setFont(CARD_LABEL.fontName, CARD_LABEL.fontSize)
    c.setFillColor(CARD_LABEL.textColor)
    c.drawString(inner_x, inner_y, "Distribuição de calorias")
    inner_y -= CARD_LABEL.leading + BLOCK_SPACING / 2
    total = sum(float(m.get("kcal") or 0) for m in meals) or 1
    bar_width = content_width - CARD_PADDING * 2
    bar_height = GRID * 3
    for meal in meals[:5]:
        share = float(meal.get("kcal") or 0) / total
        share_width = bar_width * share
        c.setFillColor(colors.Color(ROXO_ASTRAL.red, ROXO_ASTRAL.green, ROXO_ASTRAL.blue, alpha=0.12))
        c.roundRect(inner_x, inner_y - bar_height + GRID * 0.3, bar_width, bar_height, GRID, stroke=0, fill=1)
        c.setFillColor(DOURADO_MISTICO)
        c.roundRect(inner_x, inner_y - bar_height + GRID * 0.3, share_width, bar_height, GRID, stroke=0, fill=1)
        c.setFont(SMALL_NOTE.fontName, SMALL_NOTE.fontSize)
        c.setFillColor(ROXO_ASTRAL)
        c.drawString(inner_x, inner_y + GRID * 0.8, meal.get("title") or "Refeição")
        c.setFillColor(CINZA_VIOLETA)
        c.drawRightString(inner_x + bar_width, inner_y + GRID * 0.8, f"{int(share * 100)}%")
        inner_y -= bar_height + BLOCK_SPACING / 2
    y = y - bar_card_height - BLOCK_SPACING

    # Hidratação
    hydration_card_height = _px(180)
    _draw_card(c, safe_x, PAGE_MARGIN, content_width, hydration_card_height)
    inner_x = safe_x + CARD_PADDING
    inner_y = PAGE_MARGIN + hydration_card_height - CARD_PADDING
    c.setFont(CARD_LABEL.fontName, CARD_LABEL.fontSize)
    c.setFillColor(CARD_LABEL.textColor)
    c.drawString(inner_x, inner_y, "Hidratação diária")
    inner_y -= CARD_LABEL.leading + BLOCK_SPACING / 2
    hydration_text = hydration or "Defina uma meta individualizada e distribua ao longo do dia em blocos de 500 ml."
    _draw_paragraph(
        c,
        hydration_text,
        inner_x,
        inner_y,
        content_width - CARD_PADDING * 2,
        BODY,
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
    safe_x = PAGE_MARGIN
    y = height - PAGE_MARGIN
    y = _draw_page_title(c, "Conclusão & recomendações", safe_x, y)

    card_height = height - 2 * PAGE_MARGIN
    _draw_card(c, safe_x, PAGE_MARGIN, width - 2 * PAGE_MARGIN, card_height)
    inner_x = safe_x + CARD_PADDING
    inner_y = y - CARD_PADDING
    c.setFont(SECTION_TITLE.fontName, SECTION_TITLE.fontSize)
    c.setFillColor(SECTION_TITLE.textColor)
    c.drawString(inner_x, inner_y, "Resumo geral do plano")
    inner_y -= SECTION_TITLE.leading

    resumo_mock = (
        "(Texto mockup para testes de layout. Substituir futuramente pela saída real da IA.) "
        "Seu plano prioriza equilíbrio entre saciedade e variedade, mantendo o foco em hidratação, fibras e proteínas magras."
    )
    inner_y = _draw_paragraph(c, resumo_mock, inner_x, inner_y, width - 2 * PAGE_MARGIN - CARD_PADDING * 2, BODY, max_lines=5)
    inner_y -= BLOCK_SPACING

    c.setFont(SECTION_TITLE.fontName, SECTION_TITLE.fontSize)
    c.drawString(inner_x, inner_y, "Recomendações principais")
    inner_y -= SECTION_TITLE.leading
    recommendations = notes or [
        "Mantenha intervalos regulares entre refeições para estabilidade energética.",
        "Inclua verduras e frutas coloridas para ampliar a variedade de micronutrientes.",
        "Priorize proteínas magras em todas as refeições para preservar massa magra.",
        "Distribua a hidratação ao longo do dia em porções de 400–500 ml.",
        "Ajuste porções conforme sensação de saciedade e rotina de treinos.",
    ]
    for rec in recommendations[:5]:
        inner_y = _draw_paragraph(
            c,
            f"• {rec}",
            inner_x,
            inner_y,
            width - 2 * PAGE_MARGIN - CARD_PADDING * 2,
            BODY,
            max_lines=3,
        )
        inner_y -= BLOCK_SPACING / 4

    inner_y -= BLOCK_SPACING / 2
    c.setFont(SECTION_TITLE.fontName, SECTION_TITLE.fontSize)
    c.drawString(inner_x, inner_y, "Ajustes comportamentais sugeridos")
    inner_y -= SECTION_TITLE.leading
    behavior_text = (
        "Pratique refeições sem telas, mastigando lentamente; mantenha um ritual de preparo simples "
        "para reforçar consistência e prazer na alimentação."
    )
    inner_y = _draw_paragraph(c, behavior_text, inner_x, inner_y, width - 2 * PAGE_MARGIN - CARD_PADDING * 2, BODY, max_lines=4)

    inner_y -= BLOCK_SPACING
    encouragement = "Conte com o plano como um guia flexível: celebre pequenas vitórias diárias e ajuste o ritmo respeitando seu corpo."
    _draw_paragraph(c, encouragement, inner_x, inner_y, width - 2 * PAGE_MARGIN - CARD_PADDING * 2, BODY, max_lines=3)

    c.setFont(SMALL_NOTE.fontName, SMALL_NOTE.fontSize)
    c.setFillColor(DOURADO_MISTICO)
    c.drawRightString(width - PAGE_MARGIN, PAGE_MARGIN - GRID * 0.6, "NutriSigno · Lifestyle astral equilibrado")
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
