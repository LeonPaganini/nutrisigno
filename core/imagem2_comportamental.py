"""Geração da Imagem 2 – Perfil Comportamental com glassmorphism moderno."""

from __future__ import annotations

import io
import logging
import os
import random
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

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
COLOR_GOLD_PRIMARY = "#D4B86A"
COLOR_GOLD_SOFT = "#F0DCA2"
COLOR_TEXT_PRIMARY = (255, 255, 255, 245)
COLOR_TEXT_SECONDARY = (234, 226, 248, 210)
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


def _create_vertical_gradient() -> Image.Image:
    base = Image.new("RGB", (WIDTH, HEIGHT), "white")
    top_r, top_g, top_b = ImageColor.getrgb(COLOR_GRADIENT_TOP)
    bottom_r, bottom_g, bottom_b = ImageColor.getrgb(COLOR_GRADIENT_BOTTOM)
    gradient = Image.new("RGBA", (1, HEIGHT))
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        r = int(top_r + (bottom_r - top_r) * ratio)
        g = int(top_g + (bottom_g - top_g) * ratio)
        b = int(top_b + (bottom_b - top_b) * ratio)
        gradient.putpixel((0, y), (r, g, b, 170))
    gradient = gradient.resize((WIDTH, HEIGHT), resample=Image.Resampling.LANCZOS)
    base_rgba = base.convert("RGBA")
    base_rgba.paste(gradient, (0, 0), gradient)
    return base_rgba


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

    shadow = Image.new("RGBA", (width + 14, height + 14), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (7, 7, width + 7, height + 7), radius=radius + 6, fill=(0, 0, 0, 55)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
    base_img.alpha_composite(shadow, dest=(x0 - 7, y0 - 2))

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


def _tint_symbol(fallback_char: str, max_height: int) -> Image.Image:
    size = max_height
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _get_font(int(size * 0.6), "bold")
    bbox = draw.textbbox((0, 0), fallback_char, font=font)
    pos = ((size - (bbox[2] - bbox[0])) // 2, (size - (bbox[3] - bbox[1])) // 2)
    draw.text(pos, fallback_char, font=font, fill=(255, 255, 255, 210))
    tinted = ImageOps.colorize(canvas.convert("L"), black="#bda4ff", white="#f6f0ff").convert("RGBA")
    tinted.putalpha(int(255 * 0.26))
    return tinted.filter(ImageFilter.GaussianBlur(radius=3))


def _draw_constellation(draw: ImageDraw.ImageDraw) -> None:
    random.seed(42)
    points = []
    for _ in range(14):
        x = random.randint(MARGIN_OUTER, WIDTH - MARGIN_OUTER)
        y = random.randint(MARGIN_OUTER + 40, int(HEIGHT * 0.55))
        points.append((x, y))
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=COLOR_GOLD_PRIMARY + (160,))
    for i in range(len(points) - 1):
        draw.line((points[i], points[i + 1]), fill=COLOR_GOLD_SOFT + (160,), width=2)


def _draw_logo_with_glow(canvas: Image.Image, position: Tuple[int, int], max_width: int) -> int:
    x, y = position
    logo = None
    try:
        if LOGO_PATH.exists():
            logo = Image.open(LOGO_PATH).convert("RGBA")
            ratio = max_width / logo.width
            new_size = (int(logo.width * ratio), int(logo.height * ratio))
            logo = logo.resize(new_size, resample=Image.Resampling.LANCZOS)
    except Exception:
        logger.exception("Falha ao carregar logo para header comportamental.")

    if logo:
        glow = logo.copy()
        glow = glow.filter(ImageFilter.GaussianBlur(radius=14))
        glow.putalpha(90)
        canvas.alpha_composite(glow, dest=(x - 12, y - 8))
        canvas.paste(logo, (x, y), logo)
        return logo.width
    return 0


def draw_behavior_header(canvas: Image.Image, payload: dict) -> int:
    box = (MARGIN_OUTER, MARGIN_OUTER, WIDTH - MARGIN_OUTER, MARGIN_OUTER + 240)
    draw_glass_card(canvas, box, radius=36, blur_radius=24, fill_alpha=88)
    draw = ImageDraw.Draw(canvas)

    logo_width = _draw_logo_with_glow(canvas, (box[0] + CARD_PADDING, box[1] + 50), 200)
    text_x = box[0] + CARD_PADDING + logo_width + 26

    title_font = _get_font(46, "bold")
    subtitle_font = _get_font(26)

    nome = str(payload.get("nome") or "Paciente").strip() or "Paciente"
    idade = int(payload.get("idade") or 0)
    signo = str(payload.get("signo") or "Signo")
    elemento = str(payload.get("elemento") or "Elemento")
    regente = str(payload.get("regente") or "Regente")

    draw.text((text_x, box[1] + 52), nome, font=title_font, fill=COLOR_TEXT_PRIMARY)
    draw.text((text_x, box[1] + 110), f"{idade} anos", font=subtitle_font, fill=COLOR_TEXT_SECONDARY)
    draw.text((text_x, box[1] + 148), f"{signo} • {elemento} • {regente}", font=subtitle_font, fill=COLOR_TEXT_SECONDARY)

    return box[3] + GAP


def _draw_behavior_card(
    canvas: Image.Image, draw: ImageDraw.ImageDraw, rect: Tuple[int, int, int, int], title: str, bullets: Sequence[str]
) -> None:
    x0, y0, x1, y1 = rect
    draw_glass_card(canvas, rect, radius=CARD_RADIUS, blur_radius=22, fill_alpha=90, border_alpha=120)
    title_font = _get_font(32, "bold")
    body_font = _get_font(26)
    draw.text((x0 + CARD_PADDING, y0 + 22), title, font=title_font, fill=COLOR_TEXT_PRIMARY)
    y_cursor = y0 + 82
    for bullet in [b for b in bullets if str(b).strip()][:5]:
        draw.text((x0 + CARD_PADDING, y_cursor), f"• {bullet}", font=body_font, fill=COLOR_TEXT_SECONDARY)
        bbox = draw.textbbox((0, 0), f"• {bullet}", font=body_font)
        y_cursor += (bbox[3] - bbox[1]) + 12


def draw_behavior_grid(canvas: Image.Image, start_y: int, payload: dict) -> int:
    draw = ImageDraw.Draw(canvas)
    col_width = int((WIDTH - 2 * MARGIN_OUTER - GAP) / 2)
    row_height = 240
    cards_info = [
        ("Energia Comportamental", payload.get("energia") or []),
        ("Processamento Emocional", payload.get("emocional") or []),
        ("Tomada de Decisão", payload.get("decisao") or []),
        ("Rotina & Hábitos", payload.get("rotina") or []),
    ]

    for idx, (title, bullets) in enumerate(cards_info):
        row = idx // 2
        col = idx % 2
        x0 = MARGIN_OUTER + col * (col_width + GAP)
        y0 = start_y + row * (row_height + GAP)
        rect = (x0, y0, x0 + col_width, y0 + row_height)
        _draw_behavior_card(canvas, draw, rect, title, bullets)

    return start_y + 2 * (row_height + GAP)


def draw_behavior_highlights(canvas: Image.Image, start_y: int, payload: dict) -> int:
    draw = ImageDraw.Draw(canvas)
    rect = (MARGIN_OUTER, start_y, WIDTH - MARGIN_OUTER, start_y + 260)
    draw_glass_card(canvas, rect, radius=CARD_RADIUS, blur_radius=22, fill_alpha=88, border_alpha=130)

    title_font = _get_font(34, "bold")
    body_font = _get_font(26)
    signo = str(payload.get("signo") or "Signo")
    draw.text((rect[0] + CARD_PADDING, rect[1] + 28), f"Destaques Comportamentais de {signo}", font=title_font, fill=COLOR_TEXT_PRIMARY)
    y_cursor = rect[1] + 92
    for bullet in [b for b in payload.get("destaques", []) if str(b).strip()][:6]:
        draw.text((rect[0] + CARD_PADDING, y_cursor), f"• {bullet}", font=body_font, fill=COLOR_TEXT_SECONDARY)
        bbox = draw.textbbox((0, 0), f"• {bullet}", font=body_font)
        y_cursor += (bbox[3] - bbox[1]) + 10
    return rect[3] + GAP


def draw_footer(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    font = _get_font(22)
    text = "nutrisigno.com • perfil comportamental"
    bbox = draw.textbbox((0, 0), text, font=font)
    pos = ((WIDTH - (bbox[2] - bbox[0])) // 2, HEIGHT - 72)
    draw.text(pos, text, font=font, fill=COLOR_TEXT_SECONDARY)


def gerar_card_comportamental(payload_comportamental: dict) -> bytes:
    """Gera a imagem comportamental em memória."""

    canvas = _create_vertical_gradient()
    draw = ImageDraw.Draw(canvas)

    _draw_constellation(draw)

    symbol_char = (str(payload_comportamental.get("signo") or "✦")[0] or "✦").upper()
    symbol = _tint_symbol(symbol_char, int(HEIGHT * 0.36))
    symbol_pos = ((WIDTH - symbol.width) // 2, MARGIN_OUTER + 40)
    canvas.paste(symbol, symbol_pos, symbol)

    y_cursor = draw_behavior_header(canvas, payload_comportamental)
    y_cursor = draw_behavior_grid(canvas, y_cursor, payload_comportamental)
    y_cursor = draw_behavior_highlights(canvas, y_cursor, payload_comportamental)
    draw_footer(canvas)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


if __name__ == "__main__":  # pragma: no cover
    exemplo = {
        "nome": "Joana",
        "idade": 29,
        "signo": "Sagitário",
        "elemento": "Fogo",
        "regente": "Júpiter",
        "energia": ["Gosta de manhãs", "Treinos curtos"],
        "emocional": ["Escuta ativa", "Respiração profunda"],
        "decisao": ["Planeja a semana"],
        "rotina": ["Leva garrafa", "Prepara lanches"],
        "destaques": ["Consistente", "Busca autonomia", "Curiosa"],
    }
    Path("/tmp/card2.png").write_bytes(gerar_card_comportamental(exemplo))
