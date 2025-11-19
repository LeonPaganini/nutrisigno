# modules/openai_utils.py
from __future__ import annotations
import os, json, math, hashlib, random
from typing import Any, Dict

SIMULATE = os.getenv("SIMULATE", "0") == "1" or not os.getenv("OPENAI_API_KEY")

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # ok no modo simulado

# -------- utilidades internas (simulação determinística) --------
def _seed_from_payload(payload: Dict[str, Any]) -> int:
    h = hashlib.md5(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def _estimate_calories(peso: float, altura_cm: float, atividade: str, objetivo: str) -> int:
    # Mifflin-St Jeor aproximado + fator atividade
    bmr = 10 * peso + 6.25 * altura_cm - 5 * int(float(payload_or(30, "idade")))  # idade default 30
    fa = {"sedentário":1.2,"leve":1.375,"moderado":1.55,"alto":1.725,"intenso":1.725}
    tdee = bmr * fa.get((atividade or "leve").lower(), 1.375)
    objetivo = (objetivo or "manter").lower()
    if "emag" in objetivo: tdee -= 300
    if "ganho" in objetivo: tdee += 300
    return max(1200, int(round(tdee)))

def payload_or(default, key):  # helperzinho para simulação
    return default

def _mock_plan(user_data: Dict[str, Any]) -> Dict[str, Any]:
    random.seed(_seed_from_payload(user_data))
    peso = float(user_data.get("peso") or 70)
    altura = float(user_data.get("altura") or 170)
    atividade = user_data.get("nivel_atividade") or "Leve"
    objetivo = user_data.get("objetivo") or "manter"
    kcal = _estimate_calories(peso, altura, atividade, objetivo)

    def meal(title, items, share):
        return {"title": title, "items": items, "kcal": int(round(kcal * share))}

    return {
        "diet": {
            "total_kcal": kcal,
            "meals": [
                meal("Café da manhã", ["Iogurte natural 170g", "Aveia 30g", "Banana 1un"], 0.25),
                meal("Almoço", ["Arroz 120g", "Feijão 100g", "Frango 120g", "Salada mista"], 0.35),
                meal("Lanche", ["Maçã 1un", "Castanhas 20g"], 0.10),
                meal("Jantar", ["Omelete 2 ovos", "Legumes salteados", "Azeite 1 cchá"], 0.25),
            ],
            "hydration": f"Meta diária: {max(1.5, round(peso*0.035,1))} L",
            "fiber": "25–35 g/dia de fibras (verduras, legumes e frutas).",
            "substitutions": {
                "Café da manhã": ["Pão integral 1f ↔ Aveia 30g", "Queijo branco 30g ↔ Iogurte 100g"],
                "Almoço": ["Frango ↔ Peixe magro", "Arroz branco ↔ Integral"],
                "Lanche": ["Iogurte skyr ↔ Fruta + sementes"],
                "Jantar": ["Tofu ↔ Ovos", "Abóbora assada ↔ Batata-doce"],
            },
        },
        "workout": {
            "goal": "Condicionamento geral",
            "days_per_week": 3 if "emag" in objetivo.lower() else 4,
            "blocks": [
                {"phase": "Aquecimento", "exercises": ["Caminhada leve 10min"], "duration_min": 10},
                {"phase": "Principal", "exercises": ["Circuito corpo inteiro 25–30min"], "duration_min": 30},
                {"phase": "Desaquecimento", "exercises": ["Alongamentos 5–10min"], "duration_min": 10},
            ],
        },
        "notes": ["Plano simulado (offline) para testes de UI."],
    }

def _mock_insights(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Resumo de insights que o painel usa (sem IA)."""
    peso = float(user_data.get("peso") or 70)
    altura = float(user_data.get("altura") or 170)
    altura_m = altura / 100
    bmi = round(peso / (altura_m ** 2), 1)
    bmi_cat = (
        "Baixo peso" if bmi < 18.5 else
        "Eutrofia" if bmi < 25 else
        "Sobrepeso" if bmi < 30 else
        "Obesidade"
    )

    consumo_agua_raw = user_data.get("consumo_agua")
    if consumo_agua_raw in (None, "", 0):
        try:
            consumo_agua = float(user_data.get("copos_agua_dia") or 0) * 0.2
        except (TypeError, ValueError):
            consumo_agua = 0.0
        if not consumo_agua:
            consumo_agua = 1.5
    else:
        consumo_agua = float(consumo_agua_raw)
    recomendado = round(max(1.5, peso * 0.035), 1)
    water_status = "OK" if consumo_agua >= recomendado else "Abaixo do ideal"

    # Bristol & urina (texto curto)
    bristol = (
        user_data.get("tipo_fezes_bristol")
        or user_data.get("tipo_fezes")
        or ""
    ).lower()
    bristol_text = "Padrão dentro do esperado" if "tipo 4" in bristol else "Atenção à consistência/hidratação"
    urine = (user_data.get("cor_urina") or "").lower()
    urine_text = "Hidratado" if "claro" in urine else "Possível desidratação"

    # Psico (0-5)
    motiv = int(user_data.get("motivacao") or 3)
    stress = int(user_data.get("estresse") or 3)

    # Dica do signo ética (não prescritiva)
    signo = (user_data.get("signo") or "").strip().lower()
    sign_hints = {
        "áries": "Planeje lanches práticos para evitar impulsos.",
        "touro": "Valorize prazer com densidade nutricional.",
        "gêmeos": "Varie preparos para manter adesão.",
        "câncer": "Refeições leves e regulares ajudam conforto digestivo.",
        "leão": "Evite exageros por ocasião social.",
        "virgem": "Rotina simples e organizada favorece constância.",
        "libra": "Defina cardápios semanais para evitar indecisão.",
        "escorpião": "Prefira consistência a extremos alimentares.",
        "sagitário": "Modere porções em dias muito ativos.",
        "capricórnio": "Inclua pausas e refeições completas na agenda.",
        "aquário": "Teste novidades, mantendo base equilibrada.",
        "peixes": "Apoie-se em hidratação e regularidade.",
    }
    hint = sign_hints.get(signo, "Use seu signo apenas como inspiração de hábitos saudáveis.")

    return {
        "bmi": bmi,
        "bmi_category": bmi_cat,
        "recommended_water": recomendado,
        "water_status": water_status,
        "bristol": bristol_text,
        "urine": urine_text,
        "motivacao": motiv,
        "estresse": stress,
        "sign_hint": hint,
        "consumption": {"water_liters": consumo_agua, "recommended_liters": recomendado},
    }

# ----------------- API pública -----------------
def generate_plan(user_data: Dict[str, Any], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    if SIMULATE or OpenAI is None:
        return _mock_plan(user_data)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # ... (sua chamada real, se quiser manter)
    try:
        # se der pau, cai no mock:
        return _mock_plan(user_data)
    except Exception:
        return _mock_plan(user_data)

def generate_insights(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Novo: fornece o pacote de insights para o painel.
    - No modo simulado, calcula localmente.
    - Se houver IA, você pode enriquecer com um resumo textual.
    """
    if SIMULATE or OpenAI is None:
        ins = _mock_insights(user_data)
        return {
            "insights": ins,
            "ai_summary": (
                "Resumo simulado: hidratação, IMC, sinais de digestão e fatores "
                "comportamentais (motivação/estresse) combinados a um lembrete ético "
                "de que astrologia é inspiração de hábitos, não substituto de orientação clínica."
            ),
        }

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # opcional: chamar o LLM para descrever o conjunto de insights
    try:
        ins = _mock_insights(user_data)  # pode calcular localmente e pedir ao LLM para narrar
        return {"insights": ins, "ai_summary": "Resumo IA (desativado neste exemplo)."}
    except Exception:
        ins = _mock_insights(user_data)
        return {"insights": ins, "ai_summary": "Resumo simulado (fallback)."}