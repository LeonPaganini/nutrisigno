"""Validation agent for NutriSigno posts."""
from __future__ import annotations

import logging
import re
from typing import Optional

from .config import AppConfig, load_config
from .db import PostStatus, get_posts_by_status, update_post_status

LOGGER = logging.getLogger(__name__)

PROHIBITED_WORDS = [
    r"cura",
    r"milagre",
    r"perder \d+kg",
    r"resultado garantido",
    r"detox de \d+",
]
MAX_IMAGE_TEXT_LENGTH = 220
MAX_CAPTION_LENGTH = 2200


def _remove_prohibited(text: str) -> str:
    sanitized = text
    for pattern in PROHIBITED_WORDS:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    return sanitized.strip()


def _enforce_length(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    LOGGER.debug("Text truncated from %s to %s chars", len(text), max_len)
    return text[:max_len].rstrip()


def validate_post(post: dict) -> dict:
    """Validate and adjust a post's text fields."""

    texto_imagem = _remove_prohibited(post.get("texto_imagem", ""))
    legenda = _remove_prohibited(post.get("legenda", ""))
    hashtags = post.get("hashtags", "")

    texto_imagem = _enforce_length(texto_imagem, MAX_IMAGE_TEXT_LENGTH)
    legenda = _enforce_length(legenda, MAX_CAPTION_LENGTH)

    if not texto_imagem or not legenda:
        return {"status": PostStatus.ERRO, "motivo": "conteudo_vazio"}

    if "promessa" in legenda.lower():
        legenda = legenda.replace("promessa", "orientação")

    if hashtags and not hashtags.startswith("#"):
        hashtags = "#" + hashtags

    return {
        "status": PostStatus.VALIDADO,
        "texto_imagem": texto_imagem,
        "legenda": legenda,
        "hashtags": hashtags,
    }


def validate_all_pending_posts(config: Optional[AppConfig] = None) -> None:
    """Validate all posts waiting for approval."""

    cfg = config or load_config()
    pending = get_posts_by_status(PostStatus.PARA_VALIDAR, limit=100, config=cfg)

    if not pending:
        LOGGER.info("No posts awaiting validation")
        return

    for post in pending:
        try:
            result = validate_post(post)
            if result.get("status") == PostStatus.VALIDADO:
                update_post_status(
                    post["id"],
                    PostStatus.VALIDADO,
                    config=cfg,
                    texto_imagem=result.get("texto_imagem", post.get("texto_imagem")),
                    legenda=result.get("legenda", post.get("legenda")),
                    hashtags=result.get("hashtags", post.get("hashtags")),
                )
                LOGGER.info("Validated post %s", post["id"])
            else:
                update_post_status(post["id"], PostStatus.ERRO, config=cfg)
                LOGGER.warning("Post %s marked as error: %s", post["id"], result.get("motivo"))
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Validation failed for post %s: %s", post.get("id"), exc)
            update_post_status(post["id"], PostStatus.ERRO, config=cfg)


if __name__ == "__main__":
    validate_all_pending_posts()
