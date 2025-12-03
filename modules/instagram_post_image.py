"""Gerador de posts do Instagram no estilo aquarela mística NutriSigno.

Este módulo reconstrói o pipeline visual para posts 4:5 (1080x1350) com
camadas controladas, margens rígidas e tipografia centralizada.  A
abordagem prioriza a legibilidade do texto e a consistência da identidade
visual em tons de lilás/roxo.  Principais características:

* Safe area rígida de 120 px em todos os lados para o texto.
* Fundo em múltiplas camadas (base, manchas aquareladas, degradê,
  detalhes místicos, texto e logo).
* Engine de texto que ajusta o tamanho da fonte automaticamente e impede
  que blocos ultrapassem as margens ou o limite de linhas.
* Variações controladas via seed para posição das manchas, direção do
  degradê e distribuição dos detalhes.

A função principal é :func:`generate_instagram_post`, que retorna um
``PIL.Image`` pronto ou bytes PNG.
"""

from __future__ import annotations

import io
import math
import random
from dataclasses import dataclass
from typing import Optional, Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageFont

DEFAULT_LOGO_PATH = "assets/nutrisigno_logo.PNG"


# ===========================
# Configurações e constantes
# ===========================


@dataclass(frozen=True)
class LayoutConfig:
    """Parâmetros de layout e tipografia."""

    width: int = 1080
    height: int = 1350
    margin: int = 120
    text_align: str = "center"  # "center" ou "left"
    title_max_size: int = 90
    title_min_size: int = 52
    subtitle_ratio: float = 0.58
    subtitle_min_size: int = 30
    line_spacing: float = 1.18
    block_spacing: int = 28
    max_title_lines: int = 5
    max_subtitle_lines: int = 3
    safe_logo_margin: int = 48
    logo_size_ratio: tuple[float, float] = (0.06, 0.08)

    @property
    def safe_box(self) -> tuple[int, int, int, int]:
        """Retorna a caixa segura (left, top, right, bottom)."""

        left = self.margin
        top = self.margin
        right = self.width - self.margin
        bottom = self.height - self.margin
        return left, top, right, bottom

    @property
    def text_width(self) -> int:
        left, _, right, _ = self.safe_box
        return right - left


@dataclass(frozen=True)
class Palette:
    """Paleta de cores em tons lilás/roxo para o tema místico."""

    base: tuple[int, int, int] = (248, 244, 255)  # Lilás claríssimo
    light: tuple[int, int, int] = (230, 217, 255)
    medium: tuple[int, int, int] = (200, 178, 247)
    deep: tuple[int, int, int] = (109, 73, 173)
    accent: tuple[int, int, int] = (160, 124, 206)
    text_primary: tuple[int, int, int] = (60, 38, 92)
    text_secondary: tuple[int, int, int] = (80, 58, 112)
    white: tuple[int, int, int] = (255, 255, 255)


PALETTE = Palette()
CONFIG = LayoutConfig()

# Fontes de fallback (sem try/except em import).  A lista permite
# variação caso fontes decorativas estejam disponíveis no ambiente.
SCRIPT_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",  # exemplo
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
SANS_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
SANS_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


class TextLayoutError(ValueError):
    """Erro levantado quando o texto não cabe na área segura."""


# ===========================
# Utilidades de desenho
# ===========================


def _load_font(size: int, *, bold: bool = False, script: bool = False) -> ImageFont.FreeTypeFont:
    candidates: Sequence[str] = []
    if script:
        candidates = SCRIPT_FONT_CANDIDATES
    elif bold:
        candidates = SANS_BOLD_CANDIDATES
    else:
        candidates = SANS_FONT_CANDIDATES

    for path in candidates:
        try:
            font = ImageFont.truetype(path, size=size)
            return font
        except OSError:
            continue
    return ImageFont.load_default()


