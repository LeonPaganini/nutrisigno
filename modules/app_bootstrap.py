# modules/app_bootstrap.py
from __future__ import annotations

import os
import pathlib
import logging

from .repo import init_models

log = logging.getLogger(__name__)

def ensure_bootstrap() -> tuple[bool, str]:
    out_dir = os.getenv("OUTPUT_DIR", "outputs")
    try:
        pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:  # pragma: no cover - log + retorno
        log.exception("Falha ao criar outputs")
        return False, f"Falha ao criar '{out_dir}': {e}"
    try:
        init_models()
        db_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
        return True, f"Bootstrap OK · DB={db_url} · OUTPUT_DIR={out_dir}"
    except Exception as e:  # pragma: no cover - log + retorno
        log.exception("Falha ao inicializar DB")
        return False, f"Falha ao inicializar DB: {e}"
