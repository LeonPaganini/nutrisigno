"""Generate editorial calendar entries for NutriSigno."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Iterable, Optional

from .config import AppConfig, load_config
from .db import PostStatus, bulk_insert_posts, init_db

LOGGER = logging.getLogger(__name__)

POST_TYPES = [
    "frase_unica",
    "carrossel_signo",
    "carrossel_tema",
    "educativo",
    "previsao_semanal",
    "motivacional",
]

SIGNOS = [
    "Áries",
    "Touro",
    "Gêmeos",
    "Câncer",
    "Leão",
    "Virgem",
    "Libra",
    "Escorpião",
    "Sagitário",
    "Capricórnio",
    "Aquário",
    "Peixes",
]

TEMAS = ["ansiedade", "foco", "hidratação", "compulsão", "energia", "sono"]


def _rotate(values: Iterable[str]) -> list[str]:
    """Return rotated list to ensure balance."""

    return list(values)


def _build_entry(target_date: date, tipo_post: str, signo: Optional[str], tema: Optional[str]) -> dict:
    """Compose a calendar entry placeholder."""

    return {
        "tipo_post": tipo_post,
        "signo": signo,
        "tema": tema,
        "texto_imagem": "",
        "legenda": "",
        "hashtags": "",
        "status": PostStatus.RASCUNHO,
        "data_publicacao_planejada": target_date.isoformat(),
    }


def generate_calendar(dias: int, start_date: Optional[date] = None) -> list[dict]:
    """Generate a balanced calendar for the next N days."""

    today = start_date or date.today()
    entries: list[dict] = []
    tipos_rotated = _rotate(POST_TYPES)
    signo_index = 0
    tema_index = 0

    for i in range(dias):
        target = today + timedelta(days=i)
        tipo_post = tipos_rotated[i % len(tipos_rotated)]

        signo = None
        tema = None
        if tipo_post in {"carrossel_signo", "previsao_semanal"}:
            signo = SIGNOS[signo_index % len(SIGNOS)]
            signo_index += 1
        if tipo_post in {"carrossel_tema", "educativo", "motivacional"}:
            tema = TEMAS[tema_index % len(TEMAS)]
            tema_index += 1

        entries.append(_build_entry(target, tipo_post, signo, tema))

    LOGGER.info("Generated %s calendar entries", len(entries))
    return entries


def persist_calendar(entries: list[dict], config: Optional[AppConfig] = None) -> list[int]:
    """Persist generated entries as drafts in the database."""

    cfg = config or load_config()
    init_db(cfg)
    ids = bulk_insert_posts(entries, config=cfg)
    LOGGER.info("Persisted %s calendar entries", len(ids))
    return ids


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate editorial calendar drafts.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to generate")
    args = parser.parse_args()

    config = load_config()
    calendar_entries = generate_calendar(args.days)
    persist_calendar(calendar_entries, config)
    LOGGER.info("Calendar generation completed")