def _create_linear_gradient(size: tuple[int, int], colors: Sequence[tuple[int, int, int]], *, direction: float) -> Image.Image:
    """Gera um degradê linear na direção informada (radianos)."""

    width, height = size
    gradient = Image.new("RGBA", size)
    draw = ImageDraw.Draw(gradient)
    steps = max(width, height)
    cos_dir, sin_dir = math.cos(direction), math.sin(direction)

    for i in range(steps):
        t = i / max(1, steps - 1)
        c1, c2 = colors[0], colors[-1]
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        alpha = int(80 + 80 * (1 - abs(0.5 - t) * 2))
        x = int((cos_dir * i) % width)
        y = int((sin_dir * i) % height)
        draw.line([(x, 0), (x, height)], fill=(r, g, b, alpha))
        draw.line([(0, y), (width, y)], fill=(r, g, b, int(alpha * 0.6)))
    return gradient.filter(ImageFilter.GaussianBlur(radius=80))


def _draw_watercolor_blotches(base: Image.Image, rng: random.Random, *, safe_box: tuple[int, int, int, int]) -> None:
    """Adiciona manchas aquareladas suaves fora do centro de texto."""

    draw = ImageDraw.Draw(base, "RGBA")
    width, height = base.size
    left, top, right, bottom = safe_box

    regions = [
        (rng.uniform(-0.2, 0.1) * width, rng.uniform(-0.1, 0.2) * height),
        (rng.uniform(0.55, 0.85) * width, rng.uniform(-0.15, 0.15) * height),
        (rng.uniform(0.4, 0.8) * width, rng.uniform(0.55, 0.9) * height),
    ]
    blotch_palette = [
        (*PALETTE.light, 120),
        (*PALETTE.medium, 140),
        (*PALETTE.deep, 90),
    ]

    for center_x, center_y in regions:
        radius_x = rng.uniform(0.28, 0.4) * width
        radius_y = rng.uniform(0.22, 0.34) * height
        bbox = [
            center_x - radius_x,
            center_y - radius_y,
            center_x + radius_x,
            center_y + radius_y,
        ]
        # Evita sobreposição direta com área de texto.
        if not (bbox[2] < left or bbox[0] > right or bbox[3] < top or bbox[1] > bottom):
            shift_x = rng.uniform(-0.1, 0.1) * width
            shift_y = rng.uniform(-0.1, 0.1) * height
            bbox[0] -= shift_x
            bbox[2] -= shift_x
            bbox[1] += shift_y
            bbox[3] += shift_y
        color = rng.choice(blotch_palette)
        draw.ellipse(bbox, fill=color)

    base_blur = base.filter(ImageFilter.GaussianBlur(radius=60))
    base.paste(base_blur, mask=base_blur.split()[-1])


def _draw_mystic_sparks(base: Image.Image, rng: random.Random, *, safe_box: tuple[int, int, int, int]) -> None:
    """Insere pontos de luz discretos fora da área de texto."""

    draw = ImageDraw.Draw(base, "RGBA")
    left, top, right, bottom = safe_box
    width, height = base.size
    density = rng.randint(18, 28)

    for _ in range(density):
        x = rng.uniform(0, width)
        y = rng.uniform(0, height)
        if left < x < right and top < y < bottom:
            continue
        radius = rng.uniform(1.5, 3.5)
        alpha = rng.randint(90, 160)
        color = (*PALETTE.white, alpha)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


# ===========================
# Engine de texto
# ===========================


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, *, align: str) -> list[str]:
    """Quebra o texto em linhas sem exceder a largura."""

    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    for word in words[1:]:
        test = f"{current} {word}"
        bbox = draw.textbbox((0, 0), test, font=font, anchor="lt")
        if bbox[2] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)

    if align == "center":
        lines = [line.strip() for line in lines]
    return lines


def _fit_text_block(
    text: str,
    max_width: int,
    max_lines: int,
    target_size: int,
    min_size: int,
    *,
    bold: bool = False,
    script: bool = False,
    align: str,
) -> tuple[list[str], ImageFont.FreeTypeFont]:
    """Ajusta a fonte até o texto caber nas linhas permitidas."""

    for size in range(target_size, min_size - 1, -2):
        font = _load_font(size=size, bold=bold, script=script)
        lines = _wrap_text(text, font, max_width, align=align)
        if not lines or len(lines) > max_lines:
            continue
        width, _ = _measure_block(lines, font, line_spacing=1.0)
        if width <= max_width:
            return lines, font
    raise TextLayoutError("Texto longo demais para o layout definido")


