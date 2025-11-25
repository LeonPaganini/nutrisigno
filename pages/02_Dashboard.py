"""Página de resultados personalizada com métricas-base e cards essenciais."""

from __future__ import annotations

import html
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import streamlit as st

from modules import app_bootstrap, openai_utils, repo
from modules.client_state import get_user_cached, load_client_state, save_client_state
from modules.form.exporters import build_insights_pdf_bytes
from modules.form.ui_insights import (
    collect_comportamentos,
    element_icon,
    extract_bristol_tipo,
    extract_cor_urina,
    signo_elemento,
    signo_symbol,
)
from modules.share_image import gerar_imagem_share
from modules.behavior_profile_image import gerar_card_comportamental_bytes
from modules.results_context import PILLAR_NAMES, ensure_pilares_scores

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sessão e carregamento de dados
# ---------------------------------------------------------------------------

def _get_query_param(key: str) -> Optional[str]:
    try:
        value = st.query_params.get(key)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    except Exception:  # pragma: no cover - fallback
        params = st.experimental_get_query_params()
        value = params.get(key)
        if isinstance(value, list):
            return value[0] if value else None
        return value


def _resolve_pac_id() -> Optional[str]:
    pac_id = st.session_state.get("pac_id")
    if pac_id:
        return pac_id

    pac_id_loaded, step_loaded = load_client_state()
    if pac_id_loaded:
        st.session_state.pac_id = pac_id_loaded
        if step_loaded:
            try:
                st.session_state.step = max(1, int(str(step_loaded)))
            except Exception:  # pragma: no cover - defensive
                pass
        return pac_id_loaded

    pac_id_param = _get_query_param("pac_id") or _get_query_param("id")
    if pac_id_param:
        st.session_state.pac_id = pac_id_param
        return pac_id_param

    return None


def _load_payload(pac_id: str) -> Optional[Dict[str, Any]]:
    cached = st.session_state.get("paciente_data")
    if cached and cached.get("pac_id") == pac_id:
        return cached

    payload = get_user_cached(pac_id) or repo.get_by_pac_id(pac_id)
    if payload:
        st.session_state.paciente_data = payload
        st.session_state.data = payload.get("respostas") or {}
        st.session_state.plan = payload.get("plano_alimentar") or {}
        st.session_state.plano_compacto = payload.get("plano_alimentar_compacto") or {}
        st.session_state.macros = payload.get("macros") or {}
    return payload


# ---------------------------------------------------------------------------
# Normalização de insights herdados
# ---------------------------------------------------------------------------

def _fallback_insights(payload: Dict[str, Any]) -> Dict[str, Any]:
    peso = float(payload.get("peso") or 70)
    altura_cm = float(payload.get("altura") or 170)
    altura_m = max(0.1, altura_cm / 100.0)
    bmi = round(peso / (altura_m**2), 1)
    recomendado = round(max(1.5, peso * 0.035), 1)
    categoria = "Peso normal" if 18.5 <= bmi < 25 else ("Abaixo do peso" if bmi < 18.5 else "Sobrepeso")
    return {
        "bmi": bmi,
        "bmi_category": categoria,
        "water_status": "OK",
        "bristol": "Padrão dentro do esperado",
        "urine": "Hidratado",
        "motivacao": int(payload.get("motivacao") or 3),
        "estresse": int(payload.get("estresse") or 3),
        "sign_hint": "Use seu signo como inspiração, não como prescrição.",
        "consumption": {
            "water_liters": float(payload.get("consumo_agua") or 1.5),
            "recommended_liters": recomendado,
        },
    }


def _normalize_insights(payload: Dict[str, Any], insights: Dict[str, Any]) -> Dict[str, Any]:
    peso = float(payload.get("peso") or 0.0)
    altura_cm = float(payload.get("altura") or 0.0)
    altura_m = round(altura_cm / 100.0, 2) if altura_cm else 0.0
    imc = round(peso / (altura_m**2), 1) if peso and altura_m else 0.0

    bmi_value = insights.get("bmi") or imc or 0.0
    insights["bmi"] = float(bmi_value)
    insights["bmi_category"] = insights.get("bmi_category") or _imc_category(bmi_value)[0]

    consumo_info = insights.get("consumption") or {}
    consumo_real = _to_float(consumo_info.get("water_liters")) or 0.0
    if not consumo_real:
        consumo_real = _to_float(payload.get("consumo_agua")) or 0.0
    if not consumo_real:
        consumo_real = (
            _to_float(payload.get("copos_agua_dia")) or 0.0
        ) * 0.2
    recomendado = float(
        consumo_info.get("recommended_liters")
        or (round(max(1.5, peso * 0.035), 1) if peso else 2.0)
    )
    insights["consumption"] = {
        "water_liters": consumo_real,
        "recommended_liters": recomendado,
    }
    if recomendado and consumo_real:
        insights.setdefault(
            "water_status",
            "OK" if recomendado and consumo_real >= recomendado else "Abaixo do ideal",
        )
    else:
        insights.setdefault("water_status", "Indefinido")
    insights.setdefault("motivacao", int(payload.get("motivacao") or 0))
    insights.setdefault("estresse", int(payload.get("estresse") or 0))
    bristol_raw = payload.get("tipo_fezes_bristol") or payload.get("tipo_fezes")
    insights.setdefault("bristol", extract_bristol_tipo(bristol_raw))
    insights.setdefault("urine", extract_cor_urina(payload.get("cor_urina")))
    insights.setdefault("sign_hint", "Use seu signo como inspiração de hábitos saudáveis.")

    return insights


