"""Utilities for interacting with the OpenAI API or providing simulated responses.

This module centralises all calls to OpenAI.  When the environment
variable ``OPENAI_API_KEY`` is not provided or when ``SIMULATE=1`` is
set, the functions here return deterministic, simulated results to
facilitate local development.  When properly configured with an API
key, the functions will make real API requests.

Two high level capabilities are exposed: generating a dietary plan
(:func:`generate_plan`) and creating short behavioural insights based on
user data (:func:`generate_insights`).  The simulated paths use simple
heuristics to craft plausible results without any external calls.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
from typing import Any, Dict, Optional

# Simulation is triggered either when SIMULATE=1 or the API key is
# missing.  In such cases the OpenAI client is not imported and
# deterministic mock functions are used instead.
SIMULATE: bool = os.getenv("SIMULATE", "0") == "1" or not os.getenv("OPENAI_API_KEY")

try:
    from openai import OpenAI  # only available when not simulating
except Exception:
    OpenAI = None  # type: ignore[assignment]

def _seed_from_payload(payload: Dict[str, Any]) -> int:
    """Derive a reproducible seed from a JSONâserialisable payload."""
    h = hashlib.md5(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def _estimate_calories(peso: float, altura_cm: float, atividade: str, objetivo: str) -> int:
    """Estimate total daily calories using a simplified MifflinâSt Jeor formula.

    A basic basal metabolic rate is computed and then multiplied by an
    activity factor.  The result is adjusted based on the stated goal
    (loss, maintenance, or gain).
    """
    altura = altura_cm
    bmr = 10 * peso + 6.25 * altura - 5 * 30  # assume age 30 when unknown
    fa = {"SedentÃ¡rio": 1.2, "Leve": 1.375, "Moderado": 1.55, "Intenso": 1.725}.get(atividade, 1.375)
    tdee = bmr * fa
    objetivo = (objetivo or "manter").lower()
    if "emagrecer" in objetivo:
        tdee -= 300
    elif "ganho" in objetivo:
        tdee += 300
    return int(max(1200, round(tdee)))

# Behavioural hints for each zodiac sign.  These are used both by the
# dashboard and by the simulated insights generator.
_SIGN_HINTS: Dict[str, str] = {
    "Ãries": "Evite decisÃµes impulsivas: planeje suas refeiÃ§Ãµes e escolha opÃ§Ãµes saciantes.",
    "Touro": "Valorize a qualidade, evitando excessos; comidas prazerosas podem ser saudÃ¡veis.",
    "GÃªmeos": "Varie os alimentos para evitar tÃ©dio e mantenha refeiÃ§Ãµes regulares.",
    "CÃ¢ncer": "Prefira refeiÃ§Ãµes leves e frequentes para evitar desconfortos gÃ¡stricos.",
    "LeÃ£o": "Evite exagerar para impressionar; busque equilÃ­brio e moderaÃ§Ã£o.",
    "Virgem": "Mantenha uma rotina organizada, preparando refeiÃ§Ãµes caseiras sempre que possÃ­vel.",
    "Libra": "Planeje seu cardÃ¡pio semanal para reduzir indecisÃ£o e escolhas de Ãºltima hora.",
    "EscorpiÃ£o": "Evite extremos alimentares; consuma porÃ§Ãµes controladas e variadas.",
    "SagitÃ¡rio": "Cuidado com o entusiasmo excessivo: busque equilÃ­brio entre prazer e nutriÃ§Ã£o.",
    "CapricÃ³rnio": "EstabeleÃ§a pausas alimentares e evite rigidez excessiva; permita pequenas indulgÃªncias.",
    "AquÃ¡rio": "Experimente novos ingredientes, mas mantenha constÃ¢ncia e variedade.",
    "Peixes": "Escute seu corpo e hidrateâse; refeiÃ§Ãµes intuitivas podem ajudar na saciedade.",
}

def _mock_plan(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic mock plan based on the provided user data.

    The plan contains a simple distribution of meals, hydration goals,
    fibre recommendations, substitution suggestions and a basic workout
    routine.  Some elements are adjusted based on the user's zodiac
    sign to provide a personalised feel even in simulation mode.
    """
    random.seed(_seed_from_payload(user_data))
    peso = float(user_data.get("peso") or 70)
    altura = float(user_data.get("altura") or 170)
    atividade = user_data.get("nivel_atividade") or "Leve"
    objetivo = (user_data.get("objetivo") or "manter").lower()
    kcal = _estimate_calories(peso, altura, atividade, objetivo)

    def meal(title: str, items: list[str], share: float) -> Dict[str, Any]:
        return {"title": title, "items": items, "kcal": int(round(kcal * share))}

    # Base plan used when no sign specific plan is provided
    default_meals = [
        meal("CafÃ© da manhÃ£", ["Iogurte natural (170g)", "Aveia (30g)", "Banana (1un)"], 0.25),
        meal("AlmoÃ§o", ["Arroz (120g)", "FeijÃ£o (100g)", "Frango grelhado (120g)", "Salada mista"], 0.35),
        meal("Lanche", ["MaÃ§Ã£ (1un)", "Castanhas (20g)"], 0.10),
        meal("Jantar", ["Omelete 2 ovos", "Legumes salteados", "Azeite (1 cchÃ¡)"], 0.25),
    ]

    # Simple signâspecific overrides for demonstration.  These adjust
    # meal composition slightly to reflect notional preferences.
    sign = user_data.get("signo") or ""
    sign_meals: Dict[str, list[Dict[str, Any]]] = {
        "Ãries": [
            meal("CafÃ© da manhÃ£", ["Smoothie energÃ©tico de frutas vermelhas", "Granola (40g)"], 0.25),
            meal("AlmoÃ§o", ["Quinoa (100g)", "Peito de frango grelhado (120g)", "BrÃ³colis"], 0.35),
            meal("Lanche", ["Barra de proteÃ­na", "Laranja (1un)"], 0.10),
            meal("Jantar", ["SalmÃ£o ao forno (100g)", "Legumes variados", "Batata-doce (100g)"], 0.25),
        ],
        "Touro": [
            meal("CafÃ© da manhÃ£", ["PÃ£o integral (2 fatias)", "Queijo branco (30g)", "Tomate"] , 0.25),
            meal("AlmoÃ§o", ["Arroz integral (120g)", "FeijÃ£o (100g)", "Carne assada (100g)", "Salada colorida"], 0.35),
            meal("Lanche", ["Iogurte grego (100g)", "Mel (1 cchÃ¡)", "Frutas secas"], 0.10),
            meal("Jantar", ["Sopa de legumes", "PÃ£o de sementes (1 fatia)", "Ricota"], 0.25),
        ],
    }
    meals = sign_meals.get(sign, default_meals)

    plan = {
        "diet": {
            "total_kcal": kcal,
            "meals": meals,
            "hydration": f"Meta diÃ¡ria: {max(1.5, round(peso * 0.035, 1))} L de Ã¡gua",
            "fiber": "Busque 25â35 g/dia, priorizando verduras, legumes e frutas.",
            "substitutions": {
                "CafÃ© da manhÃ£": ["PÃ£o integral (1 fatia) â aveia (30g)", "Queijo branco (30g) â iogurte (100g)"],
                "AlmoÃ§o": ["Peito de frango â peixe magro", "Arroz branco â arroz integral"],
                "Lanche": ["Iogurte skyr â fruta + sementes"],
                "Jantar": ["Tofu â ovos", "AbÃ³bora assada â batata-doce cozida"],
            },
        },
        "workout": {
            "goal": "Condicionamento geral",
            "days_per_week": 3 if "emagrecer" in objetivo else 4,
            "blocks": [
                {"phase": "Aquecimento", "exercises": ["Caminhada leve 10min"], "duration_min": 10},
                {"phase": "Principal", "exercises": ["Treino circuito corpo inteiro 25â30min"], "duration_min": 30},
                {"phase": "Desaquecimento", "exercises": ["Alongamentos 5â10min"], "duration_min": 10},
            ],
        },
        "notes": [
            "Plano simulado (modo offline) para testes de interface.",
            "Ajuste por preferÃªncias e restriÃ§Ãµes quando ativar a IA.",
        ],
        # Include astrological profile hint for report generation
        "perfil_astrologico": {
            "signo": sign,
            "descricao": _SIGN_HINTS.get(sign, ""),
        },
    }
    return plan

