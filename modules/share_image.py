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


BACKGROUND_GRADIENT = ("#09061f", "#1d0c40", "#2c0f5f")
ACCENT_COLORS: Dict[ElementoSigno, Dict[str, str]] = {
    "Fogo": {"accent": "#ffb347", "shadow": "#d97706"},
    "Água": {"accent": "#5ed0ff", "shadow": "#0891b2"},
    "Terra": {"accent": "#7bd88a", "shadow": "#15803d"},
    "Ar": {"accent": "#b19dff", "shadow": "#7c3aed"},
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


def _apply_vertical_gradient(image: Image.Image, colors: Tuple[str, str, str]) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for i in range(height):
        ratio = i / max(height - 1, 1)
        # interpolação entre 3 cores
        if ratio < 0.5:
            local = ratio / 0.5
            start = _hex_to_rgba(colors[0])
            end = _hex_to_rgba(colors[1])
        else:
            local = (ratio - 0.5) / 0.5
            start = _hex_to_rgba(colors[1])
            end = _hex_to_rgba(colors[2])
        r = int(start[0] + (end[0] - start[0]) * local)
        g = int(start[1] + (end[1] - start[1]) * local)
        b = int(start[2] + (end[2] - start[2]) * local)
        draw.line([(0, i), (width, i)], fill=(r, g, b))


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
               fill: Tuple[int, int, int, int] = (255, 255, 255, 255)) -> Tuple[int, int]:
    draw.text(position, text, font=font, fill=fill)
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_metric_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int], title: str,
                      value: str, accent: Tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(bbox, radius=32, fill=(255, 255, 255, 25), outline=accent, width=3)
    title_font = _get_font(36)
    value_font = _get_font(64, "bold")
    x1, y1, x2, y2 = bbox
    draw.text((x1 + 32, y1 + 28), title, font=title_font, fill=(255, 255, 255, 220))
    bbox_value = value_font.getbbox(value)
    value_height = bbox_value[3] - bbox_value[1]
    draw.text((x1 + 32, y2 - value_height - 40), value, font=value_font, fill=accent)


def _draw_hydration_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int],
                         value: float, accent: Tuple[int, int, int, int]) -> None:
    _draw_metric_card(draw, bbox, TEXTOS_FIXOS["card_hidratacao"], f"{value:.0f}", accent)
    x1, y1, x2, y2 = bbox
    bar_height = 24
    bar_margin = 40
    bar_y = y2 - bar_height - 48
    fill_width = (x2 - x1 - 2 * bar_margin) * max(0.0, min(value, 100.0)) / 100.0
    draw.rounded_rectangle(
        (x1 + bar_margin, bar_y, x2 - bar_margin, bar_y + bar_height),
        radius=12,
        outline=(255, 255, 255, 120),
        fill=(255, 255, 255, 15),
    )
    draw.rounded_rectangle(
        (x1 + bar_margin, bar_y, x1 + bar_margin + fill_width, bar_y + bar_height),
        radius=12,
        fill=accent,
    )


def _draw_radar(draw: ImageDraw.ImageDraw, center: Tuple[int, int], radius: int,
                values: Sequence[float], labels: Sequence[str], accent: Tuple[int, int, int, int]) -> None:
    cx, cy = center
    axes = len(values)
    outline = (255, 255, 255, 90)
    for level in range(1, 4):
        points = []
        for i in range(axes):
            angle = math.pi / 2 + (2 * math.pi * i / axes)
            r = radius * (level / 4)
            x = cx + r * math.cos(angle)
            y = cy - r * math.sin(angle)
            points.append((x, y))
        draw.polygon(points, outline=outline)

    data_points = []
    for idx, value in enumerate(values):
        angle = math.pi / 2 + (2 * math.pi * idx / axes)
        x = cx + radius * value * math.cos(angle)
        y = cy - radius * value * math.sin(angle)
        data_points.append((x, y))
    draw.polygon(data_points, fill=(accent[0], accent[1], accent[2], 90), outline=accent)

    label_font = _get_font(28)
    for idx, label in enumerate(labels):
        angle = math.pi / 2 + (2 * math.pi * idx / axes)
        x = cx + (radius + 30) * math.cos(angle)
        y = cy - (radius + 30) * math.sin(angle)
        draw.text((x - 20, y - 10), label, font=label_font, fill=(255, 255, 255, 200))


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
                    max_items: int | None = None) -> None:
    draw.rounded_rectangle(bbox, radius=36, fill=(5, 5, 20, 120), outline=accent, width=3)
    x1, y1, x2, _ = bbox
    title_font = _get_font(40, "bold")
    text_font = _get_font(32)
    draw.text((x1 + 32, y1 + 32), title, font=title_font, fill=accent)
    offset = y1 + 110
    bullet = "•"
    count = 0
    for text in items:
        if max_items is not None and count >= max_items:
            break
        wrapped = _wrap_text(text, text_font, x2 - x1 - 90)
        for line in wrapped:
            draw.text((x1 + 48, offset), f"{bullet} {line}", font=text_font, fill=(255, 255, 255, 230))
            offset += 44
        count += 1


