"""Utilitários para carregar dietas do diretório de dados.

Este módulo fornece funções convenientes para carregar o arquivo
``dietas_index.json`` distribuído com o projeto. As funções aceitam
um caminho personalizado, mas por padrão localizam o arquivo dentro do
subdiretório ``data`` do projeto ``nutrisigno``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Conjunto de kcal suportadas pelos planos estáticos (1000–2000).
SUPPORTED_KCALS = tuple(range(1000, 2001, 100))


class DietCatalogError(RuntimeError):
    """Erros controlados relacionados ao carregamento do catálogo de dietas."""


@dataclass(frozen=True)
class DietEntry:
    """Representa uma dieta base carregada a partir do JSON."""

    kcal: int
    arquivo: str
    refeicoes_por_porcoes: Mapping[str, Mapping[str, str]]


def _default_data_path() -> Path:
    """Retorna o caminho padrão para ``dietas_index.json``.

    O caminho base é calculado apenas uma vez em :data:`DATA_DIR`, que
    representa o diretório ``data`` localizado imediatamente acima do
    pacote ``agents``.
    """

    return DATA_DIR / "dietas_index.json"


def _load_json(data_path: Path) -> Dict[str, Any]:
    if not data_path.exists():
        raise FileNotFoundError(
            f"Arquivo de dietas não encontrado em '{data_path}'. Verifique a pasta data/."
        )

    with data_path.open("r", encoding="utf-8") as fp:
        try:
            return json.load(fp)
        except json.JSONDecodeError as exc:  # pragma: no cover - proteção
            raise DietCatalogError(f"dietas_index.json inválido: {exc}") from exc


def load_diets(data_path: str | Path | None = None) -> Dict[str, Any]:
    """Carrega os dados de dietas a partir de ``dietas_index.json``.

    Parameters
    ----------
    data_path:
        Caminho opcional para o arquivo JSON. Quando ``None``, o caminho
        padrão retornado por :func:`_default_data_path` é utilizado.

    Returns
    -------
    dict
        O conteúdo do arquivo JSON carregado como um dicionário Python.
    """

    if data_path is None:
        data_path = _default_data_path()

    return _load_json(Path(data_path))


def load_catalog(data_path: str | Path | None = None) -> Dict[int, DietEntry]:
    """Retorna um catálogo indexado por kcal.

    O JSON original armazena uma lista em ``dietas``. Esta função
    transforma em um dicionário {kcal: DietEntry} para consultas rápidas.
    """

    raw = load_diets(data_path)
    catalog: Dict[int, DietEntry] = {}
    for item in raw.get("dietas", []):
        try:
            kcal = int(item["kcal"])
        except Exception as exc:  # pragma: no cover - sanitização defensiva
            raise DietCatalogError(f"Item de dieta sem kcal numérica: {item}") from exc

        catalog[kcal] = DietEntry(
            kcal=kcal,
            arquivo=str(item.get("arquivo") or ""),
            refeicoes_por_porcoes=dict(item.get("refeicoes_por_porcoes", {})),
        )

    if not catalog:
        raise DietCatalogError("Nenhuma dieta encontrada em dietas_index.json.")

    return catalog


def select_kcal_alvo(target_kcal: float | int) -> int:
    """Seleciona a kcal suportada mais próxima dentro do range 1000–2000.

    - Valores abaixo de 1000 → 1000.
    - Valores acima de 2000 → 2000.
    - Demais → aproximação pelo valor mais próximo em :data:`SUPPORTED_KCALS`.
    """

    if target_kcal is None:
        raise ValueError("target_kcal é obrigatório para seleção de dieta.")

    # Limita extremos
    clamped = min(max(float(target_kcal), min(SUPPORTED_KCALS)), max(SUPPORTED_KCALS))
    return int(min(SUPPORTED_KCALS, key=lambda x: abs(x - clamped)))


def get_diet(kcal_estimado: float | int, *, data_path: str | Path | None = None) -> Tuple[int, DietEntry]:
    """Obtém a dieta mais próxima do alvo calórico.

    Retorna uma tupla ``(kcal_escolhido, DietEntry)`` com a dieta já
    normalizada. Erros são lançados com mensagens claras para facilitar
    o diagnóstico em produção.
    """

    catalog = load_catalog(data_path)
    kcal_alvo = select_kcal_alvo(kcal_estimado)

    if kcal_alvo not in catalog:
        # fallback para o valor mais próximo disponível no arquivo
        kcal_alvo = int(min(catalog.keys(), key=lambda x: abs(x - kcal_alvo)))

    return kcal_alvo, catalog[kcal_alvo]


def get_portions_by_meal(kcal_estimado: float | int, *, data_path: str | Path | None = None) -> Dict[str, Dict[str, str]]:
    """Retorna a matriz de porções por refeição para a kcal mais próxima."""

    _, diet = get_diet(kcal_estimado, data_path=data_path)
    return dict(diet.refeicoes_por_porcoes)


def get_pdf_filename(kcal_estimado: float | int, *, data_path: str | Path | None = None) -> Tuple[int, str]:
    """Retorna ``(kcal_base, nome_pdf)`` para a kcal mais próxima."""

    kcal_base, diet = get_diet(kcal_estimado, data_path=data_path)
    pdf = diet.arquivo
    if pdf and not Path(pdf).is_absolute():
        pdf = str(DATA_DIR / pdf)
    return kcal_base, pdf


__all__ = [
    "SUPPORTED_KCALS",
    "DietCatalogError",
    "DietEntry",
    "load_diets",
    "load_catalog",
    "select_kcal_alvo",
    "get_diet",
    "get_portions_by_meal",
    "get_pdf_filename",
]
