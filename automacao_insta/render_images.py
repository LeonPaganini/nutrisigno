"""Render post images using Pillow."""
from __future__ import annotations

import logging
import random
import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .config import AppConfig, ImageConfig, load_config
from .db import PostStatus, get_posts_by_status, update_post_status

LOGGER = logging.getLogger(__name__)


def _load_font(fonts_dir: Path, font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Tenta carregar a fonte customizada com fallback seguro."""

    candidates = [fonts_dir / font_name, Path(__file__).resolve().parent / "assets" / "fonts" / font_name]
    for font_path in candidates:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)

    LOGGER.warning("Font %s not found in %s, using default", font_name, candidates)
    return ImageFont.load_default()


def _create_background(cfg: ImageConfig) -> Image.Image:
    img = Image.new("RGBA", (cfg.width, cfg.height), cfg.palette_background)
    draw = ImageDraw.Draw(img)

    for _ in range(6):
        ellipse_width = random.randint(int(cfg.width * 0.3), int(cfg.width * 0.7))
        ellipse_height = random.randint(int(cfg.height * 0.3), int(cfg.height * 0.6))
        x0 = random.randint(-int(cfg.width * 0.2), int(cfg.width * 0.6))
        y0 = random.randint(-int(cfg.height * 0.2), int(cfg.height * 0.6))
        x1 = x0 + ellipse_width
        y1 = y0 + ellipse_height
        color = random.choice([cfg.palette_primary, cfg.palette_accent_light, cfg.palette_accent_dark])
        alpha = random.randint(60, 120)
        draw.ellipse([x0, y0, x1, y1], fill=_add_alpha(color, alpha))

    return img.convert("RGB")


def _add_alpha(hex_color: str, alpha: int) -> tuple:
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def _draw_text(img: Image.Image, text: str, cfg: ImageConfig, fonts_dir: Path) -> None:
    draw = ImageDraw.Draw(img)
    font_size = 56
    font = _load_font(fonts_dir, cfg.font_primary, font_size)
    max_width = cfg.width - 2 * cfg.margin

    wrapped = textwrap.fill(text, width=28)
    text_width, text_height = _measure_multiline_text(draw, wrapped, font=font, spacing=10)

    x = (cfg.width - text_width) / 2
    y = (cfg.height - text_height) / 2

    draw.multiline_text((x, y), wrapped, font=font, fill=cfg.palette_primary, spacing=10, align="center")


def _measure_multiline_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, spacing: int) -> tuple[int, int]:
    """Calcula tamanho de texto multilinha compatível com Pillow 10+."""

    if hasattr(draw, "multiline_textbbox"):
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    lines = text.splitlines() or [""]
    widths = []
    heights = []

    for line in lines:
        # getbbox oferece suporte nas versões antigas; fallback para getsize se necessário
        if hasattr(font, "getbbox"):
            bbox = font.getbbox(line or " ")
            width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        else:
            width, height = font.getsize(line or " ")  # type: ignore[attr-defined]
        widths.append(width)
        heights.append(height)

    total_height = sum(heights) + spacing * (len(lines) - 1 if len(lines) > 1 else 0)
    return (max(widths) if widths else 0, total_height)


def _apply_logo(img: Image.Image, logo_path: Path, cfg: ImageConfig) -> None:
    if not logo_path.exists():
        LOGGER.warning("Logo not found at %s", logo_path)
        return

    logo = Image.open(logo_path).convert("RGBA")
    max_logo_width = int(cfg.width * 0.18)
    ratio = max_logo_width / logo.width
    logo = logo.resize((max_logo_width, int(logo.height * ratio)))

    position = (cfg.width - logo.width - cfg.margin, cfg.height - logo.height - int(cfg.margin * 0.6))
    img.paste(logo, position, logo)


def render_post_image(post: dict, config: Optional[AppConfig] = None) -> str:
    cfg = config or load_config()
    image_cfg = cfg.images

    canvas = _create_background(image_cfg)
    _draw_text(canvas, post.get("texto_imagem", ""), image_cfg, cfg.paths.fonts_dir)
    _apply_logo(canvas, cfg.paths.logo_path, image_cfg)

    output_path = cfg.paths.renders_dir / f"post_{post['id']}.png"
    canvas.save(output_path)

    update_post_status(post["id"], PostStatus.RENDERIZADO, config=cfg, imagem_path=str(output_path))
    LOGGER.info("Rendered image for post %s", post["id"])
    return str(output_path)


def render_all_validated_posts(limit: int = 10, config: Optional[AppConfig] = None) -> None:
    cfg = config or load_config()
    posts = get_posts_by_status(PostStatus.VALIDADO, limit=limit, config=cfg)

    if not posts:
        LOGGER.info("No validated posts to render")
        return

    for post in posts:
        try:
            render_post_image(post, config=cfg)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Failed to render post %s: %s", post.get("id"), exc)
            update_post_status(post["id"], PostStatus.ERRO, config=cfg)


if __name__ == "__main__":
    render_all_validated_posts()
