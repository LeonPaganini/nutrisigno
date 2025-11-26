"""Geração da Imagem 1 – Card Nutricional com glassmorphism moderno."""

from __future__ import annotations

import io
import logging
import math
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from modules.results_context import PILLAR_NAMES

logger = logging.getLogger(__name__)

WIDTH = 1080
HEIGHT = 1920
MARGIN_OUTER = 96
GAP = 48
CARD_RADIUS = 32
CARD_PADDING = 40

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "nutrisigno_logo.PNG"

COLOR_GRADIENT_TOP = "#9F88C9"
COLOR_GRADIENT_BOTTOM = "#5C488F"
COLOR_PRIMARY_GREEN = "#7CD8A1"
COLOR_GOLD = "#E7D084"
COLOR_CARD_DARK = "#252736"
COLOR_TEXT_LIGHT = (255, 255, 255, 240)
COLOR_TEXT_SUBTLE = (232, 228, 247, 210)
COLOR_TEXT_PURPLE = (159, 136, 201, 255)

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


def _create_vertical_gradient(width: int, height: int) -> Image.Image:
    base = Image.new("RGB", (width, height), "white")
    top_r, top_g, top_b = ImageColor.getrgb(COLOR_GRADIENT_TOP)
    bottom_r, bottom_g, bottom_b = ImageColor.getrgb(COLOR_GRADIENT_BOTTOM)
    gradient = Image.new("RGBA", (1, height))
    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(top_r + (bottom_r - top_r) * ratio)
        g = int(top_g + (bottom_g - top_g) * ratio)
        b = int(top_b + (bottom_b - top_b) * ratio)
        gradient.putpixel((0, y), (r, g, b, 170))
    gradient = gradient.resize((width, height), resample=Image.Resampling.LANCZOS)
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
    except Exception:  # pragma: no cover - defesa
        logger.exception("Falha ao carregar o logo do NutriSigno.")
    return None


def draw_text_left(
    draw: ImageDraw.ImageDraw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int, int],
    spacing: int = 6,
) -> int:
    x, y = position
    for line in text.split("\n"):
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + spacing
    return y


def draw_text_center(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int, int],
    spacing: int = 6,
) -> None:
    x0, y0, x1, y1 = box
    lines = text.split("\n")
    total_height = 0
    heights: List[int] = []
    widths: List[int] = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])
        widths.append(bbox[2] - bbox[0])
    for idx, h in enumerate(heights):
        total_height += h
        if idx < len(lines) - 1:
            total_height += spacing
    cursor_y = y0 + (y1 - y0 - total_height) // 2
    for line, w, h in zip(lines, widths, heights):
        cursor_x = x0 + (x1 - x0 - w) // 2
        draw.text((cursor_x, cursor_y), line, font=font, fill=fill)
        cursor_y += h + spacing