def _measure_block(lines: Sequence[str], font: ImageFont.FreeTypeFont, *, line_spacing: float) -> tuple[int, int]:
    """Calcula largura e altura total de um bloco de texto."""

    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, anchor="lt")
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    if not widths:
        return 0, 0
    spacing_total = 0
    if len(heights) > 1:
        spacing_total = int(sum(h * (line_spacing - 1) for h in heights[:-1]))
    height_total = int(sum(heights) + spacing_total)
    return max(widths), height_total


# ===========================
# Camadas principais
# ===========================


def _compose_background(rng: random.Random, *, config: LayoutConfig) -> Image.Image:
    base = Image.new("RGBA", (config.width, config.height), (*PALETTE.base, 255))

    # Layer 1.5 – reforço de clareza na área de texto
    safe_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    safe_draw = ImageDraw.Draw(safe_overlay)
    left, top, right, bottom = config.safe_box
    safe_draw.rectangle((left, top, right, bottom), fill=(*PALETTE.base, 70))
    safe_overlay = safe_overlay.filter(ImageFilter.GaussianBlur(radius=36))
    base = Image.alpha_composite(base, safe_overlay)

    # Layer 2 – Manchas aquareladas
    blotch_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    _draw_watercolor_blotches(blotch_layer, rng, safe_box=config.safe_box)
    base = Image.alpha_composite(base, blotch_layer)

    # Layer 3 – Degradê suave
    gradient = _create_linear_gradient(
        base.size,
        colors=[PALETTE.light, PALETTE.medium, PALETTE.deep],
        direction=rng.uniform(math.radians(20), math.radians(70)) if rng.random() > 0.5 else rng.uniform(math.radians(110), math.radians(160)),
    )
    base = Image.alpha_composite(base, gradient)

    # Layer 4 – Detalhes místicos
    spark_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    _draw_mystic_sparks(spark_layer, rng, safe_box=config.safe_box)
    base = Image.alpha_composite(base, spark_layer)

    return base


def _draw_text_centered(
    image: Image.Image,
    lines: Sequence[str],
    font: ImageFont.FreeTypeFont,
    *,
    origin: tuple[int, int],
    color: tuple[int, int, int],
    line_spacing: float,
    align: str,
) -> None:
    draw = ImageDraw.Draw(image)
    x0, y0 = origin

    y = y0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, anchor="lt")
        line_height_effective = bbox[3] - bbox[1]
        if align == "center":
            x = x0 - bbox[2] // 2
        else:
            x = x0
        draw.text((x, y), line, font=font, fill=color)
        y += int(line_height_effective * line_spacing)


def _draw_logo(image: Image.Image, logo_path: str, *, config: LayoutConfig) -> None:
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except OSError:
        return

    rng = random.Random(hash(logo_path) % (2**32))
    target_ratio_min, target_ratio_max = config.logo_size_ratio
    target_width = int(config.width * rng.uniform(target_ratio_min, target_ratio_max))
    target_width = max(target_width, 60)
    scale = target_width / max(1, logo.width)
    target_height = int(logo.height * scale)
    logo = logo.resize((target_width, target_height), Image.LANCZOS)

    margin = max(config.safe_logo_margin, int(config.margin * 0.5))
    x = config.width - margin - logo.width
    y = config.height - margin - logo.height

    # Fundo translúcido para legibilidade do logo.
    pad = 18
    overlay = Image.new("RGBA", (logo.width + pad * 2, logo.height + pad * 2), (255, 255, 255, 36))
    blur = overlay.filter(ImageFilter.GaussianBlur(radius=10))
    image.alpha_composite(blur, dest=(x - pad, y - pad))
    image.alpha_composite(logo, dest=(x, y))


