"""Geração da Imagem 2 – Perfil Comportamental em glassmorphism."""

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

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "nutrisigno_logo.PNG"

BACKGROUND_GRADIENT_TOP = "#3E2172"
BACKGROUND_GRADIENT_BOTTOM = "#150D30"
COLOR_GOLD_PRIMARY = "#D4B86A"
COLOR_GOLD_SOFT = "#F0DCA2"
COLOR_TEXT_PRIMARY = (255, 255, 255, 255)
COLOR_TEXT_SECONDARY = (232, 217, 255, 230)
COLOR_GLASS = (255, 255, 255, 70)
COLOR_GLASS_BORDER = (255, 255, 255, 90)

GLASS_RADIUS = 28
GLASS_BLUR_RADIUS = 10
CARD_PADDING = 28
GRID_GAP = 26
SECTION_GAP = 32

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
    base = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_GRADIENT_TOP)
    top_r, top_g, top_b = ImageColor.getrgb(BACKGROUND_GRADIENT_TOP)
    bottom_r, bottom_g, bottom_b = ImageColor.getrgb(BACKGROUND_GRADIENT_BOTTOM)
    gradient = Image.new("RGB", (1, HEIGHT))
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        r = int(top_r + (bottom_r - top_r) * ratio)
        g = int(top_g + (bottom_g - top_g) * ratio)
        b = int(top_b + (bottom_b - top_b) * ratio)
        gradient.putpixel((0, y), (r, g, b))
    gradient = gradient.resize((WIDTH, HEIGHT))
    base.paste(gradient)
    return base.convert("RGBA")


def _tint_symbol(fallback_char: str, max_height: int) -> Image.Image:
    size = max_height
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _get_font(int(size * 0.6), "bold")
    bbox = draw.textbbox((0, 0), fallback_char, font=font)
    pos = ((size - (bbox[2] - bbox[0])) // 2, (size - (bbox[3] - bbox[1])) // 2)
    draw.text(pos, fallback_char, font=font, fill=(255, 255, 255, 210))
    tinted = ImageOps.colorize(canvas.convert("L"), black="#bda4ff", white="#f6f0ff").convert("RGBA")
    tinted.putalpha(int(255 * 0.28))
    return tinted.filter(ImageFilter.GaussianBlur(radius=3))


def _draw_constellation(draw: ImageDraw.ImageDraw) -> None:
    random.seed(42)
    points = []
    for _ in range(14):
        x = random.randint(120, WIDTH - 120)
        y = random.randint(180, HEIGHT - 180)
        points.append((x, y))
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=COLOR_GOLD_PRIMARY)
    for i in range(len(points) - 1):
        draw.line((points[i], points[i + 1]), fill=COLOR_GOLD_SOFT, width=2)


