"""UI helpers dedicated to the insights dashboard."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Dict, List, Tuple

import plotly.graph_objects as go
import streamlit as st

from .ui_sections import SIGNO_META, _to_float

DASH_MUTED = "#6b7280"

ZODIAC_SYMBOLS = {
    "áries": "♈︎",
    "touro": "♉︎",
    "gêmeos": "♊︎",
    "gemeos": "♊︎",
    "câncer": "♋︎",
    "cancer": "♋︎",
    "leão": "♌︎",
    "leao": "♌︎",
    "virgem": "♍︎",
    "libra": "♎︎",
    "escorpião": "♏︎",
    "escorpiao": "♏︎",
    "sagitário": "♐︎",
    "sagitario": "♐︎",
    "capricórnio": "♑︎",
    "capricornio": "♑︎",
    "aquário": "♒︎",
    "aquario": "♒︎",
    "peixes": "♓︎",
}

ELEMENT_MAP = {
    "Terra": {"touro", "virgem", "capricornio", "capricórnio"},
    "Ar": {"gêmeos", "gemeos", "libra", "aquário", "aquario"},
    "Fogo": {"áries", "aries", "leão", "leao", "sagitário", "sagitario"},
    "Água": {"câncer", "cancer", "escorpião", "escorpiao", "peixes"},
}

ELEMENT_ICONS = {
    "Terra": "🜃",
    "Ar": "🜁",
    "Fogo": "🜂",
    "Água": "🜄",
}

IMC_FAIXAS = [
    ("Magreza", 0.0, 18.5, "#7aa6f9"),
    ("Normal", 18.5, 25.0, "#55c169"),
    ("Sobrepeso", 25.0, 30.0, "#ffb347"),
    ("Obesidade I", 30.0, 35.0, "#ff7f50"),
    ("Obesidade II/III", 35.0, 60.0, "#e74c3c"),
]


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn").lower()


def imc_categoria_cor(imc: float) -> Tuple[str, str]:
    for nome, lo, hi, cor in IMC_FAIXAS:
        if lo <= imc < hi:
            return nome, cor
    return "Indefinido", "#95a5a6"


def signo_symbol(signo: str) -> str:
    return ZODIAC_SYMBOLS.get((signo or "").strip().lower(), "✦")


def signo_elemento(signo: str) -> str:
    normalized = _strip_accents((signo or "").strip().lower())
    for elemento, conj in ELEMENT_MAP.items():
        if normalized in conj:
            return elemento
    return "—"


def element_icon(elemento: str) -> str:
    return ELEMENT_ICONS.get(elemento, "◆")


def dashboard_style() -> None:
    st.markdown(
        f"""
        <style>
        .card {{
          background:#fff;border:1px solid #e6e6e6;border-radius:12px;
          padding:14px;box-shadow:0 2px 10px rgba(0,0,0,0.04);
        }}
        .card-title {{
          font-weight:700;font-size:0.95rem;color:#2c3e50;margin-bottom:8px;
        }}
        .square {{
          aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;
          font-size:64px;font-weight:700;border-radius:16px;border:1px dashed #e5e7eb;
          background:#fbfcfd;
        }}
        .square-element {{
          aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;
          font-size:56px;font-weight:700;border-radius:16px;border:1px dashed #e5e7eb;
          background:#fafbff;
        }}
        .small-muted {{ color:#718096;font-size:0.82rem;text-align:center;margin-top:6px;}}
        .kpi {{font-size:26px;font-weight:700;margin:6px 0;}}
        .sub {{color:{DASH_MUTED};font-size:13px;margin-top:2px;}}
        .chips > span {{
          display:inline-block;padding:6px 10px;margin:4px 6px 0 0;
          background:#f4f6f8;border:1px solid #e6ebef;border-radius:10px;
          font-size:0.85rem;color:#34495e;
        }}
        .two-col {{ display:grid;grid-template-columns:1fr 1fr;gap:12px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plot_imc_horizontal(imc: float) -> Tuple[go.Figure, str]:
    faixa_max = 40.0
    imc_clip = max(0.0, min(faixa_max, imc))
    categoria, cor = imc_categoria_cor(imc_clip)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[faixa_max],
            y=["IMC"],
            orientation="h",
            marker=dict(color="#ecf0f1"),
            hoverinfo="skip",
            showlegend=False,
            width=0.5,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[imc_clip],
            y=["IMC"],
            orientation="h",
            marker=dict(color=cor),
            hovertemplate=f"IMC: {imc:.1f}<extra>{categoria}</extra>",
            showlegend=False,
            width=0.5,
        )
    )
    shapes = []
    for _, lim, _, _ in IMC_FAIXAS[1:]:
        shapes.append(
            dict(
                type="line",
                x0=lim,
                x1=lim,
                y0=-0.5,
                y1=0.5,
                line=dict(color="#d9dde1", width=1, dash="dot"),
            )
        )
    fig.update_layout(shapes=shapes)
    fig.update_layout(
        barmode="overlay",
        height=140,
        margin=dict(l=30, r=30, t=0, b=10),
        xaxis=dict(range=[0, faixa_max], showgrid=False, zeroline=False, title=None),
        yaxis=dict(showticklabels=False),
    )
    return fig, categoria


def plot_agua(consumido: float, recomendado: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[consumido, recomendado],
            y=["Consumido", "Recomendado"],
            orientation="h",
            marker=dict(color=["#2E6F59", "#cbd5e1"]),
            showlegend=False,
            hovertemplate="%{y}: %{x:.1f} L<extra></extra>",
            width=0.45,
        )
    )
    fig.update_layout(
        height=180,
        margin=dict(l=30, r=30, t=0, b=10),
        xaxis=dict(showgrid=False, zeroline=False, title="Litros"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def build_perfil_text(payload: Dict[str, Any]) -> str:
    motiv = payload.get("motivacao")
    estresse = payload.get("estresse")
    energia = payload.get("energia_diaria")
    partes: List[str] = []
    if motiv:
        partes.append(f"motivação {int(_to_float(motiv, motiv))}/5")
    if estresse:
        partes.append(f"estresse {int(_to_float(estresse, estresse))}/5")
    if energia:
        partes.append(f"energia {str(energia).lower()}")
    if partes:
        return "Perfil com " + "; ".join(partes) + "."
    return "Perfil em construção."


def build_estrategia_text(peso: float, recomendado: float, categoria: str) -> str:
    partes: List[str] = []
    if categoria and categoria != "Indefinido":
        partes.append(f"IMC na faixa {categoria.lower()}")
    if recomendado:
        partes.append(f"hidratação alvo ≈ {recomendado:.1f} L/dia")
    if not partes:
        return "Estratégia em construção com base nos próximos dados coletados."
    return "; ".join(partes) + "."


def extract_bristol_tipo(texto: str | None, fallback: str = "") -> str:
    if not texto:
        return fallback or "—"
    match = re.search(r"tipo\s*(\d)", str(texto), flags=re.IGNORECASE)
    if match:
        return f"Tipo {match.group(1)}"
    return str(texto)


def extract_cor_urina(texto: str | None, fallback: str = "") -> str:
    if not texto:
        return fallback or "—"
    base = str(texto).split("(")[0].strip()
    return base or (fallback or "—")


def collect_comportamentos(payload: Dict[str, Any]) -> List[str]:
    itens: List[str] = []
    for key in ("habitos_alimentares", "observacoes", "historico_saude"):
        raw = payload.get(key)
        if not raw:
            continue
        parts = [p.strip(" .\n") for p in re.split(r"[,;\n•]+", str(raw))]
        itens.extend([p for p in parts if p])
    return itens
