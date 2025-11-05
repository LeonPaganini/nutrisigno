"""Carregadores auxiliares para os dados de substituições alimentares."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _default_subs_path() -> Path:
    """Retorna o caminho padrão para ``substituicoes.json``.

    Assim como em ``diet_loader``, utilizamos :data:`DATA_DIR` para apontar
    para o diretório ``data`` localizado imediatamente acima do pacote.
    """
    return DATA_DIR / "substituicoes.json"


def load_substitutions(subs_path: str | Path | None = None) -> Dict[str, Any]:
    """Carrega os dados de substituições alimentares."""

    if subs_path is None:
        subs_path = _default_subs_path()

    subs_path = Path(subs_path)
    with subs_path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


__all__ = ["load_substitutions"]