# ===========================
# API pública
# ===========================


def generate_instagram_post(
    title: str,
    subtitle: Optional[str] = None,
    *,
    logo_path: str = DEFAULT_LOGO_PATH,
    seed: Optional[int] = None,
    layout: LayoutConfig = CONFIG,
) -> Image.Image:
    """Gera uma imagem do feed 4:5 com o estilo aquarela mística NutriSigno.

    Parameters
    ----------
    title:
        Texto principal. Será ajustado automaticamente para caber na safe
        area, com limite de linhas e tamanho máximo/minimo de fonte.
    subtitle:
        Texto complementar opcional com hierarquia secundária.
    logo_path:
        Caminho para o logo NutriSigno. Um retângulo translúcido é adicionado
        para garantir legibilidade caso o fundo esteja intenso.
    seed:
        Semente opcional para gerar variações controladas de fundo
        (posicionamento de manchas, direção do degradê e brilhos).
    layout:
        Configuração opcional para ajustes finos de margem e tipografia.
    """

    rng = random.Random(seed)
    background = _compose_background(rng, config=layout)

    left, top, right, bottom = layout.safe_box
    safe_height = bottom - top

    # Engine de texto
    title_lines, title_font = _fit_text_block(
        title,
        layout.text_width,
        layout.max_title_lines,
        layout.title_max_size,
        layout.title_min_size,
        bold=True,
        script=True,
        align=layout.text_align,
    )
    subtitle_lines: list[str] = []
    subtitle_font: Optional[ImageFont.FreeTypeFont] = None
    if subtitle:
        target_size = max(int(layout.title_max_size * layout.subtitle_ratio), layout.subtitle_min_size)
        subtitle_lines, subtitle_font = _fit_text_block(
            subtitle,
            layout.text_width,
            layout.max_subtitle_lines,
            target_size,
            layout.subtitle_min_size,
            align=layout.text_align,
        )

    # Calcula blocos para posicionamento vertical
    title_w, title_h = _measure_block(title_lines, title_font, line_spacing=layout.line_spacing)
    subtitle_w, subtitle_h = (0, 0)
    if subtitle_lines and subtitle_font:
        subtitle_w, subtitle_h = _measure_block(subtitle_lines, subtitle_font, line_spacing=layout.line_spacing)

    total_height = title_h + subtitle_h
    if subtitle_lines:
        total_height += layout.block_spacing

    if total_height > safe_height:
        raise TextLayoutError("Texto longo demais para a área segura")

    start_y = top + (safe_height - total_height) // 2 - int(safe_height * 0.05)
    start_y = max(top, start_y)
    text_center_x = left + layout.text_width // 2 if layout.text_align == "center" else left

    _draw_text_centered(
        background,
        title_lines,
        title_font,
        origin=(text_center_x, start_y),
        color=PALETTE.text_primary,
        line_spacing=layout.line_spacing,
        align=layout.text_align,
    )

    if subtitle_lines and subtitle_font:
        subtitle_y = start_y + title_h + layout.block_spacing
        _draw_text_centered(
            background,
            subtitle_lines,
            subtitle_font,
            origin=(text_center_x, subtitle_y),
            color=PALETTE.text_secondary,
            line_spacing=layout.line_spacing,
            align=layout.text_align,
        )

    _draw_logo(background, logo_path, config=layout)

    return background


def generate_instagram_post_bytes(
    title: str,
    subtitle: Optional[str] = None,
    *,
    logo_path: str = DEFAULT_LOGO_PATH,
    seed: Optional[int] = None,
    layout: LayoutConfig = CONFIG,
    format: str = "PNG",
) -> bytes:
    """Versão que retorna bytes para download direto."""

    image = generate_instagram_post(title, subtitle, logo_path=logo_path, seed=seed, layout=layout)
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return buffer.getvalue()


__all__ = [
    "LayoutConfig",
    "Palette",
    "generate_instagram_post",
    "generate_instagram_post_bytes",
    "TextLayoutError",
]
