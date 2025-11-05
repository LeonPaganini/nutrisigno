"""Utilitários para carregar dietas do diretório de dados.

Este módulo fornece funções convenientes para carregar o arquivo
``dietas_index.json`` distribuído com o projeto. As funções aceitam
um caminho personalizado, mas por padrão localizam o arquivo dentro do
subdiretório ``data`` do repositório ``nutrisigno-main``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _default_data_path() -> Path:
    """Retorna o caminho padrão para ``dietas_index.json``.

    O caminho base é calculado apenas uma vez em :data:`DATA_DIR`, que
    representa o diretório ``data`` localizado imediatamente acima do
    pacote ``agents``.
    """
    return DATA_DIR / "dietas_index.json"


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

    data_path = Path(data_path)
    with data_path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


__all__ = ["load_diets"]
