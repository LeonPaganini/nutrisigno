# pages/1_Dashboard_demo.py
from __future__ import annotations

import html
import unicodedata
from typing import List, Tuple
import streamlit as st
import plotly.graph_objects as go

# ==========================
# MOCK — Dados de exemplo
# ==========================
respostas = {
    "signo": "Leão",
    "perfil_astrologico": "Líder, enérgico; responde melhor a rotinas objetivas e metas semanais.",
    "estrategia_nutricional": "Plano 30P/45C/25G com foco em fibras, proteína magra e hidratação estruturada.",
    "escala_bristol": "4",
    "cor_urina": "Amarelo-claro",
    "peso_kg": 78.0,
    "altura_m": 1.78,
    "consumo_agua": 2.1,  # L/dia
    "motivacao": 4,
    "estresse": 2,
    "comportamentos": ["Come rápido", "Belisca à noite", "Baixa ingestão de água"],
}

# ==========================
# Constantes / helpers
# ==========================
PRIMARY = "#2E6F59"
MUTED = "#6b7280"

ZODIAC_SYMBOLS = {
    "aries": "♈︎", "touro": "♉︎", "gemeos": "♊︎",
    "cancer": "♋︎", "leao": "♌︎", "virgem": "♍︎",
    "libra": "♎︎", "escorpiao": "♏︎", "sagitario": "♐︎",
    "capricornio": "♑︎", "aquario": "♒︎", "peixes": "♓︎",
}

IMC_FAIXAS: List[Tuple[str, float, float, str]] = [
    ("Magreza",           0.0, 18.5, "#7aa6f9"),
    ("Normal",           18.5, 25.0, "#55c169"),
    ("Sobrepeso",        25.0, 30.0, "#ffb347"),
    ("Obesidade I",      30.0, 35.0, "#ff7f50"),
    ("Obesidade II/III", 35.0, 60.0, "#e74c3c"),
]

# Mapas de elemento (pedidos)
ELEMENT_MAP = {
    "Terra":  {"touro", "virgem", "capricornio"},
    "Ar":     {"gemeos", "libra", "aquario"},
    "Fogo":   {"aries", "leao", "sagitario"},
    "Água":   {"escorpiao", "peixes", "cancer"},
}

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()

def _signo_key(signo: str) -> str:
    # normaliza: leão→leao, câncer→cancer, gêmeos→gemeos...
    return _strip_accents((signo or "").strip())

def _signo_symbol(signo: str) -> str:
    return ZODIAC_SYMBOLS.get(_signo_key(signo), "✦")

def _signo_elemento(signo: str) -> str:
    key = _signo_key(signo)
    for elem, conjunto in ELEMENT_MAP.items():
        if key in conjunto:
            return elem
    return "—"

# ==========================
# Estilo (CSS leve)
# ==========================
def _style():
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
        .small-muted {{ color:#718096;font-size:0.82rem;text-align:center;margin-top:6px;}}
        .kpi {{font-size:26px;font-weight:700;margin:6px 0;}}
        .sub {{color:{MUTED};font-size:13px;margin-top:2px;}}
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

# ==========================
# Gráficos
# ==========================
def _plot_imc_horizontal(imc: float):
    faixa_max = 40.0
    imc_clip = max(0.0, min(faixa_max, imc))
    categoria, cor = next(((n, c) for n, lo, hi, c in IMC_FAIXAS if lo <= imc_clip < hi), ("Indefinido", "#95a5a6"))

    fig = go.Figure()
    # faixa base
    fig.add_trace(go.Bar(
        x=[faixa_max], y=["IMC"], orientation="h",
        marker=dict(color="#ecf0f1"), hoverinfo="skip",
        showlegend=False, width=0.5
    ))
    # valor
    fig.add_trace(go.Bar(
        x=[imc_clip], y=["IMC"], orientation="h",
        marker=dict(color=cor),
        hovertemplate=f"IMC: {imc:.1f}<extra>{categoria}</extra>",
        showlegend=False, width=0.5
    ))
    # divisórias
    shapes = []
    for _, lim, _, _ in IMC_FAIXAS[1:]:
        shapes.append(dict(type="line", x0=lim, x1=lim, y0=-0.5, y1=0.5,
                           line=dict(color="#d9dde1", width=1, dash="dot")))
    fig.update_layout(shapes=shapes)
    fig.update_layout(
        barmode="overlay", height=140,
        margin=dict(l=30, r=30, t=0, b=10),
        xaxis=dict(range=[0, faixa_max], showgrid=False, zeroline=False, title=None),
        yaxis=dict(showticklabels=False),
    )
    return fig, categoria

def _plot_agua(consumido: float, recomendado: float):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[consumido, recomendado],
        y=["Consumido", "Recomendado"],
        orientation="h",
        marker=dict(color=[PRIMARY, "#cbd5e1"]),
        showlegend=False,
        hovertemplate="%{y}: %{x:.1f} L<extra></extra>",
        width=0.45,
    ))
    fig.update_layout(
        height=180, margin=dict(l=30, r=30, t=0, b=10),
        xaxis=dict(showgrid=False, zeroline=False, title="Litros"),
        yaxis=dict(autorange="reversed"),
    )
    return fig

