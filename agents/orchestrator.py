"""Orquestrador do pré-pagamento.

Esta etapa é 100% determinística e usa apenas cálculos locais e os
arquivos estáticos ``dietas_index.json`` e ``substituicoes.json``. Nenhuma
chamada de IA é feita aqui: o resultado é um "pré-plano" pronto para ser
persistido e exibido no dashboard antes do pagamento.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from . import diet_loader


ACTIVITY_FACTORS = {
    "sedentário": 1.2,
    "sedentario": 1.2,
    "leve": 1.375,
    "moderado": 1.55,
    "alto": 1.725,
    "atleta": 1.9,
}

GOAL_ADJUSTMENTS = {
    "manutenção": 1.0,
    "manutencao": 1.0,
    "perda de gordura": 0.85,
    "ganho de massa": 1.1,
}


@dataclass(frozen=True)
class MacroTargets:
    kcal: int
    carbo_g: float
    proteina_g: float
    gordura_g: float
    fibra_g: float


def _calcular_tmb(sexo: str, idade: int, altura_cm: float, peso_kg: float) -> float:
    """Calcula TMB usando Mifflin-St Jeor."""

    sexo_norm = (sexo or "").strip().lower()
    if sexo_norm.startswith("m"):
        return 10 * peso_kg + 6.25 * altura_cm - 5 * idade + 5
    return 10 * peso_kg + 6.25 * altura_cm - 5 * idade - 161


def _fator_atividade(nivel_atividade: str) -> float:
    nivel_norm = (nivel_atividade or "").strip().lower()
    return ACTIVITY_FACTORS.get(nivel_norm, 1.2)


def _ajuste_objetivo(objetivo: str) -> float:
    objetivo_norm = (objetivo or "").strip().lower()
    return GOAL_ADJUSTMENTS.get(objetivo_norm, 1.0)


def calcular_meta_calorica(dados_usuario: Dict[str, Any]) -> int:
    """Calcula a meta calórica diária (kcal)."""

    try:
        tmb = _calcular_tmb(
            dados_usuario["sexo"],
            int(dados_usuario["idade"]),
            float(dados_usuario["altura_cm"]),
            float(dados_usuario["peso_kg"]),
        )
    except KeyError as exc:  # pragma: no cover - validação defensiva
        raise ValueError(f"Campo obrigatório ausente para cálculo calórico: {exc}") from exc

    fator = _fator_atividade(dados_usuario.get("nivel_atividade"))
    ajuste = _ajuste_objetivo(dados_usuario.get("objetivo"))

    return int(round(tmb * fator * ajuste))


def calcular_macros(peso_kg: float, meta_kcal: int) -> MacroTargets:
    """Define metas de macros determinísticas.

    - Proteína: 1.6 g/kg
    - Gordura: 0.8 g/kg
    - Carboidrato: calorias restantes
    - Fibra: meta fixa de 25 g
    """

    proteina_g = round(1.6 * peso_kg, 1)
    gordura_g = round(0.8 * peso_kg, 1)

    kcal_proteina = proteina_g * 4
    kcal_gordura = gordura_g * 9
    carbo_kcal = max(meta_kcal - kcal_proteina - kcal_gordura, 0)
    carbo_g = round(carbo_kcal / 4, 1)

    return MacroTargets(
        kcal=int(meta_kcal),
        carbo_g=carbo_g,
        proteina_g=proteina_g,
        gordura_g=gordura_g,
        fibra_g=25.0,
    )


def gerar_plano_pre_pagamento(dados_usuario: Dict[str, Any]) -> Dict[str, Any]:
    """Gera o payload completo do pré-plano.

    O resultado deve ser persistido pelo repositório com status
    "aguardando_pagamento" e utilizado pelo dashboard e PDF pré-pagamento.
    """

    meta_kcal = calcular_meta_calorica(dados_usuario)
    macros = calcular_macros(float(dados_usuario.get("peso_kg", 0)), meta_kcal)

    dieta_pdf_kcal, dieta_entry = diet_loader.get_diet(meta_kcal)
    porcoes_por_refeicao = dict(dieta_entry.refeicoes_por_porcoes)
    dieta_pdf_arquivo = diet_loader.get_pdf_filename(meta_kcal)[1]

    return {
        "dados_usuario": dados_usuario,
        "macros": {
            "kcal": macros.kcal,
            "carbo_g": macros.carbo_g,
            "proteina_g": macros.proteina_g,
            "gordura_g": macros.gordura_g,
            "fibra_g": macros.fibra_g,
        },
        "dieta_pdf_kcal": dieta_pdf_kcal,
        "dieta_pdf_arquivo": dieta_pdf_arquivo,
        "porcoes_por_refeicao": porcoes_por_refeicao,
        "cardapio_ia": None,
        "status": "aguardando_pagamento",
    }


__all__ = [
    "MacroTargets",
    "calcular_meta_calorica",
    "calcular_macros",
    "gerar_plano_pre_pagamento",
]
