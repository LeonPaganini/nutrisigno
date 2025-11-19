"""Centraliza o contexto de resultados do NutriSigno.

Este módulo conecta o motor de métricas (`metrics_engine.calcular_pilares`)
com as camadas de UI e exportação. Ele expõe funções utilitárias para
calcular os pilares uma única vez, normalizar valores persistidos e
disponibilizar o dicionário `pilares_scores` em toda a aplicação.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping

from .metrics_engine import calcular_pilares

PILLAR_NAMES = ("Energia", "Digestao", "Sono", "Hidratacao", "Emocao", "Rotina")


def empty_pilares_scores() -> Dict[str, int]:
    """Retorna um dicionário com todos os pilares zerados."""

    return {name: 0 for name in PILLAR_NAMES}


def normalize_pilares_scores(raw_scores: Mapping[str, Any] | None) -> Dict[str, int]:
    """Normaliza um dicionário arbitrário de pilares para inteiros 0-100."""

    if raw_scores is None:
        return empty_pilares_scores()

    normalized: Dict[str, int] = {}
    for name in PILLAR_NAMES:
        value = raw_scores.get(name, 0) if isinstance(raw_scores, Mapping) else 0
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        normalized[name] = int(max(0, min(100, round(numeric))))
    return normalized


def compute_pilares_scores(respostas: Mapping[str, Any] | None) -> Dict[str, int]:
    """Executa o motor de métricas e aplica normalização defensiva."""

    if not respostas:
        return empty_pilares_scores()
    resultados = calcular_pilares(dict(respostas))
    return normalize_pilares_scores(resultados)


def ensure_pilares_scores(
    payload: Dict[str, Any],
    *,
    respostas: Mapping[str, Any] | None = None,
    persist: Callable[[Dict[str, int]], None] | None = None,
) -> Dict[str, int]:
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