def _build_prompt(_: Dict[str, Any]) -> str:
    """Construct a prompt for the OpenAI model.

    This function is currently unused in simulation mode but is kept
    for compatibility.  In a production setting it should build a
    description of the userâs nutritional needs and preferences to be
    sent to the language model.
    """
    return "Gerar plano em JSON..."

def generate_plan(user_data: Dict[str, Any], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Generate a dietary and workout plan based on user data.

    When running in simulation mode this returns a deterministic mock
    plan.  Otherwise it constructs a prompt and sends it to the
    OpenAI Chat Completions API, expecting a JSONâformatted response.

    Parameters
    ----------
    user_data:
        Dictionary containing the userâs input collected from the form.
    model:
        The name of the OpenAI model to query when not simulating.

    Returns
    -------
    dict
        A structured plan including diet, workout and additional notes.
    """
    if SIMULATE or OpenAI is None:
        return _mock_plan(user_data)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = _build_prompt(user_data)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "VocÃª Ã© um assistente de nutriÃ§Ã£o responsÃ¡vel. Responda em JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        # fallback to mock when any error occurs
        return _mock_plan(user_data)

def generate_insights(user_data: Dict[str, Any], model: str = "gpt-4o-mini") -> str:
    """Generate a short behavioural insight string from user data.

    This helper crafts a narrative that combines subjective inputs (such
    as perceived energy levels, impulsivity and routine adherence) with
    astrological hints.  In simulation mode it applies simple rules to
    assemble a coherent paragraph.  When an API key is configured the
    function delegates to the OpenAI Chat Completions API to produce
    the insight.

    Parameters
    ----------
    user_data:
        Dictionary containing the userâs input collected from the form.
    model:
        The name of the OpenAI model to query when not simulating.

    Returns
    -------
    str
        A humanâreadable paragraph with behavioural recommendations.
    """
    # Build a simulated insight if no API key is configured
    if SIMULATE or OpenAI is None:
        sign = user_data.get("signo", "")
        energia = (user_data.get("energia_diaria") or "").lower()
        impulsividade = user_data.get("impulsividade_alimentar")
        rotina = user_data.get("rotina_alimentar")
        pieces: list[str] = []
        # Energy assessment
        if energia:
            if energia == "baixa":
                pieces.append("Sua energia diÃ¡ria estÃ¡ baixa; procure incluir refeiÃ§Ãµes energÃ©ticas e nutritivas.")
            elif energia == "moderada":
                pieces.append("VocÃª possui energia moderada; mantenha o equilÃ­brio entre refeiÃ§Ãµes e descanso.")
            else:
                pieces.append("VocÃª estÃ¡ com energia alta; aproveite para preparar refeiÃ§Ãµes saudÃ¡veis e praticar atividades fÃ­sicas.")
        # Impulsivity assessment
        if impulsividade is not None:
            try:
                imp = int(impulsividade)
            except Exception:
                imp = 3
            if imp >= 4:
                pieces.append("TendÃªncia Ã  impulsividade; planeje suas compras e refeiÃ§Ãµes para evitar escolhas precipitadas.")
            elif imp <= 2:
                pieces.append("Baixa impulsividade; continue consciente das suas escolhas alimentares.")
            else:
                pieces.append("Mantenha atenÃ§Ã£o aos sinais de fome e saciedade para controlar a impulsividade.")
        # Routine assessment
        if rotina is not None:
            try:
                rot = int(rotina)
            except Exception:
                rot = 3
            if rot >= 4:
                pieces.append("Rotina alimentar Ã© importante para vocÃª; use isso a seu favor seguindo horÃ¡rios regulares.")
            elif rot <= 2:
                pieces.append("VocÃª nÃ£o tem preferÃªncia por rotina; crie pequenas metas diÃ¡rias para ajudar.")
            else:
                pieces.append("Estabelecer horÃ¡rios regulares ajudarÃ¡ na consistÃªncia do plano.")
        # Astrological hint
        if sign:
            hint = _SIGN_HINTS.get(sign, "")
            if hint:
                pieces.append(f"Como nativo(a) de {sign}, lembre-se: {hint}")
        return " ".join(pieces).strip()

    # Real API call
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # Build a descriptive prompt that includes the subjective inputs.  The
    # content is not rigidly specified here to keep the example concise.
    prompt_parts = []
    sign = user_data.get("signo", "")
    if sign:
        prompt_parts.append(f"Signo: {sign}.")
    energia = user_data.get("energia_diaria")
    if energia:
        prompt_parts.append(f"Energia diÃ¡ria: {energia}.")
    imp = user_data.get("impulsividade_alimentar")
    if imp is not None:
        prompt_parts.append(f"Impulsividade alimentar (1-5): {imp}.")
    rot = user_data.get("rotina_alimentar")
    if rot is not None:
        prompt_parts.append(f"ImportÃ¢ncia da rotina alimentar (1-5): {rot}.")
    prompt_parts.append("ForneÃ§a um parÃ¡grafo de orientaÃ§Ã£o comportamental saudÃ¡vel combinando estes dados com conceitos astrolÃ³gicos.")
    prompt = " ".join(prompt_parts)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "VocÃª Ã© um nutricionista que integra astrologia de forma leve. Responda de forma motivacional e em um parÃ¡grafo."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=200,
    )
    try:
        return resp.choices[0].message.content.strip()
    except Exception:
        # fallback to a generic message
        return "Mantenha hÃ¡bitos saudÃ¡veis e procure orientaÃ§Ã£o profissional quando necessÃ¡rio."