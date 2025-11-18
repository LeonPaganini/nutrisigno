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

import io
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

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
ACCENT_COLORS: Dict[ElementoSigno, Dict[str, str]] = {
    "Fogo": {"accent": "#ffb347", "detail": "#fcd34d"},
    "Água": {"accent": "#5ed0ff", "detail": "#a5f3fc"},
    "Terra": {"accent": "#7bd88a", "detail": "#bef264"},
    "Ar": {"accent": "#b19dff", "detail": "#d8ccff"},
}

TEXT_PALETTE = {
    "title": (200, 182, 255, 255),
    "body": (255, 255, 255, 255),
    "muted": (255, 255, 255, 153),
}

SECTION_GAP = 32

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

CARD_BASE_FILL = (255, 255, 255, 38)
CARD_BORDER_ALPHA = 64
CARD_SHADOW_ALPHA = 30

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


def _apply_background(image: Image.Image, colors: Tuple[str, str, str, str]) -> None:
    width, height = image.size
    diagonal = Image.linear_gradient("L").resize((width, height))
    diagonal = diagonal.rotate(45, resample=Image.BILINEAR, expand=True)
    offset_x = (diagonal.width - width) // 2
    offset_y = (diagonal.height - height) // 2
    diagonal = diagonal.crop((offset_x, offset_y, offset_x + width, offset_y + height))
    base = ImageOps.colorize(diagonal, colors[0], colors[-1]).convert("RGBA")

    radial = Image.radial_gradient("L").resize((width * 2, height * 2))
    radial = radial.crop((width // 2, height // 2, width // 2 + width, height // 2 + height))
    radial_overlay = ImageOps.colorize(radial, colors[1], colors[2]).convert("RGBA")
    radial_overlay.putalpha(140)
    base.alpha_composite(radial_overlay)

    noise = Image.effect_noise((width, height), 18).convert("L")
    noise_alpha = noise.point(lambda _: int(0.16 * 255))
    noise_rgba = Image.merge("RGBA", [noise, noise, noise, noise_alpha])
    base.alpha_composite(noise_rgba)

    image.paste(base)


def _draw_placeholder_logo(draw: ImageDraw.ImageDraw, position: Tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(position, radius=24, fill=(255, 255, 255, 35), outline=(255, 255, 255, 90), width=2)
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
               fill: Tuple[int, int, int, int] = (255, 255, 255, 255)) -> Tuple[int, int]:
    draw.text(position, text, font=font, fill=fill)
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_text_with_spacing(
    draw: ImageDraw.ImageDraw,
    text: str,
    position: Tuple[int, int],
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int, int],
    spacing: int = 1,
) -> Tuple[int, int]:
    if not text:
        return 0, 0

    x, y = position
    cursor = 0
    max_height = 0
    for character in text:
        bbox = font.getbbox(character or " ")
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        draw.text((x + cursor, y), character, font=font, fill=fill)
        cursor += width + spacing
        max_height = max(max_height, height)
    return cursor - spacing, max_height


def _measure_spaced_text(font: ImageFont.ImageFont, text: str, spacing: int) -> Tuple[int, int]:
    if not text:
        return 0, 0
    bbox = font.getbbox(text)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    width += max(len(text) - 1, 0) * spacing
    return width, height


def _draw_glass_panel(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[int, int, int, int],
    border_color: Tuple[int, int, int, int],
    radius: int = 32,
    fill: Tuple[int, int, int, int] | None = None,
) -> None:
    x1, y1, x2, y2 = bbox
    shadow_bbox = (x1, y1 + 8, x2, y2 + 8)
    shadow_color = (border_color[0], border_color[1], border_color[2], CARD_SHADOW_ALPHA)
    draw.rounded_rectangle(shadow_bbox, radius=radius, fill=shadow_color)
    outline_color = (border_color[0], border_color[1], border_color[2], CARD_BORDER_ALPHA)
    fill_color = fill if fill is not None else CARD_BASE_FILL
    draw.rounded_rectangle(bbox, radius=radius, fill=fill_color, outline=outline_color, width=3)


def _draw_metric_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int], title: str,
                      value: str, accent: Tuple[int, int, int, int], detail: Tuple[int, int, int, int]) -> None:
    _draw_glass_panel(draw, bbox, detail)
    title_font = _get_font(36)
    value_font = _get_font(64, "bold")
    x1, y1, x2, y2 = bbox
    draw.text((x1 + 32, y1 + 28), title, font=title_font, fill=TEXT_PALETTE["title"])
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
        outline=(255, 255, 255, 90),
        fill=(255, 255, 255, 25),
    )
    draw.rounded_rectangle(
        (x1 + bar_margin, bar_y, x1 + bar_margin + fill_width, bar_y + bar_height),
        radius=12,
        fill=accent,
    )


