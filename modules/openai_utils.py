# modules/openai_utils.py
from __future__ import annotations
import os, json, math, hashlib, random
from typing import Any, Dict

# Modo simulado se SIMULATE=1 ou se faltar a chave
SIMULATE = os.getenv("SIMULATE", "0") == "1" or not os.getenv("OPENAI_API_KEY")

try:
    from openai import OpenAI  # só será usado se não estiver simulando
except Exception:
    OpenAI = None  # ok no modo simulado

def _seed_from_payload(payload: Dict[str, Any]) -> int:
    """Gera seed determinística para simulações reprodutíveis."""
    h = hashlib.md5(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def _estimate_calories(peso: float, altura_cm: float, atividade: str, objetivo: str) -> int:
    # Cálculo simples (Mifflin-St Jeor aproximado + fator atividade + ajuste objetivo)
    altura = altura_cm
    bmr = 10 * peso + 6.25 * altura - 5 * 30  # idade 30 default
    fa = {"Sedentário":1.2, "Leve":1.375, "Moderado":1.55, "Intenso":1.725}.get(atividade, 1.375)
    tdee = bmr * fa
    if "emagrecer" in objetivo.lower():
        tdee -= 300
    elif "ganho" in objetivo.lower():
        tdee += 300
    return int(max(1200, round(tdee)))

def _mock_plan(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Plano simulado coerente, determinístico a partir dos dados."""
    random.seed(_seed_from_payload(user_data))
    peso = float(user_data.get("peso") or 70)
    altura = float(user_data.get("altura") or 170)
    atividade = user_data.get("nivel_atividade") or "Leve"
    objetivo = (user_data.get("objetivo") or "manter").lower()
    kcal = _estimate_calories(peso, altura, atividade, objetivo)
    # refeições
    def meal(title, items, kcal_share):
        return {"title": title, "items": items, "kcal": int(round(kcal*kcal_share))}
    plan = {
        "diet": {
            "total_kcal": kcal,
            "meals": [
                meal("Café da manhã", ["Iogurte natural (170g)", "Aveia (30g)", "Banana (1un)"], 0.25),
                meal("Almoço", ["Arroz (120g)", "Feijão (100g)", "Frango grelhado (120g)", "Salada mista"], 0.35),
                meal("Lanche", ["Maçã (1un)", "Castanhas (20g)"], 0.10),
                meal("Jantar", ["Omelete 2 ovos", "Legumes salteados", "Azeite (1 cchá)"], 0.25),
            ],
            "hydration": f"Meta diária: {max(1.5, round(peso*0.035,1))} L de água",
            "fiber": "Busque 25–35 g/dia, priorizando verduras, legumes e frutas.",
            "substitutions": {
                "Café da manhã": ["Pão integral (1 fatia) ↔ aveia (30g)", "Queijo branco (30g) ↔ iogurte (100g)"],
                "Almoço": ["Peito de frango ↔ peixe magro", "Arroz branco ↔ arroz integral"],
                "Lanche": ["Iogurte skyr ↔ fruta + sementes"],
                "Jantar": ["Tofu ↔ ovos", "Abóbora assada ↔ batata-doce cozida"],
            },
        },
        "workout": {
            "goal": "Condicionamento geral",
            "days_per_week": 3 if "emagrecer" in objetivo else 4,
            "blocks": [
                {"phase": "Aquecimento", "exercises": ["Caminhada leve 10min"], "duration_min": 10},
                {"phase": "Principal", "exercises": ["Treino circuito corpo inteiro 25–30min"], "duration_min": 30},
                {"phase": "Desaquecimento", "exercises": ["Alongamentos 5–10min"], "duration_min": 10},
            ],
        },
        "notes": [
            "Plano simulado (modo offline) para testes de interface.",
            "Ajuste por preferências e restrições quando ativar a IA.",
        ],
    }
    return plan

def _build_prompt(_: Dict[str, Any]) -> str:
    # Não usado no modo simulado; mantido para compatibilidade
    return "Gerar plano em JSON..."

def generate_plan(user_data: Dict[str, Any], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Gera plano. No modo simulado, retorna um plano fake determinístico."""
    if SIMULATE or OpenAI is None:
        return _mock_plan(user_data)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = _build_prompt(user_data)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Você é um assistente de nutrição responsável. Responda em JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        # fallback duro mesmo se der problema
        return _mock_plan(user_data)