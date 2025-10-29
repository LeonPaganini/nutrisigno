from __future__ import annotations

import html
from typing import Dict, Any, List, Tuple

import streamlit as st
import plotly.graph_objects as go

from modules import app_bootstrap, repo

# ---------------------------------------------------------
# Paleta/constantes
# ---------------------------------------------------------
PRIMARY = "#2E6F59"
MUTED = "#6b7280"

ZODIAC_SYMBOLS = {
    "áries": "♈︎", "touro": "♉︎", "gêmeos": "♊︎", "gemeos": "♊︎",
    "câncer": "♋︎", "cancer": "♋︎", "leão": "♌︎", "leao": "♌︎",
    "virgem": "♍︎", "libra": "♎︎", "escorpião": "♏︎", "escorpiao": "♏︎",
    "sagitário": "♐︎", "sagitario": "♐︎", "capricórnio": "♑︎", "capricornio": "♑︎",
    "aquário": "♒︎", "aquario": "♒︎", "peixes": "♓︎",
}

# (nome, início, fim, cor)
IMC_FAIXAS: List[Tuple[str, float, float, str]] = [
    ("Magreza",           0.0, 18.5, "#7aa6f9"),
    ("Normal",           18.5, 25.0, "#55c169"),
    ("Sobrepeso",        25.0, 30.0, "#ffb347"),
    ("Obesidade I",      30.0, 35.0, "#ff7f50"),
    ("Obesidade II/III", 35.0, 60.0, "#e74c3c"),
]