def _draw_radar(
    draw: ImageDraw.ImageDraw,
    center: Tuple[int, int],
    radius: int,
    values: Sequence[float],
    labels: Sequence[str],
    accent: Tuple[int, int, int, int],
    detail: Tuple[int, int, int, int],
) -> None:
    cx, cy = center
    hex_axes = 6
    guide_color = (255, 255, 255, 60)
    for level in range(1, 5):
        points = []
        for i in range(hex_axes):
            angle = math.pi / 2 + (2 * math.pi * i / hex_axes)
            r = radius * (level / 4)
            x = cx + r * math.cos(angle)
            y = cy - r * math.sin(angle)
            points.append((x, y))
        fill_color = None
        if level == 4:
            fill_color = (detail[0], detail[1], detail[2], 25)
        draw.polygon(points, outline=guide_color, fill=fill_color)
        draw.line(points + [points[0]], fill=guide_color, width=1)

    for i in range(hex_axes):
        angle = math.pi / 2 + (2 * math.pi * i / hex_axes)
        x = cx + radius * math.cos(angle)
        y = cy - radius * math.sin(angle)
        draw.line((cx, cy, x, y), fill=guide_color, width=1)

    axes = len(values)
    data_points = []
    for idx, value in enumerate(values):
        angle = math.pi / 2 + (2 * math.pi * idx / axes)
        x = cx + radius * value * math.cos(angle)
        y = cy - radius * value * math.sin(angle)
        data_points.append((x, y))
    fill_color = (accent[0], accent[1], accent[2], 80)
    draw.polygon(data_points, fill=fill_color, outline=accent)

    label_font = _get_font(28)
    for idx, label in enumerate(labels):
        angle = math.pi / 2 + (2 * math.pi * idx / axes)
        x = cx + (radius + 40) * math.cos(angle)
        y = cy - (radius + 40) * math.sin(angle)
        bbox = label_font.getbbox(label)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text((x - text_width / 2, y - text_height / 2), label, font=label_font, fill=TEXT_PALETTE["body"])


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


def _draw_list_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int],
                    title: str, items: Iterable[str], accent: Tuple[int, int, int, int],
                    detail: Tuple[int, int, int, int], max_items: int | None = None) -> None:
    translucent_lilac = (140, 120, 255, 46)
    _draw_glass_panel(draw, bbox, detail, radius=36, fill=translucent_lilac)
    x1, y1, x2, _ = bbox
    title_font = _get_font(40, "bold")
    text_font = _get_font(32)
    draw.text((x1 + 32, y1 + 32), title, font=title_font, fill=TEXT_PALETTE["title"])
    offset = y1 + 110
    bullet = "•"
    count = 0
    bullet_color = (accent[0], accent[1], accent[2], 210)
    for text in items:
        if max_items is not None and count >= max_items:
            break
        wrapped = _wrap_text(text, text_font, x2 - x1 - 90)
        for line in wrapped:
            draw.text((x1 + 48, offset), f"{bullet} ", font=text_font, fill=bullet_color)
            draw.text((x1 + 96, offset), line, font=text_font, fill=(255, 255, 255, 230))
            offset += 44
        count += 1


def _draw_insight_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int],
                       insight: str, accent: Tuple[int, int, int, int], detail: Tuple[int, int, int, int]) -> None:
    translucent_lilac = (140, 120, 255, 46)
    _draw_glass_panel(draw, bbox, detail, radius=36, fill=translucent_lilac)
    x1, y1, x2, y2 = bbox
    title_font = _get_font(40, "bold")
    text_font = _get_font(34)
    draw.text((x1 + 32, y1 + 32), TEXTOS_FIXOS["card_insight"], font=title_font, fill=TEXT_PALETTE["title"])
    insight_lines = _wrap_text(insight, text_font, x2 - x1 - 80)
    offset = y1 + 120
    for line in insight_lines:
        draw.text((x1 + 32, offset), line, font=text_font, fill=(255, 255, 255, 230))
        offset += 46
    footer_font = _get_font(28)
    draw.text((x1 + 32, y2 - 60), TEXTOS_FIXOS["card_rodape"], font=footer_font, fill=TEXT_PALETTE["muted"])


