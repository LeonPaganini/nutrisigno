"""NutriSigno health pillars scoring engine.

This module centralizes the configuration required to transform form answers
into normalized scores (0–100) for the six health pillars requested by the
product team: Energia, Digestao, Sono, Hidratacao, Emocao and Rotina.

All the logic is driven by data structures (question catalog, pillar config
and rule definitions). New pillars, questions or adjustments can be added by
editing these dictionaries without touching the scoring code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_SCORE = 50.0


def _likert_mapping(options: List[str]) -> Dict[str, int]:
    """Generate a mapping between likert text answers and scores.

    The first option is mapped to 0, the last to 100, and the rest are evenly
    distributed in between. The keys are stored in lowercase to allow
    case-insensitive matching during normalization.
    """

    step = 100 / (len(options) - 1) if len(options) > 1 else 100
    mapping: Dict[str, int] = {}
    for index, option in enumerate(options):
        mapping[option.casefold()] = round(index * step)
    return mapping


FREQUENCY_5 = [
    "Nunca",
    "Raramente",
    "Às vezes",
    "Frequentemente",
    "Quase sempre",
]

INTENSITY_5 = [
    "Muito baixa",
    "Baixa",
    "Moderada",
    "Alta",
    "Muito alta",
]


QUESTION_CATALOG: Dict[str, Dict[str, Any]] = {
    # Energia / Sono core questions
    "nivel_energia": {
        "text": "Como você avalia seu nível de energia ao longo do dia?",
        "type": "likert",
        "options": INTENSITY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": _likert_mapping(INTENSITY_5),
        },
    },
    "horas_sono": {
        "text": "Quantas horas de sono você costuma ter por noite?",
        "type": "numeric",
        "normalizer": {
            "type": "numeric_range",
            "min_ideal": 7,
            "max_ideal": 8.5,
            "hard_min": 4,
            "hard_max": 11,
        },
    },
    "qualidade_sono": {
        "text": "Como você avalia a qualidade do seu sono?",
        "type": "likert",
        "options": INTENSITY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": _likert_mapping(INTENSITY_5),
        },
    },
    "freq_atividade_fisica": {
        "text": "Com que frequência você pratica atividade física estruturada?",
        "type": "multiple_choice",
        "options": [
            "Nunca",
            "1x por semana",
            "2-3x por semana",
            "4-5x por semana",
            "Diariamente",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 5,
                "1x por semana": 35,
                "2-3x por semana": 70,
                "4-5x por semana": 90,
                "diariamente": 100,
            },
        },
    },
    "nivel_estresse": {
        "text": "Qual o seu nível atual de estresse?",
        "type": "likert",
        "options": INTENSITY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "muito baixa": 100,
                "baixa": 85,
                "moderada": 60,
                "alta": 30,
                "muito alta": 10,
            },
        },
    },
    # Digestao
    "tipo_fezes": {
        "text": "Qual tipo de fezes melhor representa o seu padrão (Escala de Bristol)?",
        "type": "multiple_choice",
        "options": [
            "Tipo 1 (Carocinhos duros)",
            "Tipo 2 (Salsicha grumosa)",
            "Tipo 3 (Salsicha com rachaduras)",
            "Tipo 4 (Salsicha lisa e macia)",
            "Tipo 5 (Pedaços macios)",
            "Tipo 6 (Pedaços fofos)",
            "Tipo 7 (Aquosa)",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "tipo 1 (carocinhos duros)": 15,
                "tipo 2 (salsicha grumosa)": 35,
                "tipo 3 (salsicha com rachaduras)": 80,
                "tipo 4 (salsicha lisa e macia)": 100,
                "tipo 5 (pedaços macios)": 80,
                "tipo 6 (pedaços fofos)": 35,
                "tipo 7 (aquosa)": 10,
                "1": 15,
                "2": 35,
                "3": 80,
                "4": 100,
                "5": 80,
                "6": 35,
                "7": 10,
            },
        },
    },
    "freq_intestino": {
        "text": "Com que frequência você evacua?",
        "type": "multiple_choice",
        "options": [
            "Menos de 3x por semana",
            "3-4x por semana",
            "1x por dia",
            "2x por dia",
            "3 ou mais vezes por dia",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "menos de 3x por semana": 10,
                "3-4x por semana": 45,
                "1x por dia": 90,
                "2x por dia": 100,
                "3 ou mais vezes por dia": 70,
            },
        },
    },
    "freq_inchaco": {
        "text": "Com que frequência você sente inchaço abdominal?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 85,
                "à s vezes": 55,
                "as vezes": 55,
                "frequentemente": 25,
                "quase sempre": 10,
            },
        },
    },
    "freq_gases": {
        "text": "Com que frequência você sente excesso de gases?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 85,
                "à s vezes": 60,
                "as vezes": 60,
                "frequentemente": 30,
                "quase sempre": 10,
            },
        },
    },
    "sensacao_peso_pos_refeicao": {
        "text": "Com que frequência você sente peso ou empachamento após as refeições?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "à s vezes": 55,
                "as vezes": 55,
                "frequentemente": 25,
                "quase sempre": 10,
            },
        },
    },
    # Sono add-ons
    "despertares_noturnos": {
        "text": "Quantas vezes você costuma acordar durante a noite?",
        "type": "numeric",
        "normalizer": {
            "type": "numeric_range",
            "min_ideal": 0,
            "max_ideal": 1,
            "hard_min": 0,
            "hard_max": 6,
        },
    },
    "dificuldade_para_dormir": {
        "text": "Quão difícil é pegar no sono na maioria das noites?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "à s vezes": 55,
                "as vezes": 55,
                "frequentemente": 25,
                "quase sempre": 10,
            },
        },
    },
    "sensacao_ao_acordar": {
        "text": "Como você se sente ao acordar?",
        "type": "likert",
        "options": [
            "Extremamente cansada",
            "Cansada",
            "Neutra",
            "Disposta",
            "Muito disposta",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "extremamente cansada": 5,
                "cansada": 30,
                "neutra": 60,
                "disposta": 85,
                "muito disposta": 100,
            },
        },
    },
    # Hidratacao
    "qtd_copos_agua": {
        "text": "Quantos copos de água você bebe por dia (aprox. 200 ml)?",
        "type": "numeric",
        "normalizer": {
            "type": "numeric_range",
            "min_ideal": 8,
            "max_ideal": 12,
            "hard_min": 2,
            "hard_max": 18,
        },
    },
    "cor_urina": {
        "text": "Qual a cor predominante da sua urina?",
        "type": "multiple_choice",
        "options": [
            "Transparente",
            "Amarelo claro",
            "Amarelo",
            "Âmbar",
            "Muito escura",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "transparente": 95,
                "amarelo claro": 100,
                "amarelo": 70,
                "âmbar": 30,
                "ambar": 30,
                "muito escura": 10,
            },
        },
    },
    "retencao_liquidos": {
        "text": "Com que frequência você percebe retenção de líquidos (inchaço em mãos/pés)?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "à s vezes": 60,
                "as vezes": 60,
                "frequentemente": 35,
                "quase sempre": 15,
            },
        },
    },
    # Emocao
    "fome_emocional": {
        "text": "Com que frequência você come para aliviar emoções (ansiedade, tristeza, estresse)?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "à s vezes": 55,
                "as vezes": 55,
                "frequentemente": 25,
                "quase sempre": 10,
            },
        },
    },
    "compulsao_alimentar": {
        "text": "Com que frequência você sente episódios de compulsão alimentar?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 75,
                "à s vezes": 45,
                "as vezes": 45,
                "frequentemente": 20,
                "quase sempre": 5,
            },
        },
    },
    "culpa_apos_comer": {
        "text": "Com que frequência você sente culpa após comer?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "à s vezes": 55,
                "as vezes": 55,
                "frequentemente": 30,
                "quase sempre": 10,
            },
        },
    },
    # Rotina
    "freq_pular_refeicoes": {
        "text": "Com que frequência você pula refeições?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "à s vezes": 55,
                "as vezes": 55,
                "frequentemente": 30,
                "quase sempre": 10,
            },
        },
    },
    "refeicoes_no_dia": {
        "text": "Quantas refeições completas você costuma fazer por dia?",
        "type": "numeric",
        "normalizer": {
            "type": "numeric_range",
            "min_ideal": 3,
            "max_ideal": 5,
            "hard_min": 1,
            "hard_max": 7,
        },
    },
    "aderencia_plano_alimentar": {
        "text": "Quão aderente você se sente ao seu plano alimentar?",
        "type": "likert",
        "options": [
            "Quase nunca sigo",
            "Sigo menos da metade dos dias",
            "Sigo na maioria dos dias",
            "Sigo quase sempre",
            "Sigo praticamente todos os dias",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "quase nunca sigo": 5,
                "sigo menos da metade dos dias": 30,
                "sigo na maioria dos dias": 70,
                "sigo quase sempre": 90,
                "sigo praticamente todos os dias": 100,
            },
        },
    },
    "variacao_rotina_fim_de_semana": {
        "text": "O quanto sua rotina alimentar muda nos fins de semana?",
        "type": "multiple_choice",
        "options": [
            "Quase não muda",
            "Muda um pouco",
            "Muda bastante",
            "É totalmente diferente",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "quase não muda": 100,
                "quase nao muda": 100,
                "muda um pouco": 75,
                "muda bastante": 35,
                "é totalmente diferente": 15,
                "e totalmente diferente": 15,
            },
        },
    },
}


def _normalize_answer(value: Any, normalizer: Optional[Dict[str, Any]]) -> Optional[float]:
    if normalizer is None:
        return None

    norm_type = normalizer.get("type")
    if value is None:
        return normalizer.get("default")

    if norm_type == "categorical":
        mapping = {k.casefold(): v for k, v in normalizer.get("mapping", {}).items()}
        key = str(value).casefold()
        return mapping.get(key, normalizer.get("default", DEFAULT_SCORE))

    if norm_type == "numeric_range":
        numeric_value = _coerce_float(value)
        if numeric_value is None:
            return normalizer.get("default", DEFAULT_SCORE)
        min_ideal = float(normalizer["min_ideal"])
        max_ideal = float(normalizer["max_ideal"])
        hard_min = float(normalizer.get("hard_min", min_ideal))
        hard_max = float(normalizer.get("hard_max", max_ideal))

        if numeric_value < min_ideal:
            if numeric_value <= hard_min:
                return 0.0
            return 100 * (numeric_value - hard_min) / (min_ideal - hard_min)
        if numeric_value > max_ideal:
            if numeric_value >= hard_max:
                return 0.0
            return 100 * (hard_max - numeric_value) / (hard_max - max_ideal)
        return 100.0

    return normalizer.get("default")


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        candidate = value.replace(",", ".")
        try:
            return float(candidate)
        except ValueError:
            return None
    return None


def _get_question_normalizer(question_id: str) -> Optional[Dict[str, Any]]:
    question = QUESTION_CATALOG.get(question_id)
    return None if question is None else question.get("normalizer")


def _compute_weighted_score(respostas: Dict[str, Any], components: List[Dict[str, Any]]) -> float:
    accumulated = 0.0
    total_weight = 0.0
    for component in components:
        question_id = component["question_id"]
        weight = component["weight"]
        normalizer = component.get("normalizer") or _get_question_normalizer(question_id)
        normalized = _normalize_answer(respostas.get(question_id), normalizer)
        if normalized is None:
            continue
        accumulated += normalized * weight
        total_weight += weight
    if total_weight == 0:
        return DEFAULT_SCORE
    return accumulated / total_weight


def _resolve_condition_value(
    respostas: Dict[str, Any], question_id: str, normalized: bool = False
) -> Optional[float | Any]:
    if normalized:
        normalizer = _get_question_normalizer(question_id)
        return _normalize_answer(respostas.get(question_id), normalizer)
    return respostas.get(question_id)


def _coerce_condition_value(value: Any, operator: str) -> Any:
    if operator in {"lt", "le", "gt", "ge", "between"}:
        return _coerce_float(value)
    return value


def _matches_condition(respostas: Dict[str, Any], condition: Dict[str, Any]) -> bool:
    if "all" in condition:
        return all(_matches_condition(respostas, item) for item in condition["all"])
    if "any" in condition:
        return any(_matches_condition(respostas, item) for item in condition["any"])

    question_id = condition["question"]
    operator = condition.get("operator", "eq")
    use_normalized = condition.get("use_normalized", False)
    raw_value = _resolve_condition_value(respostas, question_id, normalized=use_normalized)
    if raw_value is None:
        return False
    target = condition.get("value")

    if operator in {"lt", "le", "gt", "ge"}:
        numeric_value = _coerce_float(raw_value)
        numeric_target = _coerce_float(target)
        if numeric_value is None or numeric_target is None:
            return False
        if operator == "lt":
            return numeric_value < numeric_target
        if operator == "le":
            return numeric_value <= numeric_target
        if operator == "gt":
            return numeric_value > numeric_target
        if operator == "ge":
            return numeric_value >= numeric_target

    if operator == "between":
        numeric_value = _coerce_float(raw_value)
        if numeric_value is None or not isinstance(target, (list, tuple)) or len(target) != 2:
            return False
        low = _coerce_float(target[0])
        high = _coerce_float(target[1])
        if low is None or high is None:
            return False
        return low <= numeric_value <= high

    if operator == "in":
        if target is None:
            return False
        if isinstance(target, (list, tuple, set)):
            return str(raw_value).casefold() in {str(v).casefold() for v in target}
        return False

    if operator == "not_in":
        if target is None:
            return False
        if isinstance(target, (list, tuple, set)):
            return str(raw_value).casefold() not in {str(v).casefold() for v in target}
        return False

    if operator == "eq":
        return str(raw_value).casefold() == str(target).casefold()

    return False


def _apply_adjustments(
    base_score: float, respostas: Dict[str, Any], adjustments: List[Dict[str, Any]]
) -> float:
    score = base_score
    for adjustment in adjustments:
        if _matches_condition(respostas, adjustment["conditions"]):
            score += adjustment.get("impact", 0)
    return max(0.0, min(100.0, score))


PILLARS_CONFIG: Dict[str, Dict[str, Any]] = {
    "Energia": {
        "components": [
            {"question_id": "nivel_energia", "weight": 0.3},
            {"question_id": "qualidade_sono", "weight": 0.25},
            {"question_id": "horas_sono", "weight": 0.2},
            {"question_id": "freq_atividade_fisica", "weight": 0.15},
            {"question_id": "nivel_estresse", "weight": 0.1},
        ],
        "adjustments": [
            {
                "conditions": {"question": "horas_sono", "operator": "lt", "value": 6},
                "impact": -12,
            },
            {
                "conditions": {"question": "horas_sono", "operator": "lt", "value": 5},
                "impact": -10,
            },
            {
                "conditions": {
                    "question": "nivel_estresse",
                    "operator": "in",
                    "value": ["Alta", "Muito alta"],
                },
                "impact": -12,
            },
            {
                "conditions": {
                    "all": [
                        {
                            "question": "nivel_estresse",
                            "operator": "in",
                            "value": ["Alta", "Muito alta"],
                        },
                        {
                            "question": "freq_atividade_fisica",
                            "operator": "in",
                            "value": ["4-5x por semana", "Diariamente"],
                        },
                    ]
                },
                "impact": 6,
            },
        ],
    },
    "Digestao": {
        "components": [
            {"question_id": "tipo_fezes", "weight": 0.3},
            {"question_id": "freq_intestino", "weight": 0.25},
            {"question_id": "freq_inchaco", "weight": 0.2},
            {"question_id": "freq_gases", "weight": 0.15},
            {"question_id": "sensacao_peso_pos_refeicao", "weight": 0.1},
        ],
        "adjustments": [
            {
                "conditions": {
                    "all": [
                        {"question": "tipo_fezes", "operator": "in", "value": ["Tipo 1", "Tipo 2"]},
                        {"question": "freq_intestino", "operator": "in", "value": ["1x por dia", "2x por dia"]},
                    ]
                },
                "impact": -8,
            },
            {
                "conditions": {
                    "question": "sensacao_peso_pos_refeicao",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -12,
            },
        ],
    },
    "Sono": {
        "components": [
            {"question_id": "horas_sono", "weight": 0.25},
            {"question_id": "qualidade_sono", "weight": 0.25},
            {"question_id": "sensacao_ao_acordar", "weight": 0.2},
            {"question_id": "despertares_noturnos", "weight": 0.15},
            {"question_id": "dificuldade_para_dormir", "weight": 0.15},
        ],
        "adjustments": [
            {
                "conditions": {
                    "all": [
                        {"question": "horas_sono", "operator": "between", "value": [7, 9]},
                        {
                            "question": "despertares_noturnos",
                            "operator": "gt",
                            "value": 2,
                        },
                    ]
                },
                "impact": -8,
            },
            {
                "conditions": {
                    "question": "dificuldade_para_dormir",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -10,
            },
        ],
    },
    "Hidratacao": {
        "components": [
            {"question_id": "qtd_copos_agua", "weight": 0.45},
            {"question_id": "cor_urina", "weight": 0.35},
        ],
        "adjustments": [
            {
                "conditions": {
                    "question": "retencao_liquidos",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -10,
            },
            {
                "conditions": {
                    "question": "freq_inchaco",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -6,
            },
        ],
    },
    "Emocao": {
        "components": [
            {"question_id": "fome_emocional", "weight": 0.35},
            {"question_id": "compulsao_alimentar", "weight": 0.3},
            {"question_id": "culpa_apos_comer", "weight": 0.2},
            {"question_id": "nivel_estresse", "weight": 0.15},
        ],
        "adjustments": [
            {
                "conditions": {
                    "all": [
                        {
                            "question": "fome_emocional",
                            "operator": "in",
                            "value": ["Frequentemente", "Quase sempre"],
                        },
                        {
                            "question": "compulsao_alimentar",
                            "operator": "in",
                            "value": ["Frequentemente", "Quase sempre"],
                        },
                    ]
                },
                "impact": -10,
            },
            {
                "conditions": {
                    "question": "culpa_apos_comer",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -6,
            },
        ],
    },
    "Rotina": {
        "components": [
            {"question_id": "freq_atividade_fisica", "weight": 0.25},
            {"question_id": "freq_pular_refeicoes", "weight": 0.2},
            {"question_id": "refeicoes_no_dia", "weight": 0.2},
            {"question_id": "aderencia_plano_alimentar", "weight": 0.2},
            {"question_id": "variacao_rotina_fim_de_semana", "weight": 0.15},
        ],
        "adjustments": [
            {
                "conditions": {
                    "all": [
                        {
                            "question": "aderencia_plano_alimentar",
                            "operator": "in",
                            "value": [
                                "Sigo quase sempre",
                                "Sigo praticamente todos os dias",
                            ],
                        },
                        {
                            "question": "freq_pular_refeicoes",
                            "operator": "in",
                            "value": ["Frequentemente", "Quase sempre"],
                        },
                    ]
                },
                "impact": -12,
            },
            {
                "conditions": {
                    "question": "variacao_rotina_fim_de_semana",
                    "operator": "in",
                    "value": ["Muda bastante", "É totalmente diferente"],
                },
                "impact": -8,
            },
        ],
    },
}


def calcular_pilares(respostas: Dict[str, Any]) -> Dict[str, int]:
    """Public API used by the rest of the application.

    Args:
        respostas: Dicionário com as respostas do formulário usando chaves
            estáveis (IDs definidos em QUESTION_CATALOG).

    Returns:
        Dict[str, int]: Pontuações normalizadas por pilar.
    """

    resultados: Dict[str, int] = {}
    for pilar, config in PILLARS_CONFIG.items():
        base = _compute_weighted_score(respostas, config["components"])
        final_score = _apply_adjustments(base, respostas, config.get("adjustments", []))
        resultados[pilar] = int(round(final_score))
    return resultados


__all__ = ["calcular_pilares", "QUESTION_CATALOG", "PILLARS_CONFIG"]

