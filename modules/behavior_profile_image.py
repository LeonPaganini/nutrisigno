"""Geração da Imagem 2 – Perfil Comportamental do Signo.

O script cria um layout vertical em glassmorphism para complementar a
imagem principal do NutriSigno, destacando comportamentos do signo com
cards translúcidos, constelação dourada e símbolo em destaque.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps


WIDTH = 1080
HEIGHT = 1920

BACKGROUND_GRADIENT_TOP = "#3E2172"
BACKGROUND_GRADIENT_BOTTOM = "#150D30"
COLOR_GOLD_PRIMARY = "#D4B86A"
COLOR_GOLD_SOFT = "#F0DCA2"
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#E8D9FF"
COLOR_BULLET = "#8BE39B"

GLASS_FILL_RGBA = (255, 255, 255, 60)
GLASS_BORDER_RGBA = (255, 255, 255, 80)
GLASS_SHADOW_RGBA = (0, 0, 0, 100)

MARGIN = 40
HEADER_HEIGHT = 140
HEADER_RADIUS = 32
CARD_RADIUS = 30
CARD_GAP = 28
CARD_PADDING = 28
SECTION_GAP = 32
BOTTOM_CARD_RADIUS = 30
BOTTOM_CARD_PADDING_X = 32
BOTTOM_CARD_PADDING_Y = 28
FOOTER_MARGIN_BOTTOM = 32
FOOTER_HEIGHT = 24

ROOT_DIR = Path(__file__).resolve().parent
LOGO_PATH = ROOT_DIR / "assets" / "nutrisigno_logo.PNG"

_FONT_CACHE: Dict[Tuple[int, str], ImageFont.FreeTypeFont] = {}


def _get_font(size: int, weight: str = "regular") -> ImageFont.ImageFont:
    """Retorna uma fonte básica com cache para performance."""

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


def _create_vertical_gradient(width: int, height: int, top_color: str, bottom_color: str) -> Image.Image:
    """Cria um gradiente vertical simples."""

    base = Image.new("RGB", (width, height), top_color)
    top_r, top_g, top_b = ImageColor.getrgb(top_color)
    bottom_r, bottom_g, bottom_b = ImageColor.getrgb(bottom_color)
    gradient = Image.new("RGB", (1, height))
    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(top_r + (bottom_r - top_r) * ratio)
        g = int(top_g + (bottom_g - top_g) * ratio)
        b = int(top_b + (bottom_b - top_b) * ratio)
        gradient.putpixel((0, y), (r, g, b))
    gradient = gradient.resize((width, height))
    base.paste(gradient)
    return base.convert("RGBA")


def _tint_and_resize_symbol(symbol_path: Path, max_height: int) -> Image.Image:
    symbol = Image.open(symbol_path).convert("RGBA")
    ratio = max_height / symbol.height
    new_size = (int(symbol.width * ratio), max_height)
    resized = symbol.resize(new_size, resample=Image.Resampling.LANCZOS)
    luminance = resized.convert("L")
    colored = ImageOps.colorize(luminance, black="#c8b7ff", white="#f6f0ff")
    colored = colored.convert("RGBA")
    alpha = Image.new("L", colored.size, int(255 * 0.3))
    colored.putalpha(alpha)
    return colored.filter(ImageFilter.GaussianBlur(radius=2))


def _draw_constellation(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    points = [
        (int(width * 0.2), int(height * 0.18)),
        (int(width * 0.32), int(height * 0.26)),
        (int(width * 0.48), int(height * 0.2)),
        (int(width * 0.62), int(height * 0.28)),
        (int(width * 0.78), int(height * 0.22)),
        (int(width * 0.68), int(height * 0.36)),
        (int(width * 0.52), int(height * 0.34)),
    ]
    for start, end in zip(points, points[1:]):
        draw.line([start, end], fill=COLOR_GOLD_PRIMARY, width=2)
    for x, y in points:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=COLOR_GOLD_PRIMARY + "99")


def draw_big_symbol_and_constellation(base_img: Image.Image, symbol_path: Path) -> Image.Image:
    canvas = base_img.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    symbol_img = _tint_and_resize_symbol(symbol_path, int(HEIGHT * 0.4))
    sym_x = (WIDTH - symbol_img.width) // 2
    sym_y = int(HEIGHT * 0.08)
    canvas.alpha_composite(symbol_img, (sym_x, sym_y))
    _draw_constellation(draw, WIDTH, HEIGHT)
    return canvas


def draw_glass_card(
    target_img: Image.Image,
    bbox: Tuple[int, int, int, int],
    radius: int,
    blur_radius: int = 10,
    fill_rgba: Tuple[int, int, int, int] = GLASS_FILL_RGBA,
    border_rgba: Tuple[int, int, int, int] = GLASS_BORDER_RGBA,
    background_reference: Image.Image | None = None,
) -> None:
    """Aplica efeito de vidro em uma região específica."""

    source = background_reference if background_reference is not None else target_img
    x0, y0, x1, y1 = bbox
    shadow = Image.new("RGBA", target_img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (x0 + 2, y0 + 4, x1 + 2, y1 + 4), radius=radius, fill=GLASS_SHADOW_RGBA
    )

    glass_layer = Image.new("RGBA", target_img.size, (0, 0, 0, 0))
    region = source.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(blur_radius))
    glass_layer.paste(region, (x0, y0))
    glass_draw = ImageDraw.Draw(glass_layer)
    glass_draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=fill_rgba)
    glass_draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, outline=border_rgba, width=2)

    target_img.alpha_composite(shadow)
    target_img.alpha_composite(glass_layer)


def _draw_bullets(
    draw: ImageDraw.ImageDraw,
    start_xy: Tuple[int, int],
    lines: Iterable[str],
    font: ImageFont.ImageFont,
    color: str,
    line_spacing: int = 10,
) -> None:
    bullet_radius = 5
    x, y = start_xy
    for line in lines:
        draw.ellipse((x, y + 6 - bullet_radius, x + 2 * bullet_radius, y + 6 + bullet_radius), fill=COLOR_BULLET)
        draw.text((x + 2 * bullet_radius + 10, y), line, font=font, fill=color)
        y += font.getbbox(line)[3] - font.getbbox(line)[1] + line_spacing


def draw_behavior_card(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[int, int, int, int],
    titulo: str,
    icone: str,
    linhas_texto: Sequence[str],
    fontes: Dict[str, ImageFont.ImageFont],
) -> None:
    x0, y0, x1, y1 = bbox
    padding = CARD_PADDING
    icon_font = fontes["icon"]
    title_font = fontes["title"]
    body_font = fontes["body"]

    icon_y = y0 + padding
    draw.text((x0 + padding, icon_y), icone, font=icon_font, fill=COLOR_GOLD_PRIMARY)

    title_y = icon_y + icon_font.getbbox(icone)[3] - icon_font.getbbox(icone)[1] + 4
    draw.text((x0 + padding, title_y), titulo, font=title_font, fill=COLOR_TEXT_PRIMARY)

    content_y = title_y + title_font.getbbox(titulo)[3] - title_font.getbbox(titulo)[1] + 12
    _draw_bullets(draw, (x0 + padding, content_y), linhas_texto, body_font, COLOR_TEXT_SECONDARY, line_spacing=12)


def draw_header(
    base_img: Image.Image,
    background_reference: Image.Image,
    nome: str,
    idade: int,
    signo: str,
    elemento: str,
    regente: str,
    fontes: Dict[str, ImageFont.ImageFont],
) -> int:
    header_bbox = (MARGIN, MARGIN, WIDTH - MARGIN, MARGIN + HEADER_HEIGHT)
    draw_glass_card(base_img, header_bbox, radius=HEADER_RADIUS, blur_radius=10, background_reference=background_reference)

    draw = ImageDraw.Draw(base_img)

    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
        ratio = 70 / logo.height
        new_size = (int(logo.width * ratio), 70)
        logo = logo.resize(new_size, resample=Image.Resampling.LANCZOS)
        logo_y = header_bbox[1] + (HEADER_HEIGHT - logo.height) // 2
        base_img.alpha_composite(logo, (header_bbox[0] + 20, logo_y))

    name_font = fontes["header_name"]
    sub_font = fontes["header_sub"]
    text_block_x = header_bbox[0] + 140
    name_text = f"{nome}, {idade}"
    sub_text = f"{signo} • {elemento} • {regente}"

    name_size = name_font.getbbox(name_text)
    sub_size = sub_font.getbbox(sub_text)
    total_height = (name_size[3] - name_size[1]) + 4 + (sub_size[3] - sub_size[1])
    start_y = header_bbox[1] + (HEADER_HEIGHT - total_height) // 2

    draw.text((text_block_x, start_y), name_text, font=name_font, fill=COLOR_TEXT_PRIMARY)
    draw.text((text_block_x, start_y + (name_size[3] - name_size[1]) + 4), sub_text, font=sub_font, fill=COLOR_TEXT_SECONDARY)

    return header_bbox[3]


def draw_footer(draw: ImageDraw.ImageDraw) -> None:
    footer_text = "nutrisigno.com • perfil comportamental"
    font = _get_font(20)
    text_size = font.getbbox(footer_text)
    text_w = text_size[2] - text_size[0]
    text_h = text_size[3] - text_size[1]
    x = (WIDTH - text_w) // 2
    y = HEIGHT - FOOTER_MARGIN_BOTTOM - text_h
    draw.text((x, y), footer_text, font=font, fill=COLOR_TEXT_SECONDARY)


def gerar_card_comportamental(
    nome: str,
    idade: int,
    signo: str,
    elemento: str,
    regente: str,
    dados_comportamento: Dict[str, Sequence[str]],
    caminho_simbolo_signo: str,
    output_path: str,
) -> None:
    """Gera a imagem de perfil comportamental em PNG."""

    background = _create_vertical_gradient(WIDTH, HEIGHT, BACKGROUND_GRADIENT_TOP, BACKGROUND_GRADIENT_BOTTOM)
    background = draw_big_symbol_and_constellation(background, Path(caminho_simbolo_signo))
    canvas = background.copy()

    fontes = {
        "header_name": _get_font(48, "bold"),
        "header_sub": _get_font(28),
        "title": _get_font(34, "bold"),
        "body": _get_font(26),
        "icon": _get_font(34, "bold"),
        "highlight_title": _get_font(36, "bold"),
    }

    header_bottom = draw_header(
        canvas,
        background,
        nome=nome,
        idade=idade,
        signo=signo,
        elemento=elemento,
        regente=regente,
        fontes=fontes,
    )

    available_height = HEIGHT - header_bottom - SECTION_GAP - FOOTER_HEIGHT - FOOTER_MARGIN_BOTTOM
    destaque_height = int(HEIGHT * 0.2)
    cards_height = available_height - destaque_height - SECTION_GAP
    card_height = int((cards_height - CARD_GAP) / 2)
    card_width = int((WIDTH - 2 * MARGIN - CARD_GAP) / 2)

    cards_start_y = header_bottom + SECTION_GAP
    cards = []
    for row in range(2):
        for col in range(2):
            x0 = MARGIN + col * (card_width + CARD_GAP)
            y0 = cards_start_y + row * (card_height + CARD_GAP)
            x1 = x0 + card_width
            y1 = y0 + card_height
            cards.append((x0, y0, x1, y1))

    card_info = [
        ("Energia Comportamental", "⚡", dados_comportamento.get("energia", [])),
        ("Processamento Emocional", "❤", dados_comportamento.get("emocional", [])),
        ("Tomada de Decisão", "🎯", dados_comportamento.get("decisao", [])),
        ("Rotina & Hábitos", "🗓", dados_comportamento.get("rotina", [])),
    ]

    for bbox, (titulo, icone, linhas) in zip(cards, card_info):
        draw_glass_card(canvas, bbox, radius=CARD_RADIUS, blur_radius=10, background_reference=background)
        draw_behavior_card(ImageDraw.Draw(canvas), bbox, titulo, icone, linhas, fontes)

    destaque_y0 = cards_start_y + 2 * card_height + CARD_GAP + SECTION_GAP
    destaque_y1 = destaque_y0 + destaque_height
    destaque_bbox = (MARGIN, destaque_y0, WIDTH - MARGIN, destaque_y1)
    draw_glass_card(canvas, destaque_bbox, radius=BOTTOM_CARD_RADIUS, blur_radius=10, background_reference=background)
    draw = ImageDraw.Draw(canvas)
    title_text = f"Destaques Comportamentais de {signo}"
    draw.text((destaque_bbox[0] + BOTTOM_CARD_PADDING_X, destaque_y0 + BOTTOM_CARD_PADDING_Y), title_text, font=fontes["highlight_title"], fill=COLOR_TEXT_PRIMARY)
    body_y = destaque_y0 + BOTTOM_CARD_PADDING_Y + (fontes["highlight_title"].getbbox(title_text)[3] - fontes["highlight_title"].getbbox(title_text)[1]) + 10
    _draw_bullets(
        draw,
        (destaque_bbox[0] + BOTTOM_CARD_PADDING_X, body_y),
        dados_comportamento.get("destaques", []),
        _get_font(26),
        COLOR_TEXT_SECONDARY,
        line_spacing=12,
    )

    draw_footer(draw)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG")


if __name__ == "__main__":
    exemplo_dados = {
        "energia": [
            "Preferência por atividades matinais",
            "Ritmo estável com picos ao longo da semana",
        ],
        "emocional": [
            "Busca ambientes acolhedores para se expressar",
            "Valoriza relações com transparência",
        ],
        "decisao": [
            "Age rápido quando confia na intuição",
            "Consulta referências antes de decisões importantes",
        ],
        "rotina": [
            "Organiza tarefas por prioridades diárias",
            "Valoriza pausas curtas para manter foco",
        ],
        "destaques": [
            "Fortaleça rituais matinais com hidratação e luz natural",
            "Inclua atividades criativas para aliviar o estresse",
            "Use planners semanais para equilibrar compromissos",
        ],
    }

    simbolo_exemplo = ROOT_DIR / "assets" / "simbolo_exemplo.png"
    gerar_card_comportamental(
        nome="Alex",
        idade=29,
        signo="Aquário",
        elemento="Ar",
        regente="Urano",
        dados_comportamento=exemplo_dados,
        caminho_simbolo_signo=str(simbolo_exemplo),
        output_path=str(Path(__file__).resolve().parent / "outputs" / "perfil_comportamental.png"),
    )
