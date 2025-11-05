"""Coleção de utilitários para carregar dados auxiliares do projeto."""

from .diet_loader import load_diets
from .subs_loader import load_substitutions

__all__ = ["load_diets", "load_substitutions"]