def _prepare_insights(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    cached_insights = st.session_state.get("dashboard_insights")
    cached_summary = st.session_state.get("dashboard_ai_summary")
    if cached_insights is not None and cached_summary is not None:
        return cached_insights, cached_summary

    try:
        ai_pack = openai_utils.generate_insights(payload)
        insights = ai_pack.get("insights", {}) or {}
        ai_summary = ai_pack.get("ai_summary", "Resumo indisponível (modo simulado).")
    except Exception as exc:  # pragma: no cover - fallback
        log.warning("generate_insights fallback: %s", exc)
        st.info("Modo automático: exibindo versão simplificada dos insights.")
        insights = _fallback_insights(payload)
        ai_summary = "Resumo simulado (fallback)."

    insights = _normalize_insights(payload, insights)
    st.session_state.dashboard_insights = insights
    st.session_state.dashboard_ai_summary = ai_summary
    return insights, ai_summary


# ---------------------------------------------------------------------------
# Utilidades de cálculo
# ---------------------------------------------------------------------------

PRIMARY = "#6C5DD3"
SUCCESS = "#28B487"
WARNING = "#F4A261"
CRITICAL = "#E76F51"
NEUTRAL = "#CBD5F5"


def _to_float(value: Any) -> Optional[float]:
    if value in (None, "", "—"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if not text:
        return None
    text = text.replace("kcal", "").replace("cal", "").replace("ml", "").replace("l", "")
    text = text.replace("horas", "").replace("hora", "").replace("h", "")
    text = text.replace("litros", "").replace("l/dia", "")
    text = text.replace("/dia", "")
    text = text.replace(",", ".")
    cleaned = "".join(ch if ch.isdigit() or ch in ".-" else " " for ch in text)
    parts = cleaned.split()
    for part in parts:
        try:
            return float(part)
        except ValueError:
            continue
    return None


def _strip_accents(text: str | None) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    ).lower()


def _imc_category(imc: float) -> Tuple[str, str]:
    if imc <= 0:
        return "Indefinido", WARNING
    if imc < 18.5:
        return "Abaixo do peso", WARNING
    if imc < 25:
        return "Peso normal", SUCCESS
    if imc < 30:
        return "Sobrepeso", WARNING
    return "Obesidade", CRITICAL


def _resolve_status(payload: Dict[str, Any]) -> Dict[str, str]:
    pagamento = (payload.get("status_pagamento") or payload.get("status") or "").strip().lower()
    plano = (payload.get("status_plano") or "").strip().lower()
    if plano == "erro":
        return {"state": "S3", "pagamento": pagamento or "pendente", "plano": plano or "erro"}
    if pagamento == "pago" or plano in {"disponivel", "gerado"} or payload.get("plano_alimentar"):
        return {"state": "S2", "pagamento": pagamento or "pago", "plano": plano or "disponivel"}
    return {"state": "S1", "pagamento": pagamento or "pendente", "plano": plano or "nao_gerado"}


KCAL_TABLE = {
    "nao_treinado": {
        "emagrecer": (23, 27, 25),
        "manter": (28, 32, 30),
        "ganhar": (33, 37, 35),
    },
    "treinado": {
        "emagrecer": (26, 30, 28),
        "manter": (31, 35, 33),
        "ganhar": (36, 40, 38),
    },
}


ELEMENT_BEHAVIOR = {
    "Terra": (
        "Construa rotina previsível com horários fixos de refeição.",
        "Planeje compras e pré-preparo no fim de semana.",
    ),
    "Ar": (
        "Varie formatos de refeições para evitar monotonia.",
        "Use lembretes digitais para não perder horários.",
    ),
    "Fogo": (
        "Transforme metas em desafios rápidos para manter engajamento.",
        "Inclua refeições âncora antes de compromissos intensos.",
    ),
    "Água": (
        "Crie rituais acolhedores nas refeições para sustentar hábito.",
        "Monitore sinais corporais e ajuste porções gradualmente.",
    ),
}


SIGN_BEHAVIOR = {
    "aries": (
        "Use metas semanais mensuráveis para canalizar impulso.",
        "Respire antes de comer em pressa para evitar excessos.",
    ),
    "touro": (
        "Valorize texturas nutritivas que tragam saciedade sem exagero.",
        "Troque conforto emocional por versões leves planejadas.",
    ),
    "gemeos": (
        "Alterne cardápios rápidos e novos para não perder foco.",
        "Combine refeições com conversas estruturadas para evitar distrações.",
    ),
    "cancer": (
        "Prepare refeições caseiras que transmitam segurança digestiva.",
        "Organize lanches leves para lidar com gatilhos noturnos.",
    ),
    "leao": (
        "Celebre progressos com registros visuais em vez de excessos.",
        "Planeje destaque nutricional diurno para evitar volume à noite.",
    ),
    "virgem": (
        "Checklist de ingredientes ajuda a manter padrão limpo.",
        "Cuidado com perfeccionismo: aceite ajustes simples ao plano.",
    ),
    "libra": (
        "Decida cardápio da semana para reduzir indecisão diária.",
        "Ancore refeições com companhia equilibrada sem ceder a pressões.",
    ),
    "escorpiao": (
        "Canalize intensidade criando metas nutricionais discretas.",
        "Evite extremos; prefira porções estáveis e variadas.",
    ),
    "sagitario": (
        "Planeje refeições portáteis para rotinas dinâmicas.",
        "Revise porções em dias festivos para manter direção.",
    ),
    "capricornio": (
        "Bloqueie refeições no calendário como compromissos.",
        "Permita flexibilidade controlada para evitar rigidez.",
    ),
    "aquario": (
        "Experimente receitas funcionais mantendo base nutritiva.",
        "Use comunidades online para reforçar compromisso saudável.",
    ),
    "peixes": (
        "Use playlists ou aromas para lembrar refeições equilibradas.",
        "Estabeleça limites claros para beliscos emocionais.",
    ),
}


SIGN_ACTIONS = {
    "aries": "Inicie o dia com {goal_focus} e registre vitórias rápidas.",
    "touro": "Organize refeições prazerosas e leves para sustentar {goal_focus}.",
    "gemeos": "Alterne receitas simples e novas mantendo {goal_focus}.",
    "cancer": "Monte refeição caseira-base que segure {goal_focus}.",
    "leao": "Planeje pratos destaque sem sair de {goal_focus}.",
    "virgem": "Prepare lotes organizados no domingo focando em {goal_focus}.",
    "libra": "Decida cardápio-binário (A/B) semanal para proteger {goal_focus}.",
    "escorpiao": "Defina metas discretas pós-refeição para manter {goal_focus}.",
    "sagitario": "Monte kit portátil nutritivo para seguir com {goal_focus}.",
    "capricornio": "Agende refeições no calendário como tarefas de {goal_focus}.",
    "aquario": "Teste combinações funcionais mantendo {goal_focus} estável.",
    "peixes": "Crie ritual sensorial antes das refeições para nutrir {goal_focus}.",
}


GOAL_DIRECTIVES = {
    "emagrecer": "Para emagrecer, fixe 3 refeições âncora e lanches proteicos.",
    "manter": "Para manter, consolide horários estáveis e monitore porções.",
    "ganhar": "Para ganhar, adicione lanches densos em proteína e calorias.",
}


GOAL_FOCUS = {
    "emagrecer": "o déficit leve",
    "manter": "o equilíbrio diário",
    "ganhar": "o superávit nutritivo",
}


GOAL_ACTIVITY_FOCUS = {
    "emagrecer": "o déficit leve",
    "manter": "o equilíbrio",
    "ganhar": "o superávit inteligente",
}


GOAL_RECOVERY = {
    "emagrecer": "o ritmo metabólico",
    "manter": "o equilíbrio metabólico",
    "ganhar": "a recuperação muscular",
}


CTA_TEXT = {
    "S1": "Desbloqueie seu Plano Completo com cardápios e substituições.",
    "S2": "Veja seu Plano IA e gere o PDF completo.",
    "S3": "Veja seu Plano IA e gere o PDF completo.",
}


FOCUS_STEPS = {
    "Hidratação": "ajuste ingestão hídrica com metas por garrafa.",
    "Sono": "estabeleça ritual relaxante 30 min antes de dormir.",
    "Estresse": "programar pausas de respiração durante o dia.",
    "Atividade": "estruturar microtreinos progressivos na agenda.",
    "IMC": "seguir plano alimentar monitorando medidas semanais.",
}


def _infer_goal(respostas: Dict[str, Any]) -> str:
    raw = (
        respostas.get("objetivo")
        or respostas.get("objetivo_principal")
        or respostas.get("meta_principal")
        or ""
    )
    normalized = _strip_accents(str(raw))
    if any(term in normalized for term in ("emag", "sec", "defini", "perda")):
        return "emagrecer"
    if any(term in normalized for term in ("ganh", "massa", "hiper")):
        return "ganhar"
    return "manter"


def _is_trained(respostas: Dict[str, Any]) -> bool:
    for key in ("perfil_treinado", "eh_treinado", "treinado", "perfil"):
        value = respostas.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            norm = _strip_accents(value)
            if norm in {"treinado", "sim", "atleta", "avancado", "avançado"}:
                return True
            if norm in {"nao", "não", "iniciante", "sedentario", "sedentário"}:
                return False
    nivel = _strip_accents(str(respostas.get("nivel_atividade") or ""))
    return any(term in nivel for term in ("intenso", "alto", "treino"))


def _extract_sleep_hours(respostas: Dict[str, Any]) -> Optional[float]:
    keys = (
        "sono_horas",
        "horas_sono",
        "sono",
        "tempo_sono",
        "sleep_hours",
        "sono_noite",
    )
    for key in keys:
        value = respostas.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().lower()
        if not text:
            continue
        if ":" in text:
            try:
                hours, minutes = text.split(":", 1)
                return float(hours) + float(minutes) / 60.0
            except Exception:  # pragma: no cover - defensive parsing
                pass
        text = text.replace("h", "").replace("horas", "").replace("hora", "")
        text = text.replace("~", "").replace(",", ".")
        if "-" in text:
            try:
                parts = [float(p) for p in text.split("-") if p.strip()]
                if parts:
                    return sum(parts) / len(parts)
            except Exception:
                pass
        match = re.search(r"(\d+(?:[\.,]\d+)?)", text)
        if match:
            try:
                return float(match.group(1).replace(",", "."))
            except ValueError:
                continue
    return None


def _extract_numeric_from_sources(respostas: Dict[str, Any], payload: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for key in keys:
        if key in respostas:
            value = _to_float(respostas.get(key))
            if value is not None:
                return value
        if key in payload:
            value = _to_float(payload.get(key))
            if value is not None:
                return value
    return None


def _calc_kcal_info(
    peso: float,
    goal: str,
    treinado: bool,
    respostas: Dict[str, Any],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    explicit = _extract_numeric_from_sources(
        respostas,
        payload,
        (
            "tdee",
            "get",
            "gasto_energetico_total",
            "gasto_energetico_tdee",
            "calorias_alvo",
        ),
    )
    perfil_key = "treinado" if treinado else "nao_treinado"
    faixa = KCAL_TABLE[perfil_key][goal]
    faixa_total = (peso * faixa[0], peso * faixa[1]) if peso else (0.0, 0.0)
    alvo_default = peso * faixa[2] if peso else 0.0
    alvo = explicit or alvo_default
    source = "GET/TDEE informado" if explicit else f"{faixa[2]:.0f} kcal/kg"
    return {
        "target": max(0.0, alvo),
        "target_display": _format_number(alvo),
        "source": source,
        "range_display": _format_range(faixa_total),
        "per_kg": f"{faixa[0]:.0f}–{faixa[1]:.0f} kcal/kg",
        "perfil": "Treinado" if treinado else "Não treinado",
        "goal": goal,
    }


def _format_number(value: float) -> str:
    if value <= 0:
        return "—"
    return f"{int(round(value)):,}".replace(",", ".")


def _format_range(interval: Tuple[float, float]) -> str:
    low, high = interval
    if low <= 0 or high <= 0:
        return "Sem dados"
    return f"{int(round(low)):,} – {int(round(high)):,} kcal/dia".replace(",", ".")


def _calc_hydration(peso: float, water: float, recomendado: float, urine_text: str) -> Dict[str, Any]:
    urine_norm = _strip_accents(urine_text)
    if any(term in urine_norm for term in ("transparente", "muito claro", "claro")):
        level = "ok"
    elif any(term in urine_norm for term in ("amarelo",)):
        level = "attention"
    elif any(term in urine_norm for term in ("escuro", "castanho")):
        level = "critical"
    else:
        level = "attention"

    threshold = peso * 0.03 if peso else 0.0
    if threshold and water and water < threshold:
        level = "critical" if level == "attention" else ("attention" if level == "ok" else level)

    score = {"ok": 100, "attention": 70, "critical": 40}.get(level, 70)
    message = {
        "ok": "Boa hidratação. Mantenha água ao longo do dia.",
        "attention": "Eleve o consumo de água e monitore a cor da urina.",
        "critical": "Reforce a hidratação imediatamente e procure orientação se persistir.",
    }[level]

    label = {"ok": "Ótimo", "attention": "Atenção", "critical": "Crítico"}[level]
    return {
        "level": level,
        "label": label,
        "score": score,
        "message": message,
        "water": water,
        "recommended": recomendado,
    }


def _calc_sleep(hours: Optional[float]) -> Dict[str, Any]:
    if hours is None:
        hours = 6.5
        inferred = True
    else:
        inferred = False
    if hours >= 7:
        level = "ok"
    elif hours >= 6:
        level = "attention"
    else:
        level = "critical"
    label = {"ok": "Ótimo", "attention": "Atenção", "critical": "Crítico"}[level]
    score = {"ok": 100, "attention": 70, "critical": 40}[level]
    message = {
        "ok": "Sono reparador: mantenha rotina consistente.",
        "attention": "Ajuste horários para atingir pelo menos 7h de sono.",
        "critical": "Sono curto: priorize higiene do sono e repouso noturno.",
    }[level]
    return {
        "level": level,
        "label": label,
        "score": score,
        "hours": hours,
        "message": message + (" (estimado)" if inferred else ""),
    }


def _calc_stress(respostas: Dict[str, Any], insights: Dict[str, Any]) -> Dict[str, Any]:
    raw = respostas.get("estresse") or insights.get("estresse")
    value = _to_float(raw)
    if value is None:
        value = 3
    if value <= 2:
        level = "ok"
        label = "Baixo"
        score = 90
        message = "Continue praticando estratégias que preservam sua calma."
    elif value == 3:
        level = "attention"
        label = "Médio"
        score = 70
        message = "Inclua pausas ativas e respiração para equilibrar o dia."
    else:
        level = "critical"
        label = "Alto"
        score = 45
        message = "Estresse elevado: considere técnicas de relaxamento e apoio profissional."
    return {
        "level": level,
        "label": label,
        "score": score,
        "value": value,
        "message": message,
    }


def _calc_activity(respostas: Dict[str, Any], treinado: bool) -> Dict[str, Any]:
    raw = respostas.get("nivel_atividade") or "Indefinido"
    normalized = _strip_accents(str(raw))
    if "sedent" in normalized:
        level = "critical"
        label = "Sedentário"
        score = 45
        message = "Inclua caminhadas leves e micro-movimentos ao longo do dia."
    elif any(term in normalized for term in ("leve", "baixa")):
        level = "attention"
        label = "Leve"
        score = 65
        message = "Gradualmente aumente sessões estruturadas para mais adaptação."
    elif any(term in normalized for term in ("moder", "media")):
        level = "ok"
        label = "Moderado"
        score = 80
        message = "Ótimo ritmo! Mantenha constância semanal."
    elif any(term in normalized for term in ("intens", "alto", "treino")) or treinado:
        level = "ok"
        label = "Intenso"
        score = 90
        message = "Perfil treinado: ajuste recuperação e ingestão proteica."
    else:
        level = "attention"
        label = raw if isinstance(raw, str) else "Indefinido"
        score = 60
        message = "Movimente-se diariamente para melhorar condicionamento."
    return {
        "level": level,
        "label": label,
        "score": score,
        "message": message,
    }


def _normalize_sign_name(sign: Optional[str]) -> str:
    return _strip_accents(sign or "").lower()


def _calc_bmi(peso: float, altura_cm: float, insights: Dict[str, Any]) -> Dict[str, Any]:
    imc = insights.get("bmi") or (peso / ((altura_cm / 100.0) ** 2) if peso and altura_cm else 0)
    categoria, badge_color = _imc_category(imc)
    score = {
        SUCCESS: 100,
        WARNING: 70,
        CRITICAL: 45,
    }.get(badge_color, 60)
    message = {
        "Peso normal": "IMC equilibrado. Foque em manter composição corporal.",
        "Abaixo do peso": "Avalie ajustes calóricos e acompanhamento clínico.",
        "Sobrepeso": "Ajuste calórico e atividade para reduzir gordura corporal.",
        "Obesidade": "Plano supervisionado para perda gradual de peso é prioridade.",
        "Indefinido": "Complete peso e altura para análise mais precisa.",
    }[categoria]
    return {
        "value": imc,
        "category": categoria,
        "score": score,
        "message": message,
        "color": badge_color,
    }


def _general_health_score(scores: Iterable[int]) -> Tuple[int, str, str]:
    values = [s for s in scores if isinstance(s, (int, float))]
    if not values:
        return 0, "Ajustar", CRITICAL
    mean = int(round(sum(values) / len(values)))
    if mean >= 80:
        return mean, "Ótimo", SUCCESS
    if mean >= 60:
        return mean, "Atenção", WARNING
    return mean, "Ajustar", CRITICAL


# ---------------------------------------------------------------------------
# Geração da imagem compartilhável
# ---------------------------------------------------------------------------


def _extract_first_name(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return "Paciente"
    first = re.split(r"\s+", text, maxsplit=1)[0]
    return first[:30]


def _calculate_age(raw: Any) -> int:
    text = str(raw or "").strip()
    if not text:
        return 30
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            birth = datetime.strptime(text, fmt).date()
            break
        except ValueError:
            continue
    else:
        return 30
    today = datetime.utcnow().date()
    years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    if years < 0 or years > 120:
        return 30
    return years


def _build_share_payload(
    respostas: Dict[str, Any],
    insights: Dict[str, Any],
    pilares_scores: Dict[str, Optional[int]],
    bmi: Dict[str, Any],
    score: int,
) -> Dict[str, Any]:
    primeiro_nome = _extract_first_name(respostas.get("nome") or respostas.get("nome_social"))
    idade = _calculate_age(respostas.get("data_nascimento"))
    signo = (respostas.get("signo") or insights.get("signo") or "Signo").strip() or "Signo"
    elemento = signo_elemento(signo)
    if elemento not in {"Fogo", "Água", "Terra", "Ar"}:
        elemento = "Ar"

    comportamentos = [item.strip() for item in collect_comportamentos(respostas) if item.strip()]
    comportamentos = comportamentos[:3]
    if not comportamentos:
        comportamentos = [
            "Hidrate-se ao longo do dia.",
            "Planeje refeições coloridas e equilibradas.",
        ]

    insight_frase = str(
        insights.get("sign_hint") or "Use seu signo como inspiração de hábitos saudáveis."
    ).strip()
    if not insight_frase:
        insight_frase = "Use seu signo como inspiração de hábitos saudáveis."

    imc_value = float(bmi.get("value") or insights.get("bmi") or 0.0)
    pilares_payload = {name: pilares_scores.get(name) for name in PILLAR_NAMES}
    hidratacao_score = float(pilares_scores.get("Hidratacao") or 0)
    return {
        "primeiro_nome": primeiro_nome,
        "idade": idade,
        "imc": imc_value,
        "score_geral": float(score or 0),
        "signo": signo,
        "elemento": elemento,
        "comportamentos": comportamentos,
        "insight_frase": insight_frase,
        "pilares_scores": pilares_payload,
    }


def _unique_lines(items: Iterable[Any]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        out.append(text)
        seen.add(text)
    return out


def _build_behavior_profile_content(
    respostas: Dict[str, Any],
    share_payload: Dict[str, Any],
    hydration: Dict[str, Any],
    sleep: Dict[str, Any],
    stress: Dict[str, Any],
    activity: Dict[str, Any],
    goal: str,
) -> Dict[str, Sequence[str]]:
    comportamentos = [item.strip() for item in share_payload.get("comportamentos", []) if str(item).strip()]

    energia = _unique_lines([activity.get("message"), sleep.get("message"), hydration.get("message")])
    emocional = _unique_lines([stress.get("message"), share_payload.get("insight_frase")])

    motivacao_raw = respostas.get("motivacao")
    decisao = _unique_lines(
        [
            f"Motivação declarada: {int(_to_float(motivacao_raw, motivacao_raw))}/5" if motivacao_raw else "",
            goal,
        ]
    )

    rotina = comportamentos[:3]
    destaques = comportamentos[3:] or rotina[:2] or emocional[:2] or energia[:2]

    return {
        "energia": energia or rotina[:2],
        "emocional": emocional or destaques[:2],
        "decisao": decisao or emocional[:2],
        "rotina": rotina or destaques,
        "destaques": destaques or comportamentos or energia[:2] or emocional[:2],
    }


def _build_recommendations(
    hydration: Dict[str, Any],
    sleep: Dict[str, Any],
    stress: Dict[str, Any],
    activity: Dict[str, Any],
    bmi: Dict[str, Any],
    state: str,
) -> Tuple[str, str]:
    suggestions: list[str] = []
    if hydration["score"] < 80:
        suggestions.append("Aumente ingestão hídrica e leve uma garrafa medida no dia a dia.")
    if sleep["score"] < 80:
        suggestions.append("Crie rotina de sono (luz baixa + alimentação leve à noite).")
    if stress["score"] < 80:
        suggestions.append("Inclua técnicas de respiração ou pausas ativas para reduzir estresse.")
    if bmi["score"] < 80:
        suggestions.append("Ajuste calorias e acompanhe medidas com apoio profissional.")
    if activity["score"] < 80:
        suggestions.append("Planeje treinos curtos porém frequentes (10–20 min/dia).")

    if not suggestions:
        suggestions.append("Continue consistente: hidratação + refeições equilibradas consolidam resultados.")
    if len(suggestions) == 1:
        if state == "S1":
            suggestions.append("Libere o plano completo para estratégias personalizadas de longo prazo.")
        else:
            suggestions.append("Use o plano IA para variar cardápios e manter aderência.")
    return suggestions[0], suggestions[1]


def _format_timestamp(raw: Any) -> str:
    if not raw:
        return "—"
    text = str(raw)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:  # pragma: no cover - defensive parse
        return text


# ---------------------------------------------------------------------------
# Renderização (HTML/CSS)
# ---------------------------------------------------------------------------


def _inject_style() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --primary: {PRIMARY};
            --success: {SUCCESS};
            --warning: {WARNING};
            --critical: {CRITICAL};
            --neutral: {NEUTRAL};
        }}
        .band {{
            border-radius: 18px;
            padding: 18px 22px;
            margin-bottom: 18px;
            background: linear-gradient(145deg, rgba(108,93,211,0.08), rgba(255,255,255,0.95));
            border: 1px solid rgba(108,93,211,0.12);
            box-shadow: 0 14px 32px rgba(108, 93, 211, 0.08);
        }}
        .band-header {{ display:flex; flex-wrap:wrap; gap:18px; align-items:center; }}
        .pill {{
            padding:6px 14px; border-radius:999px; font-weight:600; font-size:0.85rem;
            background: rgba(108,93,211,0.12); color:{PRIMARY};
        }}
        .pill.s1 {{ background: rgba(244,162,97,0.18); color:{WARNING}; }}
        .pill.s2 {{ background: rgba(40,180,135,0.18); color:{SUCCESS}; }}
        .pill.s3 {{ background: rgba(231,111,81,0.18); color:{CRITICAL}; }}
        .header-metric {{ font-size:0.95rem; color:#4a4a68; margin-right:18px; }}
        .header-metric span {{ display:block; font-weight:700; color:#1f1f3d; font-size:1.05rem; }}
        .kcal-card {{
            border-radius:16px; padding:18px; background:#fff;
            border:1px solid rgba(108,93,211,0.16);
            box-shadow:0 10px 20px rgba(108,93,211,0.06);
            margin-bottom:18px;
        }}
        .kcal-card h3 {{ margin:0; font-size:1rem; color:#2d2a44; }}
        .kcal-card .value {{ font-size:2.2rem; font-weight:700; color:{PRIMARY}; margin:6px 0; }}
        .kcal-card .meta {{ font-size:0.85rem; color:#5b5d7a; }}
        .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; }}
        .kpi {{
            background:#fff; border-radius:14px; border:1px solid rgba(108,93,211,0.12);
            padding:14px; box-shadow:0 6px 14px rgba(108,93,211,0.04);
        }}
        .kpi .label {{ font-size:0.82rem; text-transform:uppercase; letter-spacing:0.08em; color:#7a7c9f; }}
        .kpi .value {{ font-size:1.4rem; font-weight:700; margin-top:6px; color:#1f1f3d; }}
        .kpi .sub {{ font-size:0.85rem; color:#5b5d7a; margin-top:4px; }}
        .kpi.ok {{ border-left:4px solid {SUCCESS}; }}
        .kpi.attention {{ border-left:4px solid {WARNING}; }}
        .kpi.critical {{ border-left:4px solid {CRITICAL}; }}
        .kpi.neutral {{ border-left:4px solid {PRIMARY}; }}
        .score-card {{
            background:#fff; border-radius:18px; border:1px solid rgba(108,93,211,0.18);
            padding:22px; box-shadow:0 18px 32px rgba(108,93,211,0.08);
        }}
        .score-card .score {{ font-size:3rem; font-weight:800; color:{PRIMARY}; margin:0; }}
        .score-badge {{
            display:inline-block; padding:4px 12px; border-radius:999px; font-weight:600; font-size:0.85rem;
        }}
        .score-badge.ok {{ background: rgba(40,180,135,0.14); color:{SUCCESS}; }}
        .score-badge.attention {{ background: rgba(244,162,97,0.16); color:{WARNING}; }}
        .score-badge.critical {{ background: rgba(231,111,81,0.16); color:{CRITICAL}; }}
        .score-card ul {{ padding-left:18px; margin:12px 0 0 0; color:#4c4f6b; }}
        .mini-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; }}
        .mini-card {{ background:#fff; border-radius:14px; padding:16px; border:1px solid rgba(108,93,211,0.1); box-shadow:0 6px 14px rgba(108,93,211,0.04); }}
        .mini-card h4 {{ margin:0 0 8px 0; font-size:1rem; color:#2d2a44; }}
        .mini-card p {{ margin:0; font-size:0.9rem; color:#565778; }}
        .behavior-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:16px; margin:18px 0; }}
        .behavior-card {{
            background:#fff; border-radius:18px; border:1px solid rgba(108,93,211,0.12);
            padding:18px; box-shadow:0 14px 28px rgba(108,93,211,0.08);
            display:flex; flex-direction:column; gap:10px;
        }}
        .behavior-card .card-icon {{
            width:48px; height:48px; border-radius:14px; background:rgba(108,93,211,0.12);
            display:flex; align-items:center; justify-content:center; font-size:1.6rem; color:{PRIMARY}; gap:6px;
        }}
        .behavior-card .card-title {{ font-weight:700; font-size:0.95rem; color:#2d2a44; }}
        .behavior-card .card-subtitle {{ font-size:0.82rem; color:#6b6d86; text-transform:uppercase; letter-spacing:0.08em; }}
        .behavior-card ul {{ margin:0; padding-left:18px; color:#4a4c66; font-size:0.9rem; display:flex; flex-direction:column; gap:6px; }}
        .behavior-card li {{ margin:0; line-height:1.35; }}
        .behavior-card .card-cta {{ margin:4px 0 0 0; font-size:0.82rem; color:{PRIMARY}; font-weight:600; }}
        .behavior-card .card-note {{ margin:0; font-size:0.82rem; color:#4b4d6a; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Renderização de seções
# ---------------------------------------------------------------------------


def _render_header(state_info: Dict[str, str], pac_id: str, payload: Dict[str, Any]) -> None:
    updated_at = _format_timestamp(payload.get("updated_at"))
    created_at = _format_timestamp(payload.get("created_at"))
    state = state_info["state"].lower()
    pac_short = pac_id[:8] if pac_id else "—"
    st.markdown(
        f"""
        <div class='band band-header'>
            <div class='pill s{state}'>{'Pendente' if state=='s1' else ('Pago' if state=='s2' else 'Erro IA')}</div>
            <div class='header-metric'>Pac ID<br><span>{html.escape(pac_short)}</span></div>
            <div class='header-metric'>Atualizado em<br><span>{html.escape(updated_at)}</span></div>
            <div class='header-metric'>Criado em<br><span>{html.escape(created_at)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kcal_card(info: Dict[str, Any]) -> None:
    goal_label = {
        "emagrecer": "Emagrecimento",
        "manter": "Manutenção",
        "ganhar": "Ganho de massa",
    }[info["goal"]]
    st.markdown(
        f"""
        <div class='kcal-card'>
            <h3>Kcal de bolso · {html.escape(info['perfil'])} · {html.escape(goal_label)}</h3>
            <div class='value'>{html.escape(info['target_display'])} kcal/dia</div>
            <div class='meta'>Faixa sugerida: {html.escape(info['range_display'])} · Base: {html.escape(info['per_kg'])} · Fonte: {html.escape(info['source'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(kpis: Iterable[Dict[str, str]]) -> None:
    blocks = []
    for item in kpis:
        blocks.append(
            f"<div class='kpi {item['status']}'><div class='label'>{html.escape(item['label'])}</div>"
            f"<div class='value'>{html.escape(item['value'])}</div>"
            f"<div class='sub'>{html.escape(item['sub'])}</div></div>"
        )
    st.markdown(f"<div class='kpi-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def _render_health_score(score: int, badge: str, badge_color: str, rec1: str, rec2: str) -> None:
    badge_class = "ok" if badge_color == SUCCESS else ("critical" if badge_color == CRITICAL else "attention")
    st.markdown(
        f"""
        <div class='score-card' style="margin-top: 18px; margin-bottom: 18px; padding: 16px;">
            <div class='score'>{score}</div>
            <span class='score-badge {badge_class}'>{html.escape(badge)}</span>
            <ul>
                <li>{html.escape(rec1)}</li>
                <li>{html.escape(rec2)}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_behavior_card_content(sign: Optional[str], goal: str) -> Dict[str, Any]:
    element = signo_elemento(sign or "")
    element_bullets = ELEMENT_BEHAVIOR.get(
        element,
        (
            "Fortaleça rotina alimentar com pequenos rituais diários.",
            "Use lembretes simples para manter constância.",
        ),
    )
    sign_key = _normalize_sign_name(sign)
    sign_bullets = SIGN_BEHAVIOR.get(
        sign_key,
        (
            "Adote registro rápido das refeições para manter foco.",
            "Observe gatilhos de excesso e prepare alternativas leves.",
        ),
    )
    goal_bullet = GOAL_DIRECTIVES.get(goal, GOAL_DIRECTIVES["manter"])
    return {
        "symbol": signo_symbol(sign or ""),
        "element": element or "—",
        "element_icon": element_icon(element or ""),
        "bullets": [*element_bullets, *sign_bullets, goal_bullet],
    }


def _habit_activity_line(activity: Dict[str, Any], goal: str) -> str:
    level = activity.get("level")
    label = str(activity.get("label") or "atividade")
    focus = GOAL_ACTIVITY_FOCUS.get(goal, GOAL_ACTIVITY_FOCUS["manter"])
    if level == "critical":
        return f"Programe 3 caminhadas de 15' na semana para ativar {focus}."
    if level == "attention":
        return f"Confirme 2 treinos guiados/semana para reforçar {focus}."
    if level == "ok":
        return f"Mantenha {label.lower()} e ajuste cargas para sustentar {focus}."
    return f"Movimente-se diariamente para proteger {focus}."


def _habit_recovery_line(sleep: Dict[str, Any], stress: Dict[str, Any], goal: str) -> str:
    sleep_level = sleep.get("level")
    stress_level = stress.get("level")
    focus = GOAL_RECOVERY.get(goal, GOAL_RECOVERY["manter"])
    if sleep_level == "critical":
        return f"Crie ritual sem telas 20' antes de dormir para proteger {focus}."
    if sleep_level == "attention":
        return f"Defina horário fixo de sono e luz baixa para garantir {focus}."
    if stress_level == "critical":
        return f"Pratique respiração 4-7-8 após refeições para estabilizar {focus}."
    if stress_level == "attention":
        return f"Planeje pausas de respiração profunda para sustentar {focus}."
    return f"Mantenha pausas e sono regular para cuidar de {focus}."


def _build_habit_suggestions(
    sign: Optional[str],
    goal: str,
    activity: Dict[str, Any],
    sleep: Dict[str, Any],
    stress: Dict[str, Any],
    state: str,
) -> Dict[str, Any]:
    sign_key = _normalize_sign_name(sign)
    action_template = SIGN_ACTIONS.get(
        sign_key,
        "Use rituais rápidos antes das refeições para manter {goal_focus}.",
    )
    first = action_template.format(goal_focus=GOAL_FOCUS.get(goal, GOAL_FOCUS["manter"]))
    second = _habit_activity_line(activity, goal)
    third = _habit_recovery_line(sleep, stress, goal)
    cta = CTA_TEXT.get(state, CTA_TEXT["S2"])
    return {
        "bullets": [first, second, third],
        "cta": cta,
    }


def _build_health_certificate(
    hydration: Dict[str, Any],
    sleep: Dict[str, Any],
    stress: Dict[str, Any],
    activity: Dict[str, Any],
    bmi: Dict[str, Any],
    score: int,
    badge: str,
    state: str,
) -> Dict[str, Any]:
    water = hydration.get("water")
    recommended = hydration.get("recommended")
    water_display = (
        f"{water:.1f} L / {recommended:.1f} L"
        if isinstance(water, (int, float)) and isinstance(recommended, (int, float))
        else "—"
    )
    sleep_hours = sleep.get("hours")
    sleep_display = (
        f"{sleep_hours:.1f} h"
        if isinstance(sleep_hours, (int, float))
        else "—"
    )
    stress_value = stress.get("value")
    stress_display = (
        f"{stress['label']} ({stress_value:.0f}/5)"
        if isinstance(stress_value, (int, float))
        else stress.get("label", "—")
    )
    bmi_value = bmi.get("value")
    bmi_display = (
        f"{bmi_value:.1f}"
        if isinstance(bmi_value, (int, float)) and bmi_value > 0
        else "—"
    )
    bullets = [
        f"Hidratação: {hydration.get('label', '—')} ({water_display})",
        f"Sono: {sleep_display} · {sleep.get('label', '—')}",
        f"Estresse: {stress_display}",
        f"Atividade: {activity.get('label', '—')}",
        f"IMC: {bmi_display} · {bmi.get('category', '—')}",
    ]
    metrics_for_focus = [
        ("Hidratação", hydration.get("score", 0)),
        ("Sono", sleep.get("score", 0)),
        ("Estresse", stress.get("score", 0)),
        ("Atividade", activity.get("score", 0)),
        ("IMC", bmi.get("score", 0)),
    ]
    focus_metric = min(
        metrics_for_focus,
        key=lambda item: item[1] if isinstance(item[1], (int, float)) else 100,
    )
    focus_text = FOCUS_STEPS.get(
        focus_metric[0],
        "consultar o plano para próximos ajustes.",
    )
    note = f"Nota geral: {badge} ({score}/100). Próximo melhor passo: {focus_text}"
    cta = CTA_TEXT.get(state, CTA_TEXT["S2"])
    return {
        "bullets": bullets,
        "note": note,
        "cta": cta,
    }


def _render_behavior_cards(
    state: str,
    sign: Optional[str],
    goal: str,
    hydration: Dict[str, Any],
    sleep: Dict[str, Any],
    stress: Dict[str, Any],
    activity: Dict[str, Any],
    bmi: Dict[str, Any],
    score: int,
    badge: str,
) -> None:
    behavior_content = _build_behavior_card_content(sign, goal)
    habits_content = _build_habit_suggestions(sign, goal, activity, sleep, stress, state)
    certificate_content = _build_health_certificate(
        hydration,
        sleep,
        stress,
        activity,
        bmi,
        score,
        badge,
        state,
    )
    card1_list = "".join(
        f"<li>{html.escape(item)}</li>" for item in behavior_content["bullets"]
    )
    card2_list = "".join(
        f"<li>{html.escape(item)}</li>" for item in habits_content["bullets"]
    )
    card3_list = "".join(
        f"<li>{html.escape(item)}</li>" for item in certificate_content["bullets"]
    )
    st.markdown(
        f"""
        <div class='behavior-grid'>
          <div class='behavior-card'>
            <div class='card-icon'>{html.escape(str(behavior_content['symbol']))} <span>{html.escape(str(behavior_content['element_icon']))}</span></div>
            <div class='card-title'>Comportamento por Signo &amp; Elemento</div>
            <div class='card-subtitle'>{html.escape(behavior_content['element'])}</div>
            <ul>{card1_list}</ul>
          </div>
          <div class='behavior-card'>
            <div class='card-icon'>🧭</div>
            <div class='card-title'>Hábitos Sugeridos (Comportamentais)</div>
            <ul>{card2_list}</ul>
            <p class='card-cta'>{html.escape(habits_content['cta'])}</p>
          </div>
          <div class='behavior-card'>
            <div class='card-icon'>🩺</div>
            <div class='card-title'>Atestado de Saúde</div>
            <ul>{card3_list}</ul>
            <p class='card-note'>{html.escape(certificate_content['note'])}</p>
            <p class='card-cta'>{html.escape(certificate_content['cta'])}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_interpretations(cards: Iterable[Tuple[str, str]]) -> None:
    blocks = []
    for title, body in cards:
        blocks.append(
            f"<div class='mini-card'><h4>{html.escape(title)}</h4><p>{html.escape(body)}</p></div>"
        )
    st.markdown(f"<div class='mini-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Plano alimentar e ações
# ---------------------------------------------------------------------------


def _render_actions(
    state: str,
    pac_id: str,
    insights: Dict[str, Any],
    payload: Dict[str, Any],
    pdf_bytes: bytes,
    share_bytes: bytes,
    behavior_bytes: bytes | None = None,
) -> None:
    # Espaço vertical antes do bloco de ações
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    if state == "S1":
        cols = st.columns(4 if behavior_bytes else 3, gap="medium")
        payment_url = payload.get("payment_url") or payload.get("checkout_url")

        with cols[0]:
            if payment_url:
                st.link_button("Liberar Plano Completo", payment_url, type="primary")
            else:
                if st.button("Liberar Plano Completo", type="primary"):
                    _redirect_to_form(pac_id)

        with cols[1]:
            st.download_button(
                "PDF Resumo",
                data=pdf_bytes,
                file_name=f"nutrisigno_{pac_id[:8]}_resumo.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with cols[2]:
            st.download_button(
                "Compartilhar resultado",
                data=share_bytes,
                file_name=f"nutrisigno_{pac_id[:8]}_share.png",
                mime="image/png",
                use_container_width=True,
            )

        if behavior_bytes:
            with cols[3]:
                st.download_button(
                    "Perfil comportamental",
                    data=behavior_bytes,
                    file_name=f"nutrisigno_{pac_id[:8]}_comportamental.png",
                    mime="image/png",
                    use_container_width=True,
                )

        # Espaço depois do bloco (não colar no texto/alerta seguinte)
        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
        return

    # Estado com plano IA disponível
    cols = st.columns(5 if behavior_bytes else 4, gap="medium")

    with cols[0]:
        if st.button("Plano IA", type="primary"):
            st.toast("Confira a aba 'Cardápio base' logo abaixo.")

    with cols[1]:
        if st.button("Substituições ±2%"):
            st.toast("Veja a aba de substituições para trocas inteligentes.")

    with cols[2]:
        pdf_completo = payload.get("pdf_completo_url") or payload.get("pdf_url_completo")
        if pdf_completo:
            st.link_button("PDF Completo", pdf_completo)
        else:
            st.download_button(
                "PDF Completo (resumo)",
                data=pdf_bytes,
                file_name=f"nutrisigno_{pac_id[:8]}_completo.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    with cols[3]:
        st.download_button(
            "Compartilhar resultado",
            data=share_bytes,
            file_name=f"nutrisigno_{pac_id[:8]}_share.png",
            mime="image/png",
            use_container_width=True,
        )

    if behavior_bytes:
        with cols[4]:
            st.download_button(
                "Perfil comportamental",
                data=behavior_bytes,
                file_name=f"nutrisigno_{pac_id[:8]}_comportamental.png",
                mime="image/png",
                use_container_width=True,
            )

    # Espaço depois do bloco de ações (versão paga)
    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)


def _redirect_to_form(pac_id: str) -> None:
    st.session_state.step = 7
    save_client_state(pac_id, "7")
    try:
        st.switch_page("pages/01_Formulario.py")
    except Exception:  # pragma: no cover - fallback
        try:
            params = st.experimental_get_query_params()
            params["page"] = "01_Formulario"
            st.experimental_set_query_params(**params)
            st.experimental_rerun()
        except Exception:
            st.info("Use o menu lateral para abrir o formulário na etapa de pagamento.")
            st.stop()


def _render_plan_sections(state: str, payload: Dict[str, Any]) -> None:
    if state == "S1":
        st.info("Plano completo será liberado automaticamente após confirmação do pagamento.")
        return
    if state == "S3":
        st.error("Não conseguimos gerar o Plano completo automaticamente neste momento.")
        st.warning("Erro técnico. Nossa equipe já foi notificada; tente novamente mais tarde.")
        return

    st.markdown("### Plano NutriSigno pós-pagamento")

    plano_ia = payload.get("plano_ia") or {}
    substituicoes = payload.get("substituicoes") or {}
    combos = payload.get("cardapio_ia") or {}
    pdf_completo = payload.get("pdf_completo_url")

    cols = st.columns(3, gap="large")

    with cols[0]:
        kcal_alvo = plano_ia.get("kcal_alvo")
        kcal_pdf = plano_ia.get("kcal")
        arquivo = Path(str(plano_ia.get("arquivo") or "")).name or "—"
        st.markdown(
            f"""
            <div class='card'>
              <div class='card-title'>Seu Plano Alimentar</div>
              <p class='sub'>Base PDF selecionada</p>
              <div class='kpi'>{kcal_pdf or '—'} kcal</div>
              <p class='sub'>Alvo calculado: {kcal_alvo or '—'} kcal/dia</p>
              <p class='sub'>Arquivo base: {arquivo}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if pdf_completo:
            st.link_button("Baixar PDF consolidado", pdf_completo, use_container_width=True)
        else:
            st.caption("PDF consolidado será disponibilizado ao concluir o processamento.")

    with cols[1]:
        categorias = substituicoes.get("categorias") or []
        if categorias:
            resumo = "<br/>".join(
                f"{html.escape(cat['categoria'])} · {len(cat.get('itens', []))} itens"
                for cat in categorias[:4]
            )
        else:
            resumo = "Nenhuma categoria vinculada."
        st.markdown(
            f"""
            <div class='card'>
              <div class='card-title'>Substituições vinculadas</div>
              <p class='sub'>{resumo}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if categorias:
            with st.expander("Ver tabela completa"):
                for categoria in categorias:
                    st.markdown(f"**{categoria['categoria']}** — {categoria.get('descricao','')}")
                    refeicoes = categoria.get("refeicoes") or []
                    if refeicoes:
                        st.markdown(
                            ", ".join(
                                f"{item['refeicao']}: {item['porcao']}" for item in refeicoes
                            )
                        )
                    for item in categoria.get("itens", []):
                        detalhe = f" ({item['porcao']})" if item.get("porcao") else ""
                        st.markdown(f"- {item['nome']}{detalhe}")
        else:
            st.caption("Substituições serão preenchidas após o processamento completo.")

    with cols[2]:
        combos_list = combos.get("combos") or []
        timestamp = combos.get("timestamp")
        versao = combos.get("versao")
        st.markdown(
            f"""
            <div class='card'>
              <div class='card-title'>Sugestões IA</div>
              <p class='sub'>Versão {versao or '—'} · {timestamp or '—'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if combos_list:
            for combo in combos_list:
                refeicao = combo.get("refeicao", "—").capitalize()
                texto = combo.get("combo", "")
                st.markdown(f"**{refeicao}:** {texto}")
        else:
            st.caption("Sugestões ainda não disponíveis. Assim que processadas, aparecerão aqui.")


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title="Meu Resultado", page_icon="📊", layout="wide")

    pac_id = _resolve_pac_id()
    if not pac_id:
        st.error("Não foi possível identificar o seu painel.")
        st.caption("Refaça o acesso informando telefone e data de nascimento.")
        st.page_link("pages/0_Acessar_Resultados.py", label="Voltar para Acessar Resultados", icon="↩️")
        return

    payload = _load_payload(pac_id)
    if not payload:
        st.error("Não encontramos dados associados a este identificador.")
        st.page_link("pages/0_Acessar_Resultados.py", label="Voltar para Acessar Resultados", icon="↩️")
        return

    save_client_state(pac_id, str(st.session_state.get("step") or ""))

    respostas = st.session_state.get("data") or payload.get("respostas") or {}
    plan = st.session_state.get("plan") or payload.get("plano_alimentar") or {}

    def _persist_pilares(scores: Dict[str, Optional[int]]) -> None:
        repo.save_pilares_scores(pac_id, scores)

    pilares_scores = ensure_pilares_scores(
        payload,
        respostas=respostas,
        persist=_persist_pilares if pac_id else None,
    )
    st.session_state.pilares_scores = pilares_scores

    _inject_style()

    st.title("📊 Resultado NutriSigno")
    st.caption("Acompanhe métricas-chave e próximos passos do seu plano.")

    insights, ai_summary = _prepare_insights(respostas)

    state_info = _resolve_status(payload)
    _render_header(state_info, pac_id, payload)

    peso = float(respostas.get("peso") or 0.0)
    altura_cm = float(respostas.get("altura") or 0.0)
    goal = _infer_goal(respostas)
    treinado = _is_trained(respostas)

    kcal_info = _calc_kcal_info(peso, goal, treinado, respostas, payload)
    _render_kcal_card(kcal_info)

    bmi = _calc_bmi(peso, altura_cm, insights)
    water_value = _to_float(insights.get("consumption", {}).get("water_liters"))
    if water_value is None:
        water_value = _to_float(respostas.get("consumo_agua")) or 0.0
    recommended_value = _to_float(insights.get("consumption", {}).get("recommended_liters"))
    if recommended_value is None:
        recommended_value = max(1.5, peso * 0.035)
    hydration = _calc_hydration(
        peso,
        water_value,
        recommended_value,
        extract_cor_urina(respostas.get("cor_urina"), insights.get("urine", "")),
    )
    sleep = _calc_sleep(_extract_sleep_hours(respostas))
    stress = _calc_stress(respostas, insights)
    activity = _calc_activity(respostas, treinado)

    kpis = [
        {
            "label": "Kcal alvo",
            "value": f"{kcal_info['target_display']} kcal",
            "sub": f"Fonte: {kcal_info['source']}",
            "status": "neutral",
        },
        {
            "label": "IMC",
            "value": f"{bmi['value']:.1f}" if bmi["value"] else "—",
            "sub": bmi["category"],
            "status": "ok" if bmi["category"] == "Peso normal" else ("critical" if bmi["category"] == "Obesidade" else "attention"),
        },
        {
            "label": "Hidratação",
            "value": hydration["label"],
            "sub": f"{hydration['water']:.1f} L / {hydration['recommended']:.1f} L",
            "status": hydration["level"],
        },
        {
            "label": "Sono (h)",
            "value": f"{sleep['hours']:.1f} h",
            "sub": sleep["label"],
            "status": sleep["level"],
        },
        {
            "label": "Estresse",
            "value": f"{stress['label']} ({stress['value']:.0f}/5)",
            "sub": "Autoavaliação",
            "status": stress["level"],
        },
        {
            "label": "Atividade",
            "value": activity["label"],
            "sub": "Perfil diário",
            "status": activity["level"],
        },
    ]
    _render_kpis(kpis)

    score, badge, badge_color = _general_health_score(pilares_scores.values())
    rec1, rec2 = _build_recommendations(hydration, sleep, stress, activity, bmi, state_info["state"])
    _render_health_score(score, badge, badge_color, rec1, rec2)

    _render_behavior_cards(
        state_info["state"],
        respostas.get("signo"),
        goal,
        hydration,
        sleep,
        stress,
        activity,
        bmi,
        score,
        badge,
    )

    bristol_label = extract_bristol_tipo(
        respostas.get("tipo_fezes_bristol") or respostas.get("tipo_fezes"),
        insights.get("bristol", ""),
    )
    bristol_norm = _strip_accents(bristol_label)
    if any(term in bristol_norm for term in ("tipo 3", "tipo 4")):
        bristol_message = "Eliminação adequada; mantenha fibras variadas e hidratação."
    elif any(term in bristol_norm for term in ("tipo 1", "tipo 2")):
        bristol_message = "Fezes ressecadas: aumente água, frutas e fibras solúveis."
    elif any(term in bristol_norm for term in ("tipo 5", "tipo 6", "tipo 7")):
        bristol_message = "Fezes moles: priorize alimentos adstringentes e avalie intolerâncias."
    else:
        bristol_message = insights.get("bristol", "Monitore sua digestão com atenção.")

    interpretations = [
        ("Urina", hydration["message"]),
        ("Fezes (Bristol)", bristol_message),
        ("Sono", sleep["message"]),
        ("Atividade", activity["message"]),
    ]
    _render_interpretations(interpretations)

    pdf_bytes = build_insights_pdf_bytes(insights)
    share_payload = _build_share_payload(respostas, insights, pilares_scores, bmi, score)
    share_bytes = gerar_imagem_share(share_payload, formato="story")
    behavior_bytes: bytes | None = None
    try:
        behavior_content = _build_behavior_profile_content(
            respostas,
            share_payload,
            hydration,
            sleep,
            stress,
            activity,
            goal,
        )
        behavior_regente = str(
            respostas.get("regente")
            or respostas.get("planeta_regente")
            or respostas.get("regente_signo")
            or "—"
        )
        behavior_bytes = gerar_card_comportamental_bytes(
            nome=share_payload["primeiro_nome"],
            idade=share_payload["idade"],
            signo=share_payload["signo"],
            elemento=share_payload["elemento"],
            regente=behavior_regente,
            dados_comportamento=behavior_content,
            caminho_simbolo_signo=None,
            fallback_symbol=signo_symbol(share_payload["signo"]),
        )
    except Exception:  # pragma: no cover - geração gráfica opcional
        log.exception("Falha ao gerar imagem comportamental.")
    _render_actions(state_info["state"], pac_id, insights, payload, pdf_bytes, share_bytes, behavior_bytes)

    if state_info["state"] != "S1" and ai_summary:
        with st.expander("Resumo IA (educativo)"):
            st.write(ai_summary)

    _render_plan_sections(state_info["state"], payload)

    st.caption("Compartilhe apenas com pessoas de confiança. NutriSigno é um apoio educativo, não substitui acompanhamento clínico.")


if __name__ == "__main__":
    main()