def _compose_story(
    image: Image.Image,
    data: ShareImagePayload,
    accent: Tuple[int, int, int, int],
    detail: Tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    padding = 80

    _draw_placeholder_logo(draw, (padding, padding, padding + 160, padding + 140))
    header_font = _get_font(30)
    _draw_text_with_spacing(
        draw,
        TEXTOS_FIXOS["header_subtitle"].upper(),
        (width - padding - 420, padding + 32),
        header_font,
        TEXT_PALETTE["muted"],
        spacing=2,
    )

    identity_top = padding + 160
    identity_bbox = (padding, identity_top, width - padding, identity_top + 210)
    _draw_glass_panel(draw, identity_bbox, detail, radius=40, fill=(30, 20, 60, 90))

    name_font = _get_font(72, "bold")
    subtitle_font = _get_font(42)
    name_text = f"{data.primeiro_nome}, {data.idade}"
    draw.text((identity_bbox[0] + 32, identity_bbox[1] + 32), name_text, font=name_font, fill=TEXT_PALETTE["body"])
    draw.text(
        (identity_bbox[0] + 32, identity_bbox[1] + 120),
        f"{data.signo} • {data.elemento}",
        font=subtitle_font,
        fill=TEXT_PALETTE["title"],
    )
    divider_y = identity_bbox[3] + 12
    draw.line(
        (padding, divider_y, width - padding, divider_y),
        fill=(detail[0], detail[1], detail[2], 120),
        width=2,
    )

    card_height = 220
    gap = SECTION_GAP
    card_width = int((width - 2 * padding - 2 * gap) / 3)
    card_top = divider_y + gap
    card_positions = [
        (padding + i * (card_width + gap), card_top, padding + i * (card_width + gap) + card_width, card_top + card_height)
        for i in range(3)
    ]
    _draw_metric_card(draw, card_positions[0], TEXTOS_FIXOS["card_imc"], f"{data.imc:.1f}", accent, detail)
    _draw_metric_card(draw, card_positions[1], TEXTOS_FIXOS["card_score"], f"{data.score_geral:.0f}", accent, detail)
    _draw_hydration_card(draw, card_positions[2], data.hidratacao_score, accent, detail)

    normalized, labels = _normalize_values(data)
    radar_radius = 220
    radar_center = (width // 2, card_top + card_height + radar_radius + gap)
    _draw_radar(draw, radar_center, radar_radius, normalized, labels, accent, detail)

    list_top = radar_center[1] + radar_radius + gap
    list_height = 260
    _draw_list_card(
        draw,
        (padding, list_top, width - padding, list_top + list_height),
        TEXTOS_FIXOS["card_comportamentos"],
        data.comportamentos,
        accent,
        detail,
    )

    insight_top = list_top + list_height + gap
    _draw_insight_card(
        draw,
        (padding, insight_top, width - padding, insight_top + 260),
        data.insight_frase,
        accent,
        detail,
    )

    footer_font = _get_font(26)
    footer_text = TEXTOS_FIXOS["footer"].upper()
    footer_width, _ = _measure_spaced_text(footer_font, footer_text, 2)
    footer_x = (width - footer_width) / 2
    footer_y = height - padding - 20
    _draw_text_with_spacing(
        draw,
        footer_text,
        (int(footer_x), footer_y),
        footer_font,
        TEXT_PALETTE["muted"],
        spacing=2,
    )


def _compose_feed(
    image: Image.Image,
    data: ShareImagePayload,
    accent: Tuple[int, int, int, int],
    detail: Tuple[int, int, int, int],
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    padding = 60

    _draw_placeholder_logo(draw, (padding, padding, padding + 120, padding + 120))
    header_font = _get_font(26)
    _draw_text_with_spacing(
        draw,
        TEXTOS_FIXOS["header_subtitle"].upper(),
        (width - padding - 360, padding + 28),
        header_font,
        TEXT_PALETTE["muted"],
        spacing=2,
    )

    identity_top = padding + 130
    identity_bbox = (padding, identity_top, width - padding, identity_top + 180)
    _draw_glass_panel(draw, identity_bbox, detail, radius=32, fill=(30, 20, 60, 90))
    name_font = _get_font(64, "bold")
    subtitle_font = _get_font(38)
    draw.text((identity_bbox[0] + 28, identity_bbox[1] + 24), f"{data.primeiro_nome}, {data.idade}", font=name_font, fill=TEXT_PALETTE["body"])
    draw.text(
        (identity_bbox[0] + 28, identity_bbox[1] + 100),
        f"{data.signo} • {data.elemento}",
        font=subtitle_font,
        fill=TEXT_PALETTE["title"],
    )

    gap = SECTION_GAP
    column_width = (width - 3 * padding) // 2
    card_height = 150
    card_top = identity_bbox[3] + gap

    _draw_metric_card(
        draw,
        (padding, card_top, padding + column_width, card_top + card_height),
        TEXTOS_FIXOS["card_imc"],
        f"{data.imc:.1f}",
        accent,
        detail,
    )
    second_card_top = card_top + card_height + gap
    _draw_metric_card(
        draw,
        (padding, second_card_top, padding + column_width, second_card_top + card_height),
        TEXTOS_FIXOS["card_score"],
        f"{data.score_geral:.0f}",
        accent,
        detail,
    )

    right_x = padding + column_width + gap
    hydration_height = 170
    _draw_hydration_card(
        draw,
        (right_x, card_top, right_x + column_width, card_top + hydration_height),
        data.hidratacao_score,
        accent,
        detail,
    )

    normalized, labels = _normalize_values(data)
    radar_radius = 110
    radar_center_y = card_top + hydration_height + gap + radar_radius
    radar_center = (right_x + column_width // 2, radar_center_y)
    _draw_radar(draw, radar_center, radar_radius, normalized, labels, accent, detail)

    column_bottom = max(second_card_top + card_height, radar_center[1] + radar_radius)
    info_top = min(max(column_bottom + gap, identity_bbox[3] + 3 * gap), height - padding - 200)
    list_bbox = (padding, info_top, padding + column_width, height - padding)
    insight_bbox = (right_x, info_top, width - padding, height - padding)
    _draw_list_card(
        draw,
        list_bbox,
        TEXTOS_FIXOS["card_comportamentos"],
        data.comportamentos,
        accent,
        detail,
        max_items=3,
    )
    _draw_insight_card(draw, insight_bbox, data.insight_frase, accent, detail)

    footer_font = _get_font(22)
    footer_text = TEXTOS_FIXOS["footer"].upper()
    footer_width, _ = _measure_spaced_text(footer_font, footer_text, 2)
    footer_x = (width - footer_width) / 2
    _draw_text_with_spacing(
        draw,
        footer_text,
        (int(footer_x), height - padding - 20),
        footer_font,
        TEXT_PALETTE["muted"],
        spacing=2,
    )


def gerar_imagem_share(dados_compartilhamento: Dict[str, Any] | ShareImagePayload,
                        formato: FormatoImagem = "story") -> bytes:
    """Gera a imagem em memória e retorna os bytes em PNG."""

    if formato not in FORMATO_DIMENSOES:
        raise ValueError("Formato inválido. Use 'story' ou 'feed'.")

    if isinstance(dados_compartilhamento, ShareImagePayload):
        payload = dados_compartilhamento
    else:
        payload = ShareImagePayload.from_mapping(dados_compartilhamento)

    width, height = FORMATO_DIMENSOES[formato]
    image = Image.new("RGBA", (width, height))
    _apply_background(image, BACKGROUND_GRADIENT)

    accent_hex = ACCENT_COLORS[payload.elemento]["accent"]
    detail_hex = ACCENT_COLORS[payload.elemento]["detail"]
    accent_color = _hex_to_rgba(accent_hex, 220)
    detail_color = _hex_to_rgba(detail_hex, 200)

    if formato == "story":
        _compose_story(image, payload, accent_color, detail_color)
    else:
        _compose_feed(image, payload, accent_color, detail_color)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
