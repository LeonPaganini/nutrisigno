"""Carregadores auxiliares para os dados de substituições alimentares."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class SubstitutionCatalogError(RuntimeError):
    """Erros controlados relacionados ao catálogo de substituições."""


@dataclass(frozen=True)
class SubstitutionCategory:
    """Categoria de substituição contendo itens equivalentes a 1 porção."""

    nome: str
    descricao: str
    itens: List[str]


def _default_subs_path() -> Path:
    """Retorna o caminho padrão para ``substituicoes.json``.

    Assim como em ``diet_loader``, utilizamos :data:`DATA_DIR` para apontar
    para o diretório ``data`` localizado imediatamente acima do pacote.
    """

    return DATA_DIR / "substituicoes.json"


def _load_json(subs_path: Path) -> Dict[str, Any]:
    if not subs_path.exists():
        raise FileNotFoundError(
            f"Arquivo de substituições não encontrado em '{subs_path}'."
        )

    with subs_path.open("r", encoding="utf-8") as fp:
        try:
            return json.load(fp)
        except json.JSONDecodeError as exc:  # pragma: no cover - proteção
            raise SubstitutionCatalogError(f"substituicoes.json inválido: {exc}") from exc


def load_substitutions(subs_path: str | Path | None = None) -> Dict[str, Any]:
    """Carrega os dados crus de substituições alimentares."""

    if subs_path is None:
        subs_path = _default_subs_path()

    return _load_json(Path(subs_path))


def load_catalog(subs_path: str | Path | None = None) -> Mapping[str, SubstitutionCategory]:
    """Normaliza o catálogo em um dicionário amigável.

    As chaves retornadas preservam o nome original das categorias no JSON.
    """

    raw = load_substitutions(subs_path)
    categorias_raw = raw.get("categorias") or {}
    catalog: Dict[str, SubstitutionCategory] = {}

    for nome_categoria, payload in categorias_raw.items():
        itens = payload.get("itens") or []
        itens_txt = [item.get("nome") if isinstance(item, dict) else str(item) for item in itens]
        catalog[nome_categoria] = SubstitutionCategory(
            nome=nome_categoria,
            descricao=payload.get("descricao", ""),
            itens=itens_txt,
        )

    if not catalog:
        raise SubstitutionCatalogError("Nenhuma categoria encontrada em substituicoes.json.")

    return catalog


def list_categories(subs_path: str | Path | None = None) -> List[str]:
    """Retorna a lista de categorias disponíveis."""

    return list(load_catalog(subs_path).keys())


def get_items_for_category(category: str, subs_path: str | Path | None = None) -> List[str]:
    """Retorna as opções equivalentes (1 porção) de uma categoria."""

    catalog = load_catalog(subs_path)
    if category not in catalog:
        raise KeyError(f"Categoria de substituição não encontrada: {category}")
    return catalog[category].itens


__all__ = [
    "SubstitutionCatalogError",
    "SubstitutionCategory",
    "load_substitutions",
    "load_catalog",
    "list_categories",
    "get_items_for_category",
]
