"""Página de diagnóstico rápido do pipeline NutriSigno."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from modules.app_bootstrap import ensure_bootstrap
from modules import repo
from modules import openai_utils
from modules.dashboard_utils import (
    compute_insights,
    generate_dashboard_charts,
    create_dashboard_pdf,
)

SAMPLE_PAYLOAD: Dict[str, Any] = {
    "nome": "Teste Pipeline",
    "email": "teste.pipeline@example.com",
    "telefone": "(11) 91234-5678",
    "data_nascimento": "12/03/1990",
    "peso": 72,
    "altura": 172,
    "consumo_agua": 2.1,
    "signo": "Peixes",
    "nivel_atividade": "Moderado",
    "objetivo": "emagrecimento leve",
    "horas_sono_noite": 7.5,
    "cansaco_frequente": "Às vezes",
    "acorda_cansada": "Neutra",
    "tipo_fezes_bristol": "Tipo 4 (Salsicha lisa e macia)",
    "tipo_fezes": "Tipo 4",
    "freq_evacuacao": "1x por dia",
    "freq_inchaco_abdominal": "Raramente",
    "copos_agua_dia": 9,
    "cor_urina": "Amarelo claro",
    "retencao_inchaco": "Raramente",
    "fome_emocional": "Raramente",
    "compulsao_alimentar": "Nunca",
    "culpa_apos_comer": "Raramente",
    "refeicoes_por_dia": 4,
    "freq_pular_refeicoes": "Raramente",
    "constancia_fim_de_semana": "Muda um pouco",
}


def _ensure_outputs_dir() -> Path:
    out_dir = Path(os.getenv("OUTPUT_DIR", "outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _default_macros(plan: Dict[str, Any]) -> Dict[str, Any]:
    macros = plan.get("diet", {}).get("macros")
    if isinstance(macros, dict) and macros:
        return macros
    # fallback simples usado somente para o pipeline de teste
    return {"carboidratos": 45, "proteinas": 30, "gorduras": 25}


def _compact_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    diet = plan.get("diet", {})
    meals = diet.get("meals", [])
    resumo = [
        {
            "refeicao": meal.get("title"),
            "kcal": meal.get("kcal"),
            "itens": meal.get("items", []),
        }
        for meal in meals
    ]
    return {
        "total_kcal": diet.get("total_kcal"),
        "resumo_refeicoes": resumo,
        "hidratação": diet.get("hydration"),
    }


def run_pipeline() -> Dict[str, Any]:
    ok, bootstrap_msg = ensure_bootstrap()
    result: Dict[str, Any] = {"bootstrap": {"ok": ok, "mensagem": bootstrap_msg}}

    user_data = SAMPLE_PAYLOAD.copy()

    plan = openai_utils.generate_plan(user_data)
    result["plano"] = plan

    insights = compute_insights(user_data)
    charts = generate_dashboard_charts(insights)
    insights_bundle = openai_utils.generate_insights(user_data)
    ai_summary = insights_bundle.get("ai_summary")

    out_dir = _ensure_outputs_dir()
    pdf_path = out_dir / f"dashboard_teste_{uuid.uuid4().hex[:8]}.pdf"
    create_dashboard_pdf(user_data, insights, charts, str(pdf_path))
    for fig in charts.values():
        try:
            fig.clf()
        except Exception:
            pass

    macros = _default_macros(plan)
    plano_compacto = _compact_plan(plan)
    pac_id = repo.upsert_patient_payload(
        pac_id=None,
        respostas=user_data,
        plano=plan,
        plano_compacto=plano_compacto,
        macros=macros,
        name=user_data.get("nome"),
        email=user_data.get("email"),
    )

    payment_url = f"https://pay.nutrisigno.dev/simulado/{pac_id}" if pac_id else f"https://pay.nutrisigno.dev/simulado/{uuid.uuid4().hex[:8]}"

    result.update(
        {
            "insights": insights,
            "ai_summary": ai_summary,
            "pdf_path": str(pdf_path),
            "pac_id": pac_id,
            "payment_url": payment_url,
            "macros": macros,
            "plano_compacto": plano_compacto,
        }
    )
    return result


def main() -> None:
    st.set_page_config(page_title="Teste do Pipeline", page_icon="🧪", layout="wide")
    st.title("🧪 Teste do Pipeline NutriSigno")
    st.write(
        "Esta página executa o pipeline completo com dados de demonstração para validar o ambiente."
    )

    st.subheader("Payload de demonstração")
    st.json(SAMPLE_PAYLOAD)

    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None

    if st.button("Executar pipeline de teste", type="primary"):
        with st.spinner("Executando pipeline simulado..."):
            st.session_state.pipeline_result = run_pipeline()

    result = st.session_state.pipeline_result
    if not result:
        st.info("Clique no botão acima para gerar pré-plano, PDF e URL simulada de pagamento.")
        return

    st.success("Pipeline executado com sucesso!")

    bootstrap = result.get("bootstrap", {})
    status_text = "✅ Bootstrap concluído" if bootstrap.get("ok") else "⚠️ Bootstrap com avisos"
    with st.expander(status_text, expanded=not bootstrap.get("ok", True)):
        st.write(bootstrap.get("mensagem"))

    st.subheader("Pré-plano gerado")
    st.json(result.get("plano", {}))

    st.subheader("Insights do Dashboard")
    cols = st.columns(2)
    with cols[0]:
        st.json(result.get("insights", {}))
    with cols[1]:
        st.write("Resumo IA")
        ai_summary = result.get("ai_summary")
        if ai_summary:
            st.write(ai_summary)
        else:
            st.info("Nenhum resumo adicional disponível no modo atual.")

    pdf_path = result.get("pdf_path")
    if pdf_path and Path(pdf_path).exists():
        pdf_bytes = Path(pdf_path).read_bytes()
        st.download_button(
            "Baixar PDF do Dashboard",
            data=pdf_bytes,
            file_name=Path(pdf_path).name,
            mime="application/pdf",
        )
        st.caption(f"Arquivo gerado em: {pdf_path}")

    st.subheader("Dados persistidos")
    st.json(
        {
            "pac_id": result.get("pac_id"),
            "macros": result.get("macros"),
            "plano_compacto": result.get("plano_compacto"),
        }
    )

    st.subheader("Pagamento simulado")
    payment_url = result.get("payment_url")
    if payment_url:
        st.markdown(f"[Abrir link de pagamento simulado]({payment_url})")
    else:
        st.warning("URL de pagamento não disponível.")

    st.toast("Pipeline gerado com sucesso!", icon="✅")


if __name__ == "__main__":
    main()