def _draw_insight_card(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int],
                       insight: str, accent: Tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(bbox, radius=36, fill=(5, 5, 20, 140), outline=accent, width=3)
    x1, y1, x2, y2 = bbox
    title_font = _get_font(40, "bold")
    text_font = _get_font(34)
    draw.text((x1 + 32, y1 + 32), TEXTOS_FIXOS["card_insight"], font=title_font, fill=accent)
    insight_lines = _wrap_text(insight, text_font, x2 - x1 - 80)
    offset = y1 + 120
    for line in insight_lines:
        draw.text((x1 + 32, offset), line, font=text_font, fill=(255, 255, 255, 230))
        offset += 46
    footer_font = _get_font(28)
    draw.text((x1 + 32, y2 - 60), TEXTOS_FIXOS["card_rodape"], font=footer_font, fill=(255, 255, 255, 180))


def _compose_story(image: Image.Image, data: ShareImagePayload, accent: Tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size

    _draw_placeholder_logo(draw, (80, 60, 260, 220))
    header_font = _get_font(32)
    draw.text((width - 540, 120), TEXTOS_FIXOS["header_subtitle"], font=header_font, fill=(255, 255, 255, 200))

    name_font = _get_font(82, "bold")
    subtitle_font = _get_font(48)
    draw.text((80, 260), f"{data.primeiro_nome}, {data.idade}", font=name_font, fill=(255, 255, 255, 255))
    draw.text((80, 360), f"{data.signo} • {data.elemento}", font=subtitle_font, fill=(255, 255, 255, 220))

    card_width = 300
    card_height = 220
    top = 420
    gap = 40
    card_positions = [
        (80, top, 80 + card_width, top + card_height),
        (80 + card_width + gap, top, 80 + 2 * card_width + gap, top + card_height),
        (80 + 2 * (card_width + gap), top, 80 + 3 * card_width + 2 * gap, top + card_height),
    ]
    _draw_metric_card(draw, card_positions[0], TEXTOS_FIXOS["card_imc"], f"{data.imc:.1f}", accent)
    _draw_metric_card(draw, card_positions[1], TEXTOS_FIXOS["card_score"], f"{data.score_geral:.0f}", accent)
    _draw_hydration_card(draw, card_positions[2], data.hidratacao_score, accent)

    normalized, labels = _normalize_values(data)
    _draw_radar(draw, (width // 2, 930), 230, normalized, labels, accent)

    _draw_list_card(draw, (80, 1180, width - 80, 1450), TEXTOS_FIXOS["card_comportamentos"], data.comportamentos, accent)
    _draw_insight_card(draw, (80, 1480, width - 80, 1740), data.insight_frase, accent)

    footer_font = _get_font(28)
    draw.text((80, height - 100), TEXTOS_FIXOS["footer"], font=footer_font, fill=(255, 255, 255, 160))


def _compose_feed(image: Image.Image, data: ShareImagePayload, accent: Tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size

    _draw_placeholder_logo(draw, (60, 50, 180, 170))
    header_font = _get_font(28)
    draw.text((width - 480, 80), TEXTOS_FIXOS["header_subtitle"], font=header_font, fill=(255, 255, 255, 200))

    name_font = _get_font(64, "bold")
    subtitle_font = _get_font(38)
    draw.text((60, 200), f"{data.primeiro_nome}, {data.idade}", font=name_font, fill=(255, 255, 255, 255))
    draw.text((60, 270), f"{data.signo} • {data.elemento}", font=subtitle_font, fill=(255, 255, 255, 220))

    card_width = 420
    card_height = 200
    gap = 40
    _draw_metric_card(draw, (60, 320, 60 + card_width, 320 + card_height), TEXTOS_FIXOS["card_imc"], f"{data.imc:.1f}", accent)
    _draw_metric_card(draw, (60 + card_width + gap, 320, 60 + 2 * card_width + gap, 320 + card_height), TEXTOS_FIXOS["card_score"], f"{data.score_geral:.0f}", accent)
    _draw_hydration_card(draw, (60, 560, width - 60, 560 + card_height), data.hidratacao_score, accent)

    normalized, labels = _normalize_values(data)
    _draw_radar(draw, (width // 2, 720), 150, normalized, labels, accent)

    _draw_list_card(
        draw,
        (60, 880, width - 60, 960),
        TEXTOS_FIXOS["card_comportamentos"],
        data.comportamentos,
        accent,
        max_items=2,
    )
    _draw_insight_card(draw, (60, 980, width - 60, height - 60), data.insight_frase, accent)


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
    _apply_vertical_gradient(image, BACKGROUND_GRADIENT)

    accent_hex = ACCENT_COLORS[payload.elemento]["accent"]
    accent_color = _hex_to_rgba(accent_hex, 220)

    if formato == "story":
        _compose_story(image, payload, accent_color)
    else:
        _compose_feed(image, payload, accent_color)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