def _draw_glass_panel(canvas: Image.Image, rect: Tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = rect
    glass_width = x1 - x0
    glass_height = y1 - y0
    glass = Image.new("RGBA", (glass_width, glass_height), (255, 255, 255, 0))
    glass_draw = ImageDraw.Draw(glass)
    glass_draw.rounded_rectangle((0, 0, glass_width, glass_height), radius=GLASS_RADIUS, fill=COLOR_GLASS, outline=COLOR_GLASS_BORDER, width=2)
    blurred = glass.filter(ImageFilter.GaussianBlur(radius=GLASS_BLUR_RADIUS))
    canvas.paste(blurred, (x0, y0), blurred)


def _draw_header(canvas: Image.Image, payload: dict) -> int:
    header_height = 180
    rect = (40, 40, WIDTH - 40, 40 + header_height)
    _draw_glass_panel(canvas, rect)
    draw = ImageDraw.Draw(canvas)

    try:
        if LOGO_PATH.exists():
            logo = Image.open(LOGO_PATH).convert("RGBA")
            ratio = 140 / logo.width
            logo = logo.resize((int(logo.width * ratio), int(logo.height * ratio)), resample=Image.Resampling.LANCZOS)
            canvas.paste(logo, (rect[0] + CARD_PADDING, rect[1] + 16), logo)
            text_x = rect[0] + CARD_PADDING + logo.width + 20
        else:
            text_x = rect[0] + CARD_PADDING
    except Exception:
        logger.exception("Falha ao carregar logo para header comportamental.")
        text_x = rect[0] + CARD_PADDING

    title_font = _get_font(40, "bold")
    subtitle_font = _get_font(24)
    nome = str(payload.get("nome") or "Paciente").strip() or "Paciente"
    idade = int(payload.get("idade") or 0)
    signo = str(payload.get("signo") or "Signo")
    elemento = str(payload.get("elemento") or "Elemento")
    regente = str(payload.get("regente") or "Regente")

    draw.text((text_x, rect[1] + 32), nome, font=title_font, fill=COLOR_TEXT_PRIMARY)
    draw.text((text_x, rect[1] + 78), f"{idade} anos", font=subtitle_font, fill=COLOR_TEXT_SECONDARY)
    draw.text((text_x, rect[1] + 112), f"{signo} • {elemento} • {regente}", font=subtitle_font, fill=COLOR_TEXT_SECONDARY)
    return rect[3] + 16


def _draw_behavior_card(draw: ImageDraw.ImageDraw, rect: Tuple[int, int, int, int], title: str, icon: str, bullets: Sequence[str]) -> None:
    x0, y0, x1, y1 = rect
    draw.rounded_rectangle(rect, radius=GLASS_RADIUS, fill=COLOR_GLASS, outline=COLOR_GLASS_BORDER, width=2)
    title_font = _get_font(30, "bold")
    body_font = _get_font(24)
    draw.text((x0 + CARD_PADDING, y0 + 18), f"{icon} {title}", font=title_font, fill=COLOR_TEXT_PRIMARY)
    y_cursor = y0 + 72
    for bullet in [b for b in bullets if str(b).strip()][:4]:
        draw.text((x0 + CARD_PADDING, y_cursor), f"• {bullet}", font=body_font, fill=COLOR_TEXT_SECONDARY)
        y_cursor += 34


def _draw_behavior_grid(canvas: Image.Image, start_y: int, payload: dict) -> int:
    draw = ImageDraw.Draw(canvas)
    grid_width = WIDTH - 80
    card_width = (grid_width - GRID_GAP) // 2
    card_height = 230
    x_start = 40

    cards_info = [
        ("Energia Comportamental", "⚡", payload.get("energia") or []),
        ("Processamento Emocional", "❤", payload.get("emocional") or []),
        ("Tomada de Decisão", "🎯", payload.get("decisao") or []),
        ("Rotina & Hábitos", "🗓", payload.get("rotina") or []),
    ]

    y = start_y
    for idx, (title, icon, bullets) in enumerate(cards_info):
        row = idx // 2
        col = idx % 2
        x0 = x_start + col * (card_width + GRID_GAP)
        y0 = y + row * (card_height + GRID_GAP)
        rect = (x0, y0, x0 + card_width, y0 + card_height)
        _draw_behavior_card(draw, rect, title, icon, bullets)
    return y + 2 * (card_height + GRID_GAP)


def _draw_highlights(canvas: Image.Image, start_y: int, payload: dict) -> int:
    draw = ImageDraw.Draw(canvas)
    rect = (40, start_y, WIDTH - 40, start_y + 260)
    _draw_glass_panel(canvas, rect)
    title_font = _get_font(32, "bold")
    body_font = _get_font(24)
    signo = str(payload.get("signo") or "Signo")
    draw.text((rect[0] + CARD_PADDING, rect[1] + 18), f"Destaques Comportamentais de {signo}", font=title_font, fill=COLOR_TEXT_PRIMARY)
    y_cursor = rect[1] + 72
    for bullet in [b for b in payload.get("destaques", []) if str(b).strip()][:6]:
        draw.text((rect[0] + CARD_PADDING, y_cursor), f"• {bullet}", font=body_font, fill=COLOR_TEXT_SECONDARY)
        y_cursor += 32
    return rect[3] + 12


def _draw_footer(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas)
    font = _get_font(22)
    text = "nutrisigno.com • perfil comportamental"
    bbox = draw.textbbox((0, 0), text, font=font)
    pos = ((WIDTH - (bbox[2] - bbox[0])) // 2, HEIGHT - 60)
    draw.text(pos, text, font=font, fill=COLOR_TEXT_SECONDARY)


def gerar_card_comportamental(payload_comportamental: dict) -> bytes:
    """Gera a imagem comportamental em memória."""

    canvas = _create_vertical_gradient()
    draw = ImageDraw.Draw(canvas)

    symbol_char = (str(payload_comportamental.get("signo") or "✦")[0] or "✦").upper()
    symbol = _tint_symbol(symbol_char, int(HEIGHT * 0.4))
    symbol_pos = ((WIDTH - symbol.width) // 2, 180)
    canvas.paste(symbol, symbol_pos, symbol)

    _draw_constellation(draw)

    y_cursor = _draw_header(canvas, payload_comportamental)
    y_cursor += SECTION_GAP
    y_cursor = _draw_behavior_grid(canvas, y_cursor, payload_comportamental)
    y_cursor += SECTION_GAP
    y_cursor = _draw_highlights(canvas, y_cursor, payload_comportamental)
    _draw_footer(canvas)

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
