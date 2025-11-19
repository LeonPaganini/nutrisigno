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
    "nivel_energia_dia": {
        "text": "Como você avalia seu nível de energia ao longo do dia?",
        "type": "likert",
        "options": INTENSITY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": _likert_mapping(INTENSITY_5),
        },
    },
    "cansaco_frequente": {
        "text": "Com que frequência você se sente cansada ao longo do dia?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 85,
                "às vezes": 60,
                "as vezes": 60,
                "frequentemente": 35,
                "quase sempre": 15,
            },
        },
    },
    "acorda_cansada": {
        "text": "Como você costuma se sentir ao acordar?",
        "type": "multiple_choice",
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
    "tipo_fezes_bristol": {
        "text": "Qual tipo de fezes representa melhor seu padrão (Escala de Bristol)?",
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
    "freq_inchaco_abdominal": {
        "text": "Com que frequência você sente inchaço abdominal?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 85,
                "às vezes": 55,
                "as vezes": 55,
                "frequentemente": 25,
                "quase sempre": 10,
            },
        },
    },
    "freq_evacuacao": {
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
    "horas_sono_noite": {
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
    "copos_agua_dia": {
        "text": "Quantos copos de água (200 ml) você bebe por dia?",
        "type": "numeric",
        "normalizer": {
            "type": "numeric_range",
            "min_ideal": 8,
            "max_ideal": 12,
            "hard_min": 2,
            "hard_max": 20,
        },
    },
    "cor_urina": {
        "text": "Qual a cor predominante da sua urina?",
        "type": "multiple_choice",
        "options": [
            "Transparente",
            "Amarelo muito claro",
            "Amarelo claro",
            "Amarelo",
            "Âmbar",
            "Muito escura",
        ],
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "transparente": 95,
                "amarelo muito claro": 100,
                "amarelo claro": 85,
                "amarelo": 60,
                "âmbar": 30,
                "ambar": 30,
                "muito escura": 10,
                "transparente (parabéns, você está hidratado(a)!)": 95,
                "amarelo muito claro (parabéns, você está hidratado(a)!)": 100,
                "amarelo claro (atenção, moderadamente desidratado)": 70,
                "amarelo (atenção, moderadamente desidratado)": 60,
                "amarelo escuro (perigo, procure atendimento!)": 25,
                "castanho claro (perigo extremo, muito desidratado!)": 15,
                "castanho escuro (perigo extremo, muito desidratado!)": 10,
            },
        },
    },
    "retencao_inchaco": {
        "text": "Com que frequência você percebe retenção de líquidos/inchaço?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "às vezes": 60,
                "as vezes": 60,
                "frequentemente": 35,
                "quase sempre": 15,
            },
        },
    },
    "fome_emocional": {
        "text": "Com que frequência você come para aliviar emoções (ansiedade, tristeza, estresse)?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "às vezes": 55,
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
                "às vezes": 45,
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
                "às vezes": 55,
                "as vezes": 55,
                "frequentemente": 30,
                "quase sempre": 10,
            },
        },
    },
    "refeicoes_por_dia": {
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
    "freq_pular_refeicoes": {
        "text": "Com que frequência você pula refeições?",
        "type": "likert",
        "options": FREQUENCY_5,
        "normalizer": {
            "type": "categorical",
            "mapping": {
                "nunca": 100,
                "raramente": 80,
                "às vezes": 55,
                "as vezes": 55,
                "frequentemente": 30,
                "quase sempre": 10,
            },
        },
    },
    "constancia_fim_de_semana": {
        "text": "Como sua rotina alimentar muda nos fins de semana?",
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


def _liters_to_cups(value: Any) -> Optional[float]:
    liters = _coerce_float(value)
    if liters is None:
        return None
    return liters * 5.0


LEGACY_ALIASES: Dict[str, List[Dict[str, Any]]] = {
    "nivel_energia_dia": [{"key": "nivel_energia"}, {"key": "energia_diaria"}],
    "acorda_cansada": [{"key": "sensacao_ao_acordar"}],
    "tipo_fezes_bristol": [{"key": "tipo_fezes"}],
    "freq_inchaco_abdominal": [{"key": "freq_inchaco"}],
    "freq_evacuacao": [{"key": "freq_intestino"}],
    "horas_sono_noite": [{"key": "horas_sono"}, {"key": "sono_horas"}],
    "copos_agua_dia": [
        {"key": "qtd_copos_agua"},
        {"key": "consumo_agua", "transform": _liters_to_cups},
    ],
    "retencao_inchaco": [{"key": "retencao_liquidos"}],
    "refeicoes_por_dia": [{"key": "refeicoes_no_dia"}],
    "constancia_fim_de_semana": [{"key": "variacao_rotina_fim_de_semana"}],
}


def _get_answer(respostas: Dict[str, Any], question_id: str) -> Any:
    if question_id in respostas:
        return respostas.get(question_id)
    for alias in LEGACY_ALIASES.get(question_id, []):
        alias_key = alias.get("key")
        if not alias_key or alias_key not in respostas:
            continue
        value = respostas[alias_key]
        transform = alias.get("transform")
        if transform is None:
            return value
        try:
            transformed = transform(value)
        except Exception:
            transformed = None
        if transformed is not None:
            return transformed
    return None


def _get_question_normalizer(question_id: str) -> Optional[Dict[str, Any]]:
    question = QUESTION_CATALOG.get(question_id)
    return None if question is None else question.get("normalizer")


def _compute_weighted_score(respostas: Dict[str, Any], components: List[Dict[str, Any]]) -> Optional[float]:
    accumulated = 0.0
    total_weight = 0.0
    for component in components:
        question_id = component["question_id"]
        weight = component["weight"]
        normalizer = component.get("normalizer") or _get_question_normalizer(question_id)
        answer = _get_answer(respostas, question_id)
        normalized = _normalize_answer(answer, normalizer)
        if normalized is None:
            continue
        accumulated += normalized * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return accumulated / total_weight


def _resolve_condition_value(
    respostas: Dict[str, Any], question_id: str, normalized: bool = False
) -> Optional[float | Any]:
    if normalized:
        normalizer = _get_question_normalizer(question_id)
        return _normalize_answer(_get_answer(respostas, question_id), normalizer)
    return _get_answer(respostas, question_id)


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
    base_score: Optional[float], respostas: Dict[str, Any], adjustments: List[Dict[str, Any]]
) -> Optional[float]:
    if base_score is None:
        return None
    score = base_score
    for adjustment in adjustments:
        if _matches_condition(respostas, adjustment["conditions"]):
            score += adjustment.get("impact", 0)
    return max(0.0, min(100.0, score))


PILLARS_CONFIG: Dict[str, Dict[str, Any]] = {
    "Energia": {
        "components": [
            {"question_id": "nivel_energia_dia", "weight": 0.4},
            {"question_id": "cansaco_frequente", "weight": 0.3},
            {"question_id": "acorda_cansada", "weight": 0.3},
        ],
        "adjustments": [
            {
                "conditions": {
                    "question": "cansaco_frequente",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -6,
            },
            {
                "conditions": {
                    "question": "acorda_cansada",
                    "operator": "in",
                    "value": ["Extremamente cansada", "Cansada"],
                },
                "impact": -6,
            },
        ],
    },
    "Digestao": {
        "components": [
            {"question_id": "tipo_fezes_bristol", "weight": 0.45},
            {"question_id": "freq_evacuacao", "weight": 0.3},
            {"question_id": "freq_inchaco_abdominal", "weight": 0.25},
        ],
        "adjustments": [
            {
                "conditions": {
                    "all": [
                        {
                            "question": "tipo_fezes_bristol",
                            "operator": "in",
                            "value": [
                                "Tipo 1",
                                "Tipo 1 (Carocinhos duros)",
                                "Tipo 2",
                                "Tipo 2 (Salsicha grumosa)",
                            ],
                        },
                        {
                            "question": "freq_evacuacao",
                            "operator": "in",
                            "value": ["Menos de 3x por semana"],
                        },
                    ]
                },
                "impact": -10,
            },
            {
                "conditions": {
                    "question": "freq_inchaco_abdominal",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -6,
            },
        ],
    },
    "Sono": {
        "components": [
            {"question_id": "horas_sono_noite", "weight": 0.35},
            {"question_id": "qualidade_sono", "weight": 0.35},
            {"question_id": "despertares_noturnos", "weight": 0.3},
        ],
        "adjustments": [
            {
                "conditions": {"question": "horas_sono_noite", "operator": "lt", "value": 6},
                "impact": -12,
            },
            {
                "conditions": {
                    "all": [
                        {
                            "question": "horas_sono_noite",
                            "operator": "between",
                            "value": [7, 9],
                        },
                        {
                            "question": "despertares_noturnos",
                            "operator": "gt",
                            "value": 2,
                        },
                    ]
                },
                "impact": -8,
            },
        ],
    },
    "Hidratacao": {
        "components": [
            {"question_id": "copos_agua_dia", "weight": 0.45},
            {"question_id": "cor_urina", "weight": 0.35},
            {"question_id": "retencao_inchaco", "weight": 0.2},
        ],
        "adjustments": [
            {
                "conditions": {
                    "question": "copos_agua_dia",
                    "operator": "lt",
                    "value": 6,
                },
                "impact": -6,
            },
            {
                "conditions": {
                    "question": "retencao_inchaco",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -6,
            },
        ],
    },
    "Emocao": {
        "components": [
            {"question_id": "fome_emocional", "weight": 0.4},
            {"question_id": "compulsao_alimentar", "weight": 0.35},
            {"question_id": "culpa_apos_comer", "weight": 0.25},
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
            {"question_id": "refeicoes_por_dia", "weight": 0.3},
            {"question_id": "freq_pular_refeicoes", "weight": 0.25},
            {"question_id": "constancia_fim_de_semana", "weight": 0.2},
            {"question_id": "freq_atividade_fisica", "weight": 0.25},
        ],
        "adjustments": [
            {
                "conditions": {
                    "question": "freq_pular_refeicoes",
                    "operator": "in",
                    "value": ["Frequentemente", "Quase sempre"],
                },
                "impact": -10,
            },
            {
                "conditions": {
                    "question": "constancia_fim_de_semana",
                    "operator": "in",
                    "value": ["Muda bastante", "É totalmente diferente"],
                },
                "impact": -8,
            },
        ],
    },
}


def calcular_pilares(respostas: Dict[str, Any]) -> Dict[str, Optional[int]]:
    """Public API used by the rest of the application.

    Args:
        respostas: Dicionário com as respostas do formulário usando chaves
            estáveis (IDs definidos em QUESTION_CATALOG).

    Returns:
        Dict[str, Optional[int]]: Pontuações normalizadas por pilar.
    """

    resultados: Dict[str, Optional[int]] = {}
    for pilar, config in PILLARS_CONFIG.items():
        base = _compute_weighted_score(respostas, config["components"])
        final_score = _apply_adjustments(base, respostas, config.get("adjustments", []))
        resultados[pilar] = None if final_score is None else int(round(final_score))
    return resultados


__all__ = ["calcular_pilares", "QUESTION_CATALOG", "PILLARS_CONFIG"]

