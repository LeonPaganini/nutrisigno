"""Coleção de utilitários para carregar dados auxiliares do projeto."""

from .diet_loader import (
    DietCatalogError,
    DietEntry,
    SUPPORTED_KCALS,
    get_diet,
    get_pdf_filename,
    get_portions_by_meal,
    load_catalog as load_diet_catalog,
    load_diets,
    select_kcal_alvo,
)
from .orchestrator import (
    MacroTargets,
    calcular_macros,
    calcular_meta_calorica,
    gerar_plano_pre_pagamento,
)
from .subs_loader import (
    SubstitutionCatalogError,
    SubstitutionCategory,
    get_items_for_category,
    list_categories,
    load_catalog as load_substitution_catalog,
    load_substitutions,
)

__all__ = [
    # Dietas
    "DietCatalogError",
    "DietEntry",
    "SUPPORTED_KCALS",
    "get_diet",
    "get_pdf_filename",
    "get_portions_by_meal",
    "load_diet_catalog",
    "load_diets",
    "select_kcal_alvo",
    # Orquestrador
    "MacroTargets",
    "calcular_macros",
    "calcular_meta_calorica",
    "gerar_plano_pre_pagamento",
    # Substituições
    "SubstitutionCatalogError",
    "SubstitutionCategory",
    "get_items_for_category",
    "list_categories",
    "load_substitution_catalog",
    "load_substitutions",
]
