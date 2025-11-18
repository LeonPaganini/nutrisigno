"""Geração de imagens compartilháveis para o NutriSigno.

Este módulo encapsula a criação de imagens em memória que representam o
resultado público de um usuário.  A ideia é permitir que o frontend
exiba um botão "Compartilhar resultado" que, ao ser acionado, faça o
download de um PNG gerado sob demanda com tema astrológico.

Desta forma, o módulo não conhece detalhes de Streamlit ou qualquer
framework web – ele apenas recebe os dados prontos, desenha a imagem e
retorna os bytes para quem chamou.
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

FormatoImagem = Literal["story", "feed"]
ElementoSigno = Literal["Fogo", "Água", "Terra", "Ar"]


@dataclass(frozen=True)
class ShareImagePayload:
    """Estrutura mínima de dados para montar o template."""

    primeiro_nome: str
    idade: int
    imc: float
    score_geral: float
    hidratacao_score: float
    signo: str
    elemento: ElementoSigno
    comportamentos: Sequence[str] = field(default_factory=list)
    insight_frase: str = ""

    @classmethod
    def from_mapping(cls, data: Dict[str, Any]) -> "ShareImagePayload":
        required = {
            "primeiro_nome",
            "idade",
            "imc",
            "score_geral",
            "hidratacao_score",
            "signo",
            "elemento",
            "comportamentos",
            "insight_frase",
        }
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Campos obrigatórios ausentes: {', '.join(missing)}")

        primeiro_nome = str(data["primeiro_nome"]).strip()
        if not primeiro_nome or len(primeiro_nome) > 30:
            raise ValueError("primeiro_nome deve ter entre 1 e 30 caracteres")

        signo = str(data["signo"]).strip() or "Signo"
        elemento = str(data["elemento"]).strip().title()
        if elemento not in {"Fogo", "Água", "Agua", "Terra", "Ar"}:
            raise ValueError("elemento inválido. Use Fogo, Água, Terra ou Ar")
        elemento = "Água" if elemento == "Agua" else elemento  # normaliza acento

        comportamentos = [
            str(item).strip()
            for item in list(data.get("comportamentos", []))[:3]
            if str(item).strip()
        ]
        if not comportamentos:
            raise ValueError("É necessário fornecer ao menos um comportamento")

        idade = int(data["idade"])
        hidratacao_score = float(data["hidratacao_score"])
        return cls(
            primeiro_nome=primeiro_nome,
            idade=idade,
            imc=float(data["imc"]),
            score_geral=float(data["score_geral"]),
            hidratacao_score=hidratacao_score,
            signo=signo,
            elemento=elemento,  # type: ignore[arg-type]
            comportamentos=comportamentos,
            insight_frase=str(data["insight_frase"]).strip(),
        )


BACKGROUND_GRADIENT = ("#2A1457", "#3D1F78", "#6A3CBD", "#9F6CFF")
NOISE_INTENSITY = 0.15
VERTICAL_SPACING = 32
CARD_RADIUS = 32

ACCENT_COLORS: Dict[ElementoSigno, Dict[str, str]] = {
    "Fogo": {"accent": "#FFB347", "detail": "#FF8C42", "soft": "#FFE3B3"},
    "Água": {"accent": "#5ED0FF", "detail": "#3BA7E4", "soft": "#BFE9FF"},
    "Terra": {"accent": "#7BD88A", "detail": "#4EAD60", "soft": "#C3F0CF"},
    "Ar": {"accent": "#B19DFF", "detail": "#8B6CFF", "soft": "#DDD0FF"},
}

TEXTOS_FIXOS = {
    "header_subtitle": "NutriSigno • Mapa Nutricional",
    "card_imc": "IMC",
    "card_score": "Score NutriSigno",
    "card_hidratacao": "Hidratação",
    "card_comportamentos": "Comportamentos em Destaque",
    "card_insight": "Insight NutriSigno",
    "card_rodape": "Gerado por NutriSigno",
    "footer": "nutrisigno.com • Resultado público",
}

FORMATO_DIMENSOES: Dict[FormatoImagem, Tuple[int, int]] = {
    "story": (1080, 1920),
    "feed": (1080, 1080),
}

_FONT_CACHE: Dict[Tuple[int, str], ImageFont.FreeTypeFont] = {}


def _get_font(size: int, weight: str = "regular") -> ImageFont.ImageFont:
    key = (size, weight)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates = []
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


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b, alpha


def _with_alpha(color: Tuple[int, int, int, int], alpha: int) -> Tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def _mix_with_white(color: Tuple[int, int, int, int], factor: float) -> Tuple[int, int, int, int]:
    r = int(color[0] + (255 - color[0]) * factor)
    g = int(color[1] + (255 - color[1]) * factor)
    b = int(color[2] + (255 - color[2]) * factor)
    return r, g, b, color[3]


def _apply_gradient_background(image: Image.Image, colors: Tuple[str, ...]) -> None:
    width, height = image.size
    segments = len(colors) - 1
    if segments <= 0:
        image.paste(_hex_to_rgba(colors[0]), [0, 0, width, height])
        return

    pixels = image.load()
    for y in range(height):
        y_ratio = y / max(height - 1, 1)
        for x in range(width):
            x_ratio = x / max(width - 1, 1)
            ratio = (x_ratio * 0.35) + (y_ratio * 0.65)
            ratio = max(0.0, min(ratio, 1.0))
            scaled = ratio * segments
            idx = min(int(scaled), segments - 1)
            local = scaled - idx
            start = _hex_to_rgba(colors[idx])
            end = _hex_to_rgba(colors[idx + 1])
            r = int(start[0] + (end[0] - start[0]) * local)
            g = int(start[1] + (end[1] - start[1]) * local)
            b = int(start[2] + (end[2] - start[2]) * local)
            pixels[x, y] = (r, g, b, 255)


def _apply_noise_overlay(
    image: Image.Image,
    intensity: float = NOISE_INTENSITY,
    rng: random.Random | None = None,
) -> None:
    if intensity <= 0:
        return
    rng = rng or random.Random()
    width, height = image.size
    tile_size = 256
    tile = Image.new("L", (tile_size, tile_size))
    pixels = tile.load()
    for y in range(tile_size):
        for x in range(tile_size):
            pixels[x, y] = int(rng.random() * 255)
    noise = tile.resize((width, height), resample=Image.BILINEAR)
    alpha = noise.point(lambda px: int(px * intensity))
    overlay = Image.merge("RGBA", (noise, noise, noise, alpha))
    image.alpha_composite(overlay)


def _scatter_sparkles(
    image: Image.Image,
    count: int = 140,
    rng: random.Random | None = None,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    rng = rng or random.Random()
    for _ in range(count):
        x = rng.randint(0, width)
        y = rng.randint(0, height)
        radius = rng.randint(1, 3)
        opacity = rng.randint(18, 40)
        draw.ellipse((x, y, x + radius, y + radius), fill=(255, 255, 255, opacity))


def _draw_placeholder_logo(draw: ImageDraw.ImageDraw, position: Tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(position, radius=20, outline=(255, 255, 255, 120), width=2)
    text = "LOGO"
    font = _get_font(28, "bold")
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x1, y1, x2, y2 = position
    draw.text(((x1 + x2 - w) / 2, (y1 + y2 - h) / 2), text, font=font, fill=(255, 255, 255, 180))


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    if not text:
        return []
    lines: List[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}".strip()
            bbox = font.getbbox(candidate)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def _draw_text(draw: ImageDraw.ImageDraw, text: str, position: Tuple[int, int], font: ImageFont.ImageFont,
               fill: Tuple[int, int, int, int] = (255, 255, 255, 255), letter_spacing: float = 0.0) -> Tuple[int, int]:
    if not letter_spacing:
        draw.text(position, text, font=font, fill=fill)
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    x, y = position
    total_width = 0
    spacing_px = font.size * letter_spacing
    for char in text:
        draw.text((x + total_width, y), char, font=font, fill=fill)
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        total_width += char_width + spacing_px
    height = font.getbbox(text)[3] - font.getbbox(text)[1]
    return int(total_width), height


def _draw_card_base(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int],
                    detail: Tuple[int, int, int, int], fill_alpha: float = 0.15) -> None:
    x1, y1, x2, y2 = bbox
    shadow_offset = 10
    shadow_color = (detail[0], detail[1], detail[2], 70)
    draw.rounded_rectangle(
        (x1 + shadow_offset, y1 + shadow_offset, x2 + shadow_offset, y2 + shadow_offset),
        radius=CARD_RADIUS + 8,
        fill=shadow_color,
    )
    fill_color = (255, 255, 255, int(255 * fill_alpha))
    border_color = (detail[0], detail[1], detail[2], 140)
    draw.rounded_rectangle(bbox, radius=CARD_RADIUS, fill=fill_color, outline=border_color, width=3)


def _draw_metric_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int], title: str,
                      value: str, accent: Tuple[int, int, int, int], detail: Tuple[int, int, int, int]) -> None:
    _draw_card_base(draw, bbox, detail)
    title_font = _get_font(32)
    value_font = _get_font(68, "bold")
    x1, y1, x2, y2 = bbox
    _draw_text(draw, title, (x1 + 32, y1 + 32), title_font, fill=_with_alpha(detail, 220), letter_spacing=0.015)
    bbox_value = value_font.getbbox(value)
    value_height = bbox_value[3] - bbox_value[1]
    draw.text((x1 + 32, y2 - value_height - 40), value, font=value_font, fill=accent)


def _draw_hydration_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int],
                         value: float, accent: Tuple[int, int, int, int], detail: Tuple[int, int, int, int]) -> None:
    _draw_metric_card(draw, bbox, TEXTOS_FIXOS["card_hidratacao"], f"{value:.0f}", accent, detail)
    x1, y1, x2, y2 = bbox
    bar_height = 24
    bar_margin = 40
    bar_y = y2 - bar_height - 48
    fill_width = (x2 - x1 - 2 * bar_margin) * max(0.0, min(value, 100.0)) / 100.0
    draw.rounded_rectangle(
        (x1 + bar_margin, bar_y, x2 - bar_margin, bar_y + bar_height),
        radius=12,
        outline=_with_alpha(detail, 120),
        fill=(255, 255, 255, 40),
    )
    draw.rounded_rectangle(
        (x1 + bar_margin, bar_y, x1 + bar_margin + fill_width, bar_y + bar_height),
        radius=12,
        fill=accent,
    )


def _draw_radar(draw: ImageDraw.ImageDraw, center: Tuple[int, int], radius: int,
                values: Sequence[float], labels: Sequence[str], accent: Tuple[int, int, int, int],
                detail: Tuple[int, int, int, int]) -> None:
    cx, cy = center
    axes = len(values)
    grid_levels = 4

    # fundo hexagonal translúcido
    for level in range(1, grid_levels + 1):
        ratio = level / grid_levels
        points = []
        for idx in range(6):
            angle = math.pi / 2 + (2 * math.pi * idx / 6)
            r = radius * ratio
            x = cx + r * math.cos(angle)
            y = cy - r * math.sin(angle)
            points.append((x, y))
        fill = (255, 255, 255, int(20 * ratio))
        draw.polygon(points, outline=(255, 255, 255, 70), fill=fill)

    # linhas de eixos específicos
    axis_color = _with_alpha(detail, 160)
    for idx in range(axes):
        angle = math.pi / 2 + (2 * math.pi * idx / axes)
        x = cx + radius * math.cos(angle)
        y = cy - radius * math.sin(angle)
        draw.line((cx, cy, x, y), fill=(255, 255, 255, 90), width=2)

    data_points = []
    for idx, value in enumerate(values):
        angle = math.pi / 2 + (2 * math.pi * idx / axes)
        r = radius * max(0.0, min(value, 1.0))
        x = cx + r * math.cos(angle)
        y = cy - r * math.sin(angle)
        data_points.append((x, y))

    fill_color = (200, 180, 255, int(255 * 0.28))
    draw.polygon(data_points, fill=fill_color, outline=axis_color)

    label_font = _get_font(28)
    for idx, label in enumerate(labels):
        angle = math.pi / 2 + (2 * math.pi * idx / axes)
        x = cx + (radius + 36) * math.cos(angle)
        y = cy - (radius + 36) * math.sin(angle)
        bbox = label_font.getbbox(label)
        width = bbox[2] - bbox[0]
        draw.text((x - width / 2, y - 12), label, font=label_font, fill=(255, 255, 255, 210))


def _normalize_values(data: ShareImagePayload) -> Tuple[Sequence[float], Sequence[str]]:
    limits = {
        "IMC": 40,
        "Score": 100,
        "Hidratação": 100,
    }
    values = [data.imc, data.score_geral, data.hidratacao_score]
    labels = list(limits.keys())
    normalized = [max(0.0, min(value / limits[label], 1.0)) for value, label in zip(values, labels)]
    return normalized, labels


def _draw_list_card(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[int, int, int, int],
    title: str,
    items: Iterable[str],
    accent: Tuple[int, int, int, int],
    max_items: int | None = None,
    base_color: Tuple[int, int, int, int] | None = None,
    compact: bool = False,
) -> None:
    x1, y1, x2, y2 = bbox
    base_fill = base_color or (160, 140, 255, int(255 * 0.18))
    border = _with_alpha(accent, 160)
    shadow = (accent[0], accent[1], accent[2], 60)
    draw.rounded_rectangle((x1 + 8, y1 + 12, x2 + 8, y2 + 12), radius=40, fill=shadow)
    draw.rounded_rectangle(bbox, radius=40, fill=base_fill, outline=border, width=3)
    title_font = _get_font(36 if compact else 40, "bold")
    text_font = _get_font(24 if compact else 30)
    title_y = y1 + (24 if compact else 32)
    _draw_text(draw, title, (x1 + 32, title_y), title_font, fill=_with_alpha(accent, 230))
    offset = title_y + (40 if compact else 90)
    bullet = "•"
    count = 0
    max_width = x2 - x1 - 110
    for text in items:
        if max_items is not None and count >= max_items:
            break
        wrapped = _wrap_text(text, text_font, max_width)
        for line in wrapped:
            _draw_text(
                draw,
                f"{bullet} {line}",
                (x1 + 48, offset),
                text_font,
                fill=(255, 255, 255, 230),
                letter_spacing=0.012,
            )
            offset += 30 if compact else 44
        count += 1


def _draw_insight_card(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[int, int, int, int],
    insight: str,
    accent: Tuple[int, int, int, int],
    compact: bool = False,
) -> None:
    x1, y1, x2, y2 = bbox
    fill_color = (170, 150, 255, int(255 * 0.2))
    border = _with_alpha(accent, 170)
    draw.rounded_rectangle((x1 + 8, y1 + 10, x2 + 8, y2 + 10), radius=40, fill=(accent[0], accent[1], accent[2], 60))
    draw.rounded_rectangle(bbox, radius=40, fill=fill_color, outline=border, width=3)
    title_font = _get_font(32 if compact else 40, "bold")
    text_font = _get_font(26 if compact else 32)
    footer_font = _get_font(22 if compact else 26)
    title_y = y1 + (28 if compact else 36)
    _draw_text(
        draw,
        TEXTOS_FIXOS["card_insight"],
        (x1 + 32, title_y),
        title_font,
        fill=_with_alpha(accent, 230),
    )
    insight_lines = _wrap_text(insight, text_font, x2 - x1 - 80)
    offset = title_y + (50 if compact else 92)
    for line in insight_lines:
        _draw_text(draw, line, (x1 + 32, offset), text_font, fill=(255, 255, 255, 230), letter_spacing=0.01)
        offset += 32 if compact else 46
    _draw_text(
        draw,
        TEXTOS_FIXOS["card_rodape"],
        (x1 + 32, y2 - (48 if compact else 64)),
        footer_font,
        fill=(255, 255, 255, 160),
        letter_spacing=0.02,
    )


def _compose_story(
    image: Image.Image,
    data: ShareImagePayload,
    accent: Tuple[int, int, int, int],
    detail: Tuple[int, int, int, int],
    soft: Tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    margin = 90

    _draw_placeholder_logo(draw, (margin, 70, margin + 160, 230))
    header_font = _get_font(32)
    _draw_text(
        draw,
        TEXTOS_FIXOS["header_subtitle"],
        (width - 500, 120),
        header_font,
        fill=(255, 255, 255, 200),
        letter_spacing=0.02,
    )

    name_font = _get_font(72, "bold")
    subtitle_font = _get_font(40)
    _draw_text(draw, f"{data.primeiro_nome}, {data.idade}", (margin, 250), name_font, fill=(255, 255, 255, 255))
    subtitle_color = _mix_with_white(_with_alpha(soft, 220), 0.25)
    _draw_text(
        draw,
        f"{data.signo} • {data.elemento}",
        (margin, 250 + VERTICAL_SPACING + 50),
        subtitle_font,
        fill=subtitle_color,
        letter_spacing=0.01,
    )

    line_y = 250 + 120 + VERTICAL_SPACING
    draw.line((margin, line_y, width - margin, line_y), fill=_with_alpha(detail, 120), width=2)
    draw.line((margin, line_y + 4, width - margin, line_y + 4), fill=_with_alpha(detail, 50), width=2)

    card_height = 230
    card_gap = 32
    card_width = int((width - 2 * margin - 2 * card_gap) / 3)
    cards_top = line_y + VERTICAL_SPACING
    card_positions = [
        (margin, cards_top, margin + card_width, cards_top + card_height),
        (margin + card_width + card_gap, cards_top, margin + 2 * card_width + card_gap, cards_top + card_height),
        (
            margin + 2 * (card_width + card_gap),
            cards_top,
            margin + 3 * card_width + 2 * card_gap,
            cards_top + card_height,
        ),
    ]
    _draw_metric_card(draw, card_positions[0], TEXTOS_FIXOS["card_imc"], f"{data.imc:.1f}", accent, detail)
    _draw_metric_card(draw, card_positions[1], TEXTOS_FIXOS["card_score"], f"{data.score_geral:.0f}", accent, detail)
    _draw_hydration_card(draw, card_positions[2], data.hidratacao_score, accent, detail)

    normalized, labels = _normalize_values(data)
    radar_center_y = cards_top + card_height + 200
    _draw_radar(draw, (width // 2, radar_center_y), 240, normalized, labels, accent, detail)

    list_top = radar_center_y + 240
    list_height = 240
    _draw_list_card(
        draw,
        (margin, list_top, width - margin, list_top + list_height),
        TEXTOS_FIXOS["card_comportamentos"],
        data.comportamentos,
        accent,
        base_color=soft,
    )

    insight_top = list_top + list_height + VERTICAL_SPACING
    _draw_insight_card(draw, (margin, insight_top, width - margin, insight_top + 260), data.insight_frase, accent)

    footer_font = _get_font(24)
    footer_text = TEXTOS_FIXOS["footer"]
    bbox = footer_font.getbbox(footer_text)
    footer_width = bbox[2] - bbox[0]
    _draw_text(
        draw,
        footer_text,
        ((width - footer_width) // 2, height - 110),
        footer_font,
        fill=(255, 255, 255, 150),
        letter_spacing=0.018,
    )


def _compose_feed(
    image: Image.Image,
    data: ShareImagePayload,
    accent: Tuple[int, int, int, int],
    detail: Tuple[int, int, int, int],
    soft: Tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    margin = 60
    bottom_margin = 30

    _draw_placeholder_logo(draw, (margin, 40, margin + 120, 180))
    header_font = _get_font(28)
    _draw_text(
        draw,
        TEXTOS_FIXOS["header_subtitle"],
        (width - 440, 80),
        header_font,
        fill=(255, 255, 255, 200),
        letter_spacing=0.02,
    )

    name_font = _get_font(64, "bold")
    subtitle_font = _get_font(38)
    name_y = 190
    _draw_text(draw, f"{data.primeiro_nome}, {data.idade}", (margin, name_y), name_font, fill=(255, 255, 255, 255))
    subtitle_color = _mix_with_white(_with_alpha(soft, 220), 0.25)
    _draw_text(
        draw,
        f"{data.signo} • {data.elemento}",
        (margin, name_y + VERTICAL_SPACING + 30),
        subtitle_font,
        fill=subtitle_color,
        letter_spacing=0.012,
    )
    line_y = name_y + 110
    draw.line((margin, line_y, width - margin, line_y), fill=_with_alpha(detail, 120), width=2)

    card_gap = 24
    card_width = int((width - 2 * margin - card_gap) / 2)
    card_height = 130
    cards_top = line_y + 24
    _draw_metric_card(
        draw,
        (margin, cards_top, margin + card_width, cards_top + card_height),
        TEXTOS_FIXOS["card_imc"],
        f"{data.imc:.1f}",
        accent,
        detail,
    )
    _draw_metric_card(
        draw,
        (margin + card_width + card_gap, cards_top, width - margin, cards_top + card_height),
        TEXTOS_FIXOS["card_score"],
        f"{data.score_geral:.0f}",
        accent,
        detail,
    )
    hydration_top = cards_top + card_height + card_gap
    _draw_hydration_card(
        draw,
        (margin, hydration_top, width - margin, hydration_top + card_height),
        data.hidratacao_score,
        accent,
        detail,
    )

    normalized, labels = _normalize_values(data)
    radar_radius = 140
    radar_center_y = hydration_top + card_height + 50
    _draw_radar(draw, (width // 2, radar_center_y), radar_radius, normalized, labels, accent, detail)

    list_height = 100
    list_top = radar_center_y + radar_radius + 10
    _draw_list_card(
        draw,
        (margin, list_top, width - margin, list_top + list_height),
        TEXTOS_FIXOS["card_comportamentos"],
        data.comportamentos,
        accent,
        max_items=2,
        base_color=soft,
        compact=True,
    )
    insight_top = list_top + list_height + 20
    _draw_insight_card(
        draw,
        (margin, insight_top, width - margin, height - bottom_margin),
        data.insight_frase,
        accent,
        compact=True,
    )


def _derive_seed(
    payload: ShareImagePayload,
    formato: FormatoImagem,
    explicit_seed: int | None,
) -> int:
    if explicit_seed is not None:
        return explicit_seed

    parts = [
        payload.primeiro_nome.strip().lower(),
        str(payload.idade),
        f"{payload.imc:.2f}",
        f"{payload.score_geral:.2f}",
        f"{payload.hidratacao_score:.2f}",
        payload.signo.strip().lower(),
        payload.elemento,
        "|".join(str(item) for item in payload.comportamentos),
        payload.insight_frase.strip(),
        formato,
    ]
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def gerar_imagem_share(dados_compartilhamento: Dict[str, Any] | ShareImagePayload,
                        formato: FormatoImagem = "story",
                        seed: int | None = None) -> bytes:
    """Gera a imagem em memória e retorna os bytes em PNG.

    O parâmetro opcional ``seed`` (ou o hash derivado dos dados) mantém o mesmo
    resultado visual para payloads idênticos, garantindo previsibilidade.
    """

    if formato not in FORMATO_DIMENSOES:
        raise ValueError("Formato inválido. Use 'story' ou 'feed'.")

    if isinstance(dados_compartilhamento, ShareImagePayload):
        payload = dados_compartilhamento
    else:
        payload = ShareImagePayload.from_mapping(dados_compartilhamento)

    width, height = FORMATO_DIMENSOES[formato]
    image = Image.new("RGBA", (width, height))
    _apply_gradient_background(image, BACKGROUND_GRADIENT)

    seed_value = _derive_seed(payload, formato, seed)
    rng = random.Random(seed_value)
    _apply_noise_overlay(image, NOISE_INTENSITY, rng)
    _scatter_sparkles(image, rng=rng)

    palette = ACCENT_COLORS[payload.elemento]
    accent_color = _hex_to_rgba(palette["accent"], 230)
    detail_color = _hex_to_rgba(palette["detail"], 210)
    soft_color = _hex_to_rgba(palette["soft"], 180)

    if formato == "story":
        _compose_story(image, payload, accent_color, detail_color, soft_color)
    else:
        _compose_feed(image, payload, accent_color, detail_color, soft_color)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
