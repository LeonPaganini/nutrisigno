"""Geração da Imagem 1 – Card Nutricional."""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont

from modules.results_context import PILLAR_NAMES

logger = logging.getLogger(__name__)

WIDTH = 1080
HEIGHT = 1920

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "nutrisigno_logo.PNG"

COLOR_BACKGROUND_TOP = "#2A1457"
COLOR_BACKGROUND_BOTTOM = "#512C8A"
COLOR_PRIMARY_GREEN = "#8BE39B"
COLOR_CARD_DARK = "#2F3142"
COLOR_CARD_BORDER = "#42465A"
COLOR_TEXT_PRIMARY = (255, 255, 255, 255)
COLOR_TEXT_MUTED = (230, 224, 248, 220)
COLOR_PANEL = (255, 255, 255, 30)
COLOR_PANEL_BORDER = (255, 255, 255, 60)

PADDING = 48
TOP_CARD_HEIGHT = 150
BOTTOM_CARD_HEIGHT = 320
BOTTOM_CARD_GAP = 24
RADAR_PADDING = 64
RADAR_TEXT_PADDING = 28

_FONT_CACHE: Dict[Tuple[int, str], ImageFont.FreeTypeFont] = {}


def _get_font(size: int, weight: str = "regular") -> ImageFont.ImageFont:
    key = (size, weight)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates: List[str]
    if weight == "bold":
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

    font: ImageFont.ImageFont | None = None
    for path in candidates:
        if os.path.exists(path):
            font = ImageFont.truetype(path, size=size)
            break
    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[key] = font  # type: ignore[assignment]
    return font


def _create_vertical_gradient(width: int, height: int, top: str, bottom: str) -> Image.Image:
    base = Image.new("RGB", (width, height), "white")
    top_r, top_g, top_b = ImageColor.getrgb(top)
    bottom_r, bottom_g, bottom_b = ImageColor.getrgb(bottom)
    gradient = Image.new("RGBA", (1, height))
    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(top_r + (bottom_r - top_r) * ratio)
        g = int(top_g + (bottom_g - top_g) * ratio)
        b = int(top_b + (bottom_b - top_b) * ratio)
        gradient.putpixel((0, y), (r, g, b, 170))
    gradient = gradient.resize((width, height))
    base_rgba = base.convert("RGBA")
    base_rgba.paste(gradient, (0, 0), gradient)
    return base_rgba


def _load_logo(max_width: int) -> Image.Image | None:
    try:
        if LOGO_PATH.exists():
            logo = Image.open(LOGO_PATH).convert("RGBA")
            ratio = max_width / logo.width
            new_size = (int(logo.width * ratio), int(logo.height * ratio))
            return logo.resize(new_size, resample=Image.Resampling.LANCZOS)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Falha ao carregar o logo do NutriSigno.")
    return None