def draw_glass_card(
    base_img: Image.Image,
    box: Tuple[int, int, int, int],
    radius: int = CARD_RADIUS,
    blur_radius: int = 22,
    fill_alpha: int = 85,
    border_alpha: int = 110,
) -> None:
    x0, y0, x1, y1 = map(int, box)
    width, height = x1 - x0, y1 - y0

    cropped = base_img.crop((x0, y0, x1, y1))
    blurred = cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    shadow = Image.new("RGBA", (width + 12, height + 12), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (6, 6, width + 6, height + 6), radius=radius + 6, fill=(0, 0, 0, 60)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
    base_img.alpha_composite(shadow, dest=(x0 - 6, y0 - 2))

    glass = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    glass_draw = ImageDraw.Draw(glass)
    glass_draw.rounded_rectangle(
        (0, 0, width, height),
        radius=radius,
        fill=(255, 255, 255, fill_alpha),
        outline=(255, 255, 255, border_alpha),
        width=2,
    )

    blurred.paste(glass, (0, 0), glass)
    base_img.paste(blurred, (x0, y0))


def draw_header_nutricional(canvas: Image.Image, payload: dict) -> int:
    box = (MARGIN_OUTER, MARGIN_OUTER, WIDTH - MARGIN_OUTER, MARGIN_OUTER + 260)
    draw_glass_card(canvas, box, radius=36, blur_radius=24, fill_alpha=90)
    draw = ImageDraw.Draw(canvas)

    logo = _load_logo(210)
    text_x = box[0] + CARD_PADDING
    if logo:
        logo_y = box[1] + (260 - logo.height) // 2
        canvas.paste(logo, (box[0] + CARD_PADDING, logo_y), logo)
        text_x = box[0] + CARD_PADDING + logo.width + 28

    title_font = _get_font(46, "bold")
    subtitle_font = _get_font(28)

    nome = str(payload.get("nome") or "Paciente").strip() or "Paciente"
    idade = int(payload.get("idade") or 0)
    signo = str(payload.get("signo") or "Signo")

    draw.text((text_x, box[1] + 66), nome, font=title_font, fill=COLOR_TEXT_LIGHT)
    draw.text((text_x, box[1] + 126), f"{idade} anos", font=subtitle_font, fill=COLOR_TEXT_SUBTLE)
    draw.text((text_x, box[1] + 168), signo, font=subtitle_font, fill=COLOR_TEXT_SUBTLE)

    return box[3] + GAP


def draw_metrics(canvas: Image.Image, start_y: int, payload: dict) -> int:
    draw = ImageDraw.Draw(canvas)
    section_width = WIDTH - 2 * MARGIN_OUTER
    card_width = int((section_width - 2 * GAP) / 3)
    card_height = 152

    labels = ["IMC", "Score", "Hidratação"]
    values = [payload.get("imc", 0), payload.get("score", 0), payload.get("hidratacao", 0)]
    colors = ["#3CBF73", COLOR_GOLD, "#3CBF73"]

    title_font = _get_font(28, "bold")
    value_font = _get_font(42, "bold")

    for idx, (label, value, color) in enumerate(zip(labels, values, colors)):
        x0 = MARGIN_OUTER + idx * (card_width + GAP)
        y0 = start_y
        x1 = x0 + card_width
        y1 = y0 + card_height

        shadow = Image.new("RGBA", (card_width + 20, card_height + 20), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            (10, 10, card_width + 10, card_height + 10),
            radius=CARD_RADIUS + 6,
            fill=(0, 0, 0, 50),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
        canvas.alpha_composite(shadow, dest=(x0 - 10, y0 - 6))

        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=CARD_RADIUS,
            fill=(255, 255, 255, 255),
            outline=(255, 255, 255, 220),
            width=2,
        )

        draw.text((x0 + CARD_PADDING, y0 + 22), label, font=title_font, fill=COLOR_TEXT_PURPLE)
        value_str = f"{value}" if isinstance(value, int) else f"{value:.1f}" if isinstance(value, float) else str(value)
        draw.text((x0 + CARD_PADDING, y0 + 72), value_str, font=value_font, fill=ImageColor.getrgb(color) + (255,))

    return start_y + card_height + GAP


def _normalize_scores(pilares_scores: Dict[str, float]) -> List[float]:
    normalized: List[float] = []
    for key in PILLAR_NAMES:
        value = pilares_scores.get(key, 0)
        value_float = float(value or 0)
        normalized.append(max(0.0, min(value_float / 100.0, 1.0)))
    return normalized


def draw_radar(canvas: Image.Image, start_y: int, payload: dict) -> int:
    pilares_scores = payload.get("pilares_scores") or {}
    normalized = _normalize_scores(pilares_scores)

    radar_height = 620
    box = (MARGIN_OUTER, start_y, WIDTH - MARGIN_OUTER, start_y + radar_height)
    draw_glass_card(canvas, box, radius=36, blur_radius=24, fill_alpha=82)
    draw = ImageDraw.Draw(canvas)

    center = (WIDTH // 2, start_y + radar_height // 2 + 20)
    radius_polygon = 210
    radius_labels = radius_polygon + 32

    angles = [i * (360 / len(normalized)) for i in range(len(normalized))]
    points: List[Tuple[float, float]] = []
    for angle_deg, value in zip(angles, normalized):
        angle_rad = math.radians(angle_deg - 90)
        r = radius_polygon * value
        x = center[0] + r * math.cos(angle_rad)
        y = center[1] + r * math.sin(angle_rad)
        points.append((x, y))

    for step in (0.2, 0.4, 0.6, 0.8, 1.0):
        grid: List[Tuple[float, float]] = []
        for angle_deg in angles:
            angle_rad = math.radians(angle_deg - 90)
            r = radius_polygon * step
            grid.append((center[0] + r * math.cos(angle_rad), center[1] + r * math.sin(angle_rad)))
        draw.polygon(grid, outline=(255, 255, 255, 60))

    draw.polygon(points, fill=(124, 216, 161, 160), outline=ImageColor.getrgb(COLOR_PRIMARY_GREEN) + (220,))

    label_font = _get_font(26, "bold")
    for angle_deg, label in zip(angles, [name.title() for name in PILLAR_NAMES]):
        angle_rad = math.radians(angle_deg - 90)
        x = center[0] + radius_labels * math.cos(angle_rad)
        y = center[1] + radius_labels * math.sin(angle_rad)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        pos = (int(x - (bbox[2] - bbox[0]) / 2), int(y - (bbox[3] - bbox[1]) / 2))
        draw.text(pos, label, font=label_font, fill=COLOR_TEXT_SUBTLE)

    center_font = _get_font(32, "bold")
    center_box = (
        center[0] - 140,
        center[1] - 40,
        center[0] + 140,
        center[1] + 40,
    )
    draw_text_center(draw, center_box, "Energia", font=center_font, fill=COLOR_TEXT_LIGHT)

    return box[3] + GAP


def _render_bullets(draw: ImageDraw.ImageDraw, x: int, start_y: int, bullets: Sequence[str], font: ImageFont.ImageFont) -> None:
    y_cursor = start_y
    for bullet in [b for b in bullets if str(b).strip()]:
        draw.text((x, y_cursor), f"• {bullet}", font=font, fill=COLOR_TEXT_SUBTLE)
        bbox = draw.textbbox((0, 0), f"• {bullet}", font=font)
        y_cursor += (bbox[3] - bbox[1]) + 12


def draw_bottom_cards(canvas: Image.Image, start_y: int, payload: dict) -> int:
    draw = ImageDraw.Draw(canvas)
    section_width = WIDTH - 2 * MARGIN_OUTER
    card_width = int((section_width - GAP) / 2)
    card_height = 320

    titles = ["Comportamentos em Destaque", "Insight NutriSigno"]
    contents: List[Sequence[str] | str] = [
        payload.get("comportamentos") or [],
        payload.get("insight") or "Use seu signo como inspiração de hábitos saudáveis.",
    ]

    title_font = _get_font(32, "bold")
    body_font = _get_font(26)

    for idx, title in enumerate(titles):
        x0 = MARGIN_OUTER + idx * (card_width + GAP)
        y0 = start_y
        x1 = x0 + card_width
        y1 = y0 + card_height

        draw.rounded_rectangle((x0, y0, x1, y1), radius=CARD_RADIUS, fill=COLOR_CARD_DARK)
        draw_glass_card(
            canvas,
            (x0, y0, x1, y1),
            radius=CARD_RADIUS,
            blur_radius=18,
            fill_alpha=80,
            border_alpha=120,
        )

        draw.text((x0 + CARD_PADDING, y0 + 26), title, font=title_font, fill=COLOR_TEXT_LIGHT)

        if idx == 0:
            _render_bullets(draw, x0 + CARD_PADDING, y0 + 92, contents[idx], body_font)  # type: ignore[arg-type]
        else:
            insight_text = str(contents[idx])
            draw_text_left(draw, (x0 + CARD_PADDING, y0 + 92), insight_text, font=body_font, fill=COLOR_TEXT_SUBTLE, spacing=10)

    return start_y + card_height + GAP


def draw_footer(canvas: Image.Image, text: str) -> None:
    draw = ImageDraw.Draw(canvas)
    font = _get_font(22)
    bbox = draw.textbbox((0, 0), text, font=font)
    pos = ((WIDTH - (bbox[2] - bbox[0])) // 2, HEIGHT - 72)
    draw.text(pos, text, font=font, fill=COLOR_TEXT_SUBTLE)


def gerar_card_nutricional(payload_nutricional: dict) -> bytes:
    """Gera o card nutricional em memória e retorna bytes PNG."""

    canvas = _create_vertical_gradient(WIDTH, HEIGHT)

    y_cursor = draw_header_nutricional(canvas, payload_nutricional)
    y_cursor = draw_metrics(canvas, y_cursor, payload_nutricional)
    y_cursor += 120
    y_cursor = draw_radar(canvas, y_cursor, payload_nutricional)
    y_cursor = draw_bottom_cards(canvas, y_cursor, payload_nutricional)
    draw_footer(canvas, "nutrisigno.com • resultado público")

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