# ---------------------------------------------------------
# Estilo
# ---------------------------------------------------------
def _style():
    st.markdown(
        f"""
        <style>
        .grid {{
          display:grid;
          grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
          gap:12px;margin-top:8px;
        }}
        .card {{
          background:#fff;border:1px solid #e6e6e6;border-radius:12px;
          padding:14px;box-shadow:0 2px 10px rgba(0,0,0,0.04);
        }}
        .card-title {{
          font-weight:700;font-size:0.95rem;color:#2c3e50;margin-bottom:8px;
        }}
        .kpi {{font-size:26px;font-weight:700;margin:6px 0;}}
        .sub {{color:{MUTED};font-size:13px;margin-top:2px;}}
        .badge-ok{{display:inline-block;padding:2px 8px;border-radius:999px;background:#e8f7ef;color:#127a46;font-size:12px}}
        .badge-warn{{display:inline-block;padding:2px 8px;border-radius:999px;background:#fff5e6;color:#8a5200;font-size:12px}}
        .square {{
          aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;
          font-size:64px;font-weight:700;border-radius:16px;border:1px dashed #e5e7eb;
          background:#fbfcfd;
        }}
        .small-muted {{ color:#718096;font-size:0.82rem;text-align:center;margin-top:6px;}}
        .chips > span {{
          display:inline-block;padding:6px 10px;margin:4px 6px 0 0;
          background:#f4f6f8;border:1px solid #e6ebef;border-radius:10px;
          font-size:0.85rem;color:#34495e;
        }}
        .two-col {{
          display:grid;grid-template-columns:1fr 1fr;gap:12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def _badge(text: str, ok: bool = True) -> str:
    cls = "badge-ok" if ok else "badge-warn"
    return f'<span class="{cls}">{html.escape(text)}</span>'

# ---------------------------------------------------------
# Dados / Insights
# ---------------------------------------------------------
def _fake_insights() -> Dict[str, Any]:
    return {
        "signo": "Leão",
        "perfil": "Líder, enérgico, responde bem a rotinas objetivas.",
        "estrategia": "Plano balanceado 30P/45C/25G com fibras e proteína magra.",
        "bmi": 24.1,
        "bmi_category": "Normal",
        "consumption": {"water_liters": 1.8, "recommended_liters": 2.3},
        "water_status": "OK",
        "bristol": "Tipo 4 (dentro do esperado)",
        "urine": "Amarelo-claro",
        "motivacao": 4,
        "estresse": 2,
        "comportamentos": ["Come rápido", "Belisca à noite", "Baixa ingestão de água"],
    }

def _imc_categoria_cor(imc: float) -> Tuple[str, str]:
    for nome, lo, hi, cor in IMC_FAIXAS:
        if lo <= imc < hi:
            return nome, cor
    return "Indefinido", "#95a5a6"

def _insights_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai dados mínimos do payload real; fallback para demo.
    Espera chaves dentro de payload/respostas (ajuste livre conforme seu repo).
    """
    if not payload:
        return _fake_insights()

    respostas = payload.get("respostas", {}) or {}
    # Origem dos campos
    signo = respostas.get("signo") or payload.get("signo") or "—"
    perfil = respostas.get("perfil_astrologico") or respostas.get("perfil") or "—"
    estrategia = respostas.get("estrategia_nutricional") or respostas.get("estrategia") or "—"

    # IMC
    peso = float(respostas.get("peso_kg") or respostas.get("peso") or 70)
    altura_m = 0.0
    if "altura_m" in respostas:
        try: altura_m = float(respostas["altura_m"])
        except: altura_m = 0.0
    elif "altura_cm" in respostas:
        try: altura_m = float(respostas["altura_cm"]) / 100.0
        except: altura_m = 0.0
    if not altura_m:
        try:
            altura = float(respostas.get("altura") or 170.0)
            altura_m = max(1.0, altura / 100.0)
        except:
            altura_m = 1.7

    bmi = round(peso / (altura_m ** 2), 1)
    bmi_cat, _ = _imc_categoria_cor(bmi)

    # Água
    consumido = float(respostas.get("consumo_agua") or 1.6)
    recomendado = round(max(1.5, peso * 0.035), 1)
    water_ok = consumido >= recomendado

    return {
        "signo": signo,
        "perfil": perfil,
        "estrategia": estrategia,
        "bmi": bmi,
        "bmi_category": bmi_cat,
        "consumption": {"water_liters": consumido, "recommended_liters": recomendado},
        "water_status": "OK" if water_ok else "LOW",
        "bristol": respostas.get("escala_bristol") or respostas.get("bristol") or respostas.get("tipo_fezes", "—"),
        "urine": respostas.get("cor_urina", "—"),
        "motivacao": int(respostas.get("motivacao") or 3),
        "estresse": int(respostas.get("estresse") or 3),
        "comportamentos": respostas.get("comportamentos") or [],
    }

# ---------------------------------------------------------
# Render helpers (cards e gráficos)
# ---------------------------------------------------------
def _signo_symbol(signo: str) -> str:
    s = (signo or "").strip().lower()
    return ZODIAC_SYMBOLS.get(s, "✦")

def _card_signo(signo: str):
    symbol = _signo_symbol(signo)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">Signo</div>
          <div class="square">{html.escape(symbol)}</div>
          <div class="small-muted">{html.escape(signo or "—")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _card_texto(titulo: str, valor: str):
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">{html.escape(titulo)}</div>
          <div class="kpi" style="font-size:18px">{html.escape(valor or "—")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _row_bristol_urina(bristol: str, urine: str):
    st.markdown('<div class="two-col">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">Bristol (fezes)</div>
          <div class="kpi" style="font-size:18px">{"Bristol"}</div>
          <div class="sub">{html.escape(bristol or "—")}</div>
        </div>
        """, unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">Cor da urina</div>
          <div class="kpi" style="font-size:18px">{"Cor"}</div>
          <div class="sub">{html.escape(urine or "—")}</div>
        </div>
        """, unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

def _plot_imc_horizontal(imc: float):
    faixa_max = 40.0
    imc_clip = max(0.0, min(faixa_max, imc))
    categoria, cor = _imc_categoria_cor(imc_clip)

    fig = go.Figure()
    # faixa completa (cinza claro)
    fig.add_trace(go.Bar(
        x=[faixa_max], y=["IMC"], orientation="h",
        marker=dict(color="#ecf0f1"), hoverinfo="skip",
        showlegend=False, width=0.5
    ))
    # valor (cor dinâmica)
    fig.add_trace(go.Bar(
        x=[imc_clip], y=["IMC"], orientation="h",
        marker=dict(color=cor),
        hovertemplate=f"IMC: {imc:.1f}<extra>{categoria}</extra>",
        showlegend=False, width=0.5
    ))
    # Linhas das faixas (opcional)
    shapes = []
    for _, lim, _, _ in IMC_FAIXAS[1:]:  # desenha divisórias nas mudanças
        shapes.append(dict(type="line", x0=lim, x1=lim, y0=-0.5, y1=0.5,
                           line=dict(color="#d9dde1", width=1, dash="dot")))
    fig.update_layout(shapes=shapes)

    fig.update_layout(
        barmode="overlay", height=140,
        margin=dict(l=30, r=30, t=0, b=10),
        xaxis=dict(range=[0, faixa_max], showgrid=False, zeroline=False, title=None),
        yaxis=dict(showticklabels=False),
    )
    return fig, categoria, cor

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

def _card_comportamento(itens: List[str]):
    chips = "".join([f"<span>{html.escape(x)}</span>" for x in (itens or [])]) or \
            '<span style="color:#718096;">Sem itens cadastrados.</span>'
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

# ---------------------------------------------------------
# Página
# ---------------------------------------------------------
def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title="Dashboard (Amostra)", page_icon="📊", layout="wide")

    st.title("📊 Dashboard — Visual readequado")
    st.caption(
        "Cards de signo, perfil e estratégia; Bristol e Urina na mesma linha; "
        "IMC com barra horizontal por faixa; Comportamento com mini-cards."
    )

    _style()

    # Dados reais se houver sessão; caso contrário, demo
    payload = None
    if st.session_state.get("pac_id"):
        st.success(f"Sessão ativa: pac_id `{st.session_state['pac_id']}`")
        payload = st.session_state.get("paciente_data") or repo.get_by_pac_id(st.session_state["pac_id"])
    else:
        st.info("Você não está logado. Mostrando **amostra** com dados fictícios.")
        st.page_link("pages/0_Acessar_Resultados.py", label="Fazer login (telefone + data de nascimento)", icon="🔑")

    ins = _insights_from_payload(payload)

    # ===== Linha 1: Signo | Perfil | Estratégia =====
    col1, col2, col3 = st.columns([1, 2, 2], gap="medium")
    with col1: _card_signo(ins.get("signo"))
    with col2: _card_texto("Perfil da Pessoa", ins.get("perfil"))
    with col3: _card_texto("Estratégia Nutricional", ins.get("estrategia"))

    # ===== Linha 2: Bristol | Urina (mesma linha) =====
    _row_bristol_urina(ins.get("bristol"), ins.get("urine"))

    # ===== Linha 3: IMC (barra horizontal colorida) + Água (modernizado) =====
    colA, colB = st.columns(2, gap="medium")
    with colA:
        fig_imc, categoria, cor = _plot_imc_horizontal(ins.get("bmi", 0.0))
        st.markdown('<div class="card"><div class="card-title">IMC</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_imc, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<div class="sub"><b>Categoria:</b> {html.escape(categoria)} &nbsp; '
            f'<b>IMC:</b> {ins.get("bmi",0):.1f}</div></div>',
            unsafe_allow_html=True
        )
    with colB:
        agua = ins.get("consumption", {})
        fig_agua = _plot_agua(float(agua.get("water_liters", 0)), float(agua.get("recommended_liters", 0)))
        ok = ins.get("water_status") == "OK"
        st.markdown('<div class="card"><div class="card-title">Hidratação</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_agua, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<div class="sub">{_badge("Meta atingida", True) if ok else _badge("Abaixo do ideal", False)}</div></div>',
            unsafe_allow_html=True
        )

    # ===== Linha 4: Comportamento (mini-cards dentro do card principal) =====
    _card_comportamento(ins.get("comportamentos") or [
        f"Motivação {ins.get('motivacao',0)}/5",
        f"Estresse {ins.get('estresse',0)}/5",
    ])

    # ===== Debug =====
    with st.expander("Dados-base utilizados"):
        st.json(payload or {"demo": "dados fictícios de amostra"})

    st.divider()
    colL, colR = st.columns([1,1])
    with colL:
        st.page_link("pages/0_Acessar_Resultados.py", label="🔑 Acessar Resultados (Login leve)", icon="➡️")
    with colR:
        st.page_link("pages/2_Dashboard_guard_example.py", label="🛡️ Ver exemplo do Guard", icon="➡️")

if __name__ == "__main__":
    main()