def _draw_text_centered(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], text: str, font: ImageFont.ImageFont, fill: Tuple[int, int, int, int]) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x0, y0, x1, y1 = box
    pos = (x0 + (x1 - x0 - text_w) // 2, y0 + (y1 - y0 - text_h) // 2)
    draw.text(pos, text, font=font, fill=fill)


def _draw_top_cards(draw: ImageDraw.ImageDraw, start_y: int, width: int, payload: dict) -> int:
    section_width = width - (2 * PADDING)
    card_width = (section_width - (2 * BOTTOM_CARD_GAP)) // 3
    labels = ["IMC", "Score", "Hidratação"]
    values = [payload.get("imc", 0), payload.get("score", 0), payload.get("hidratacao", 0)]
    colors = [COLOR_PRIMARY_GREEN, "#F3DFA2", COLOR_PRIMARY_GREEN]
    title_font = _get_font(28, "bold")
    value_font = _get_font(44, "bold")

    y = start_y
    for idx, label in enumerate(labels):
        x = PADDING + idx * (card_width + BOTTOM_CARD_GAP)
        rect = (x, y, x + card_width, y + TOP_CARD_HEIGHT)
        draw.rounded_rectangle(rect, radius=26, fill=COLOR_PANEL, outline=COLOR_PANEL_BORDER, width=2)
        _draw_text_centered(
            draw,
            (rect[0], rect[1] + 16, rect[2], rect[1] + 16 + 36),
            label,
            title_font,
            COLOR_TEXT_MUTED,
        )
        _draw_text_centered(draw, (rect[0], rect[1] + 60, rect[2], rect[3]), f"{values[idx]}", value_font, ImageColor.getrgb(colors[idx]) + (255,))
    return y + TOP_CARD_HEIGHT + 32


def _normalize_scores(pilares: Dict[str, float | int | None]) -> List[float]:
    normalized: List[float] = []
    for name in PILLAR_NAMES:
        value = pilares.get(name) if pilares else None
        value_float = float(value or 0)
        normalized.append(max(0.0, min(value_float / 100.0, 1.0)))
    return normalized


def _draw_radar(draw: ImageDraw.ImageDraw, center: Tuple[int, int], radius: int, values: Sequence[float], labels: Iterable[str]) -> None:
    angles = [i * (360 / len(values)) for i in range(len(values))]
    points: List[Tuple[float, float]] = []
    for angle_deg, value in zip(angles, values):
        angle_rad = (angle_deg - 90) * 3.14159 / 180
        r = radius * value
        x = center[0] + r * float(__import__("math").cos(angle_rad))
        y = center[1] + r * float(__import__("math").sin(angle_rad))
        points.append((x, y))

    # grid
    for step in (0.25, 0.5, 0.75, 1.0):
        grid = []
        for angle_deg in angles:
            angle_rad = (angle_deg - 90) * 3.14159 / 180
            r = radius * step
            grid.append((center[0] + r * float(__import__("math").cos(angle_rad)), center[1] + r * float(__import__("math").sin(angle_rad))))
        draw.polygon(grid, outline=(255, 255, 255, 60))

    draw.polygon(points, fill=(139, 227, 155, 60), outline=ImageColor.getrgb(COLOR_PRIMARY_GREEN) + (200,))

    label_font = _get_font(22, "bold")
    for angle_deg, label in zip(angles, labels):
        angle_rad = (angle_deg - 90) * 3.14159 / 180
        x = center[0] + (radius + RADAR_TEXT_PADDING) * float(__import__("math").cos(angle_rad))
        y = center[1] + (radius + RADAR_TEXT_PADDING) * float(__import__("math").sin(angle_rad))
        bbox = draw.textbbox((0, 0), label, font=label_font)
        pos = (int(x - (bbox[2] - bbox[0]) / 2), int(y - (bbox[3] - bbox[1]) / 2))
        draw.text(pos, label, font=label_font, fill=COLOR_TEXT_MUTED)

    center_font = _get_font(28, "bold")
    center_bbox = draw.textbbox((0, 0), "Energia", font=center_font)
    draw.text(
        (center[0] - (center_bbox[2] - center_bbox[0]) / 2, center[1] - (center_bbox[3] - center_bbox[1]) / 2),
        "Energia",
        font=center_font,
        fill=COLOR_TEXT_PRIMARY,
    )


def _draw_bottom_cards(draw: ImageDraw.ImageDraw, start_y: int, width: int, payload: dict) -> None:
    section_width = width - (2 * PADDING)
    card_width = (section_width - BOTTOM_CARD_GAP) // 2
    titles = ["Comportamentos em Destaque", "Insight NutriSigno"]
    contents: List[Sequence[str] | str] = [
        payload.get("comportamentos") or [],
        payload.get("insight") or "Use seu signo como inspiração de hábitos saudáveis.",
    ]
    body_font = _get_font(26)
    title_font = _get_font(30, "bold")

    for idx, title in enumerate(titles):
        x = PADDING + idx * (card_width + BOTTOM_CARD_GAP)
        rect = (x, start_y, x + card_width, start_y + BOTTOM_CARD_HEIGHT)
        draw.rounded_rectangle(rect, radius=28, fill=COLOR_CARD_DARK, outline=COLOR_CARD_BORDER, width=2)
        draw.text((rect[0] + 24, rect[1] + 22), title, font=title_font, fill=COLOR_TEXT_PRIMARY)

        if idx == 0:
            bullets: Sequence[str] = [str(item) for item in contents[idx] if str(item).strip()] if isinstance(contents[idx], Iterable) else []
            y_cursor = rect[1] + 72
            for bullet in bullets:
                draw.text((rect[0] + 32, y_cursor), f"• {bullet}", font=body_font, fill=COLOR_TEXT_MUTED)
                y_cursor += 34
        else:
            insight_text = str(contents[idx])
            draw.multiline_text(
                (rect[0] + 24, rect[1] + 70),
                insight_text,
                font=body_font,
                fill=COLOR_TEXT_MUTED,
                spacing=8,
            )


def gerar_card_nutricional(payload_nutricional: dict) -> bytes:
    """Gera o card nutricional em memória e retorna bytes PNG."""

    canvas = _create_vertical_gradient(WIDTH, HEIGHT, COLOR_BACKGROUND_TOP, COLOR_BACKGROUND_BOTTOM)
    draw = ImageDraw.Draw(canvas)

    logo = _load_logo(220)
    if logo:
        canvas.paste(logo, (PADDING, PADDING), logo)

    header_font = _get_font(40, "bold")
    sub_font = _get_font(26)
    nome = str(payload_nutricional.get("nome") or "Paciente").strip() or "Paciente"
    idade = int(payload_nutricional.get("idade") or 0)
    signo = str(payload_nutricional.get("signo") or "Signo")
    header_y = PADDING + (logo.height + 12 if logo else 0)
    draw.text((PADDING, header_y), nome, font=header_font, fill=COLOR_TEXT_PRIMARY)
    draw.text((PADDING, header_y + 46), f"{idade} anos • {signo}", font=sub_font, fill=COLOR_TEXT_MUTED)

    next_y = header_y + 110
    next_y = _draw_top_cards(draw, next_y, WIDTH, payload_nutricional)

    pilares_scores = payload_nutricional.get("pilares_scores") or {}
    normalized = _normalize_scores(pilares_scores)
    radar_center = (WIDTH // 2, next_y + RADAR_PADDING + 240)
    _draw_radar(draw, radar_center, 220, normalized, [name.title() for name in PILLAR_NAMES])

    bottom_start = radar_center[1] + 220 + RADAR_PADDING
    _draw_bottom_cards(draw, bottom_start, WIDTH, payload_nutricional)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


if __name__ == "__main__":  # pragma: no cover
    exemplo = {
        "nome": "Joana",
        "idade": 29,
        "signo": "Sagitário",
        "imc": 23.4,
        "score": 86,
        "hidratacao": 78,
        "pilares_scores": {key: 80 for key in PILLAR_NAMES},
        "comportamentos": ["Planeja refeições", "Leva garrafinha", "Pratica yoga"],
        "insight": "Use seu signo como inspiração de hábitos saudáveis.",
    }
    img_bytes = gerar_card_nutricional(exemplo)
    Path("/tmp/card1.png").write_bytes(img_bytes)
