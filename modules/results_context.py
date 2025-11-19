"""Centraliza o contexto de resultados do NutriSigno.

Este módulo conecta o motor de métricas (`metrics_engine.calcular_pilares`)
com as camadas de UI e exportação. Ele expõe funções utilitárias para
calcular os pilares uma única vez, normalizar valores persistidos e
disponibilizar o dicionário `pilares_scores` em toda a aplicação.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

from .metrics_engine import calcular_pilares

PILLAR_NAMES = ("Energia", "Digestao", "Sono", "Hidratacao", "Emocao", "Rotina")


def empty_pilares_scores() -> Dict[str, Optional[int]]:
    """Retorna um dicionário com todos os pilares sem cálculo."""

    return {name: None for name in PILLAR_NAMES}


def normalize_pilares_scores(raw_scores: Mapping[str, Any] | None) -> Dict[str, Optional[int]]:
    """Normaliza um dicionário arbitrário de pilares para inteiros 0-100."""

    if raw_scores is None or not isinstance(raw_scores, Mapping):
        return empty_pilares_scores()

    normalized: Dict[str, Optional[int]] = {}
    for name in PILLAR_NAMES:
        value = raw_scores.get(name)
        if value in (None, "", "None"):
            normalized[name] = None
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            normalized[name] = None
            continue
        numeric = max(0.0, min(100.0, numeric))
        normalized[name] = int(round(numeric))
    return normalized


def compute_pilares_scores(respostas: Mapping[str, Any] | None) -> Dict[str, Optional[int]]:
    """Executa o motor de métricas e aplica normalização defensiva."""

    if not respostas:
        return empty_pilares_scores()
    resultados = calcular_pilares(dict(respostas))
    return normalize_pilares_scores(resultados)


def ensure_pilares_scores(
    payload: Dict[str, Any],
    *,
    respostas: Mapping[str, Any] | None = None,
    persist: Callable[[Dict[str, Optional[int]]], None] | None = None,
) -> Dict[str, Optional[int]]:
    """Garante que `payload['pilares_scores']` exista e esteja normalizado."""

    stored_candidates = [
        payload.get("pilares_scores"),
        (payload.get("plano_alimentar_compacto") or {}).get("pilares_scores"),
        (payload.get("resultados") or {}).get("pilares_scores"),
    ]
    for candidate in stored_candidates:
        if isinstance(candidate, Mapping) and candidate:
            normalized = normalize_pilares_scores(candidate)
            payload["pilares_scores"] = normalized
            return normalized

    respostas_ref = respostas if respostas is not None else payload.get("respostas")
    normalized = compute_pilares_scores(respostas_ref)

    if persist is not None:
        try:
            persist(normalized)
        except Exception:
            # Persistência é opcional; falhas não devem quebrar o fluxo da UI.
            pass

    payload["pilares_scores"] = normalized
    return normalized


__all__ = [
    "PILLAR_NAMES",
    "compute_pilares_scores",
    "empty_pilares_scores",
    "ensure_pilares_scores",
    "normalize_pilares_scores",
]
