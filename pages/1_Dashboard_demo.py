# pages/1_Dashboard_demo.py
from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, Any

import streamlit as st
import matplotlib.pyplot as plt

from modules import app_bootstrap, repo

PRIMARY = "#2E6F59"
MUTED = "#6b7280"

def _style():
    st.markdown(
        f"""
        <style>
        .grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:8px;}}
        .card {{background:#fff;border:1px solid #e6e6e6;border-radius:12px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);}}
        .kpi {{font-size:26px;font-weight:700;margin:6px 0;}}
        .sub {{color:{MUTED};font-size:13px;margin-top:2px;}}
        .badge-ok{{display:inline-block;padding:2px 8px;border-radius:999px;background:#e8f7ef;color:#127a46;font-size:12px}}
        .badge-warn{{display:inline-block;padding:2px 8px;border-radius:999px;background:#fff5e6;color:#8a5200;font-size:12px}}
        </style>
        """,
        unsafe_allow_html=True,
    )

def _badge(text: str, ok: bool = True) -> str:
    cls = "badge-ok" if ok else "badge-warn"
    return f'<span class="{cls}">{text}</span>'

def _fake_insights() -> Dict[str, Any]:
    """Dados fictícios de amostra (amole)."""
    return {
        "bmi": 24.1,
        "bmi_category": "Eutrofia",
        "consumption": {"water_liters": 1.8, "recommended_liters": 2.3},
        "water_status": "OK",
        "bristol": "Tipo 4 (dentro do esperado)",
        "urine": "Amarelo claro",
        "motivacao": 4,
        "estresse": 2,
        "sign_hint": "Organize refeições conforme seu ritmo natural.",
    }

def _insights_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai o mínimo para a amostra a partir do payload real; fallback para fake."""
    if not payload:
        return _fake_insights()
    # Caso seu pipeline completo já gere insights prontos, ajuste aqui.
    respostas = payload.get("respostas", {}) or {}
    peso = float(respostas.get("peso") or 70)
    altura = float(respostas.get("altura") or 170)
    altura_m = max(1.0, altura / 100)
    bmi = round(peso / (altura_m ** 2), 1)
    return {
        "bmi": bmi,
        "bmi_category": "Eutrofia" if 18.5 <= bmi < 25 else ("Baixo peso" if bmi < 18.5 else ("Sobrepeso" if bmi < 30 else "Obesidade")),
        "consumption": {"water_liters": float(respostas.get("consumo_agua") or 1.6),
                        "recommended_liters": round(max(1.5, peso * 0.035), 1)},
        "water_status": "OK",
        "bristol": respostas.get("tipo_fezes", "—"),
        "urine": respostas.get("cor_urina", "—"),
        "motivacao": int(respostas.get("motivacao") or 3),
        "estresse": int(respostas.get("estresse") or 3),
        "sign_hint": "Use seu signo como inspiração, não como prescrição.",
    }

def _render_kpis(ins: Dict[str, Any]):
    st.markdown('<div class="grid">', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="card">
      <div>IMC</div>
      <div class="kpi">{ins.get("bmi","--")}</div>
      <div class="sub">{ins.get("bmi_category","")}</div>
    </div>
    ''', unsafe_allow_html=True)

    ok = ins.get("water_status","OK") == "OK"
    st.markdown(f'''
    <div class="card">
      <div>Hidratação</div>
      <div class="kpi">{ins["consumption"]["water_liters"]} / {ins["consumption"]["recommended_liters"]} L</div>
      <div class="sub">{_badge("Meta atingida" if ok else "Abaixo do ideal", ok)}</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f'''
    <div class="card">
      <div>Digestão</div>
      <div class="kpi">Bristol</div>
      <div class="sub">{ins.get("bristol","")}</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f'''
    <div class="card">
      <div>Urina</div>
      <div class="kpi">Cor</div>
      <div class="sub">{ins.get("urine","")}</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f'''
    <div class="card">
      <div>Comportamento</div>
      <div class="kpi">Motivação {ins.get("motivacao",0)}/5</div>
      <div class="sub">Estresse {ins.get("estresse",0)}/5</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f'''
    <div class="card">
      <div>Insight do signo</div>
      <div class="kpi">🜚</div>
      <div class="sub">{ins.get("sign_hint","")}</div>
    </div>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def _render_charts(ins: Dict[str, Any]):
    col1, col2 = st.columns(2)
    with col1:
        fig = plt.figure()
        plt.title("Consumo de água (L)")
        vals = [ins["consumption"]["water_liters"], ins["consumption"]["recommended_liters"]]
        plt.bar(["Consumido", "Recomendado"], vals)
        st.pyplot(fig, clear_figure=True)
    with col2:
        fig2 = plt.figure()
        plt.title("IMC")
        plt.bar(["IMC"], [ins.get("bmi", 0)])
        plt.axhline(18.5, linestyle="--"); plt.axhline(25, linestyle="--")
        st.pyplot(fig2, clear_figure=True)

def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title="Dashboard (Amostra)", page_icon="📊", layout="wide")

    st.title("📊 Dashboard — Amostra visual")
    st.caption("Esta tela demonstra como ficará o dashboard com KPIs e gráficos. "
               "Se você estiver logado (pac_id em sessão), usa dados reais; caso contrário, usa dados fictícios.")

    _style()

    # Tenta dados reais se houver sessão
    payload = None
    if st.session_state.get("pac_id"):
        st.success(f"Sessão ativa: pac_id `{st.session_state['pac_id']}`")
        payload = st.session_state.get("paciente_data") or repo.get_by_pac_id(st.session_state["pac_id"])
    else:
        st.info("Você não está logado. Mostrando **amostra** com dados fictícios.")
        st.page_link("pages/0_Acessar_Resultados.py", label="Fazer login (telefone + data de nascimento)", icon="🔑")

    ins = _insights_from_payload(payload)
    _render_kpis(ins)
    _render_charts(ins)

    with st.expander("Dados-base utilizados"):
        st.json(payload or {"demo": "dados fictícios de amostra"})

    st.divider()
    colA, colB = st.columns([1,1])
    with colA:
        st.page_link("pages/0_Acessar_Resultados.py", label="🔑 Acessar Resultados (Login leve)", icon="➡️")
    with colB:
        st.page_link("pages/2_Dashboard_guard_example.py", label="🛡️ Ver exemplo do Guard", icon="➡️")

if __name__ == "__main__":
    main()