# ==========================
# UI
# ==========================
def main() -> None:
    st.set_page_config(page_title="Dashboard (Demo)", page_icon="📊", layout="wide")
    st.title("📊 Dashboard — Demo (mock)")
    st.caption("Inclui card de Elemento e layout: Linha 1 (Signo | Perfil | Estratégia) • Linha 2 (Elemento | Signo ícone).")

    _style()

    # Cálculos básicos
    peso = float(respostas.get("peso_kg") or 0)
    altura_m = float(respostas.get("altura_m") or 0)
    imc = round(peso / (altura_m**2), 1) if (peso and altura_m) else 0.0
    elemento = _signo_elemento(respostas["signo"])

    # ===== Linha 1: Signo (texto) | Perfil | Estratégia =====
    col1, col2, col3 = st.columns([1, 2, 2], gap="medium")
    with col1:
        st.markdown('<div class="card"><div class="card-title">Signo</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi">{html.escape(respostas["signo"])}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''
        <div class="card">
          <div class="card-title">Perfil da Pessoa</div>
          <div class="kpi" style="font-size:18px">{html.escape(respostas["perfil_astrologico"])}</div>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        st.markdown(f'''
        <div class="card">
          <div class="card-title">Estratégia Nutricional</div>
          <div class="kpi" style="font-size:18px">{html.escape(respostas["estrategia_nutricional"])}</div>
        </div>
        ''', unsafe_allow_html=True)

    # ===== Linha 2: Elemento | Signo (ícone) =====
    colE, colS = st.columns([1, 1], gap="medium")
    with colE:
        st.markdown('<div class="card"><div class="card-title">Elemento</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi">{html.escape(elemento)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with colS:
        st.markdown('<div class="card"><div class="card-title">Signo (ícone)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="square">{html.escape(_signo_symbol(respostas["signo"]))}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="small-muted">{html.escape(respostas["signo"])}</div></div>', unsafe_allow_html=True)

    # ===== Linha 3: Bristol | Urina =====
    st.markdown('<div class="two-col">', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="card">
      <div class="card-title">Bristol (fezes)</div>
      <div class="kpi" style="font-size:18px">Bristol</div>
      <div class="sub">Tipo {html.escape(str(respostas["escala_bristol"]))}</div>
    </div>
    ''', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="card">
      <div class="card-title">Cor da urina</div>
      <div class="kpi" style="font-size:18px">Cor</div>
      <div class="sub">{html.escape(respostas["cor_urina"])}</div>
    </div>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ===== Linha 4: IMC + Hidratação =====
    colA, colB = st.columns(2, gap="medium")
    with colA:
        fig_imc, categoria = _plot_imc_horizontal(imc)
        st.markdown('<div class="card"><div class="card-title">IMC</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_imc, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<div class="sub"><b>Categoria:</b> {html.escape(categoria)} &nbsp; '
            f'<b>IMC:</b> {imc:.1f} &nbsp; '
            f'<b>Peso:</b> {peso:.1f} kg &nbsp; '
            f'<b>Altura:</b> {altura_m:.2f} m</div></div>',
            unsafe_allow_html=True
        )
    with colB:
        recomendado = round(max(1.5, peso * 0.035), 1) if peso else 2.0
        consumo = float(respostas.get("consumo_agua") or 0)
        fig_agua = _plot_agua(consumo, recomendado)
        st.markdown('<div class="card"><div class="card-title">Hidratação</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_agua, use_container_width=True, config={"displayModeBar": False})
        ok = consumo >= recomendado
        badge = '<span style="background:#e8f7ef;color:#127a46;padding:2px 8px;border-radius:999px;font-size:12px">Meta atingida</span>' \
                if ok else \
                '<span style="background:#fff5e6;color:#8a5200;padding:2px 8px;border-radius:999px;font-size:12px">Abaixo do ideal</span>'
        st.markdown(f'<div class="sub">{badge}</div></div>', unsafe_allow_html=True)

    # ===== Linha 5: Comportamento (chips dentro do card) =====
    chips = "".join([f"<span>{html.escape(x)}</span>" for x in respostas.get("comportamentos", [])]) \
            or '<span style="color:#718096;">Sem itens cadastrados.</span>'
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">Comportamento</div>
          <div class="card" style="background:#fbfcfd;border:1px dashed #e6ebef;">
            <div class="chips">{chips}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()