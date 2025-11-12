"""Página centralizada de exibição dos resultados do paciente."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import streamlit as st

from modules import app_bootstrap, openai_utils, repo
from modules.client_state import get_user_cached, load_client_state, save_client_state
from modules.form.exporters import build_insights_pdf_bytes, build_share_png_bytes
from modules.form.ui_insights import (
    build_estrategia_text,
    build_perfil_text,
    collect_comportamentos,
    dashboard_style,
    element_icon,
    extract_bristol_tipo,
    extract_cor_urina,
    imc_categoria_cor,
    plot_agua,
    plot_imc_horizontal,
    signo_elemento,
    signo_symbol,
)

log = logging.getLogger(__name__)


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


def _fallback_insights(payload: Dict[str, Any]) -> Dict[str, Any]:
    peso = float(payload.get("peso") or 70)
    altura_cm = float(payload.get("altura") or 170)
    altura_m = max(0.1, altura_cm / 100.0)
    bmi = round(peso / (altura_m**2), 1)
    recomendado = round(max(1.5, peso * 0.035), 1)
    categoria, _ = imc_categoria_cor(bmi)
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
    insights["bmi_category"] = insights.get("bmi_category") or imc_categoria_cor(insights["bmi"])[0]

    consumo_info = insights.get("consumption") or {}
    consumo_real = float(consumo_info.get("water_liters") or payload.get("consumo_agua") or 0.0)
    recomendado = float(
        consumo_info.get("recommended_liters")
        or (round(max(1.5, peso * 0.035), 1) if peso else 2.0)
    )
    insights["consumption"] = {
        "water_liters": consumo_real,
        "recommended_liters": recomendado,
    }
    insights.setdefault("water_status", "OK" if recomendado and consumo_real >= recomendado else "Abaixo do ideal")
    insights.setdefault("motivacao", int(payload.get("motivacao") or 0))
    insights.setdefault("estresse", int(payload.get("estresse") or 0))
    insights.setdefault("bristol", extract_bristol_tipo(payload.get("tipo_fezes")))
    insights.setdefault("urine", extract_cor_urina(payload.get("cor_urina")))
    insights.setdefault("sign_hint", "Use seu signo como inspiração de hábitos saudáveis.")

    return insights


def _prepare_insights(payload: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
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


def _render_personal_header(respostas: Dict[str, Any], insights: Dict[str, Any]) -> None:
    signo = respostas.get("signo") or "—"
    elemento = signo_elemento(signo)
    elemento_icon = element_icon(elemento)
    perfil_text = build_perfil_text(respostas)
    estrategia_text = build_estrategia_text(
        float(respostas.get("peso") or 0.0),
        insights["consumption"].get("recommended_liters", 0.0),
        insights.get("bmi_category", "—"),
    )
    bristol_tipo = extract_bristol_tipo(respostas.get("tipo_fezes"), insights.get("bristol", ""))
    cor_urina = extract_cor_urina(respostas.get("cor_urina"), insights.get("urine", ""))
    comportamentos = collect_comportamentos(respostas)

    dashboard_style()

    col_signo, col_elem, col_perfil, col_estrat = st.columns([1, 1, 2, 2], gap="medium")
    with col_signo:
        st.markdown('<div class="card"><div class="card-title">Signo</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="square">{signo_symbol(signo)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="small-muted">{signo}</div></div>',
            unsafe_allow_html=True,
        )

    with col_elem:
        st.markdown('<div class="card"><div class="card-title">Elemento</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="square-element">{elemento_icon}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="small-muted">{elemento}</div></div>',
            unsafe_allow_html=True,
        )

    with col_perfil:
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">Perfil da Pessoa</div>
              <div class="kpi" style="font-size:18px">{perfil_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_estrat:
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">Estratégia Nutricional</div>
              <div class="kpi" style="font-size:18px">{estrategia_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="two-col">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">Bristol (fezes)</div>
          <div class="kpi" style="font-size:18px">Bristol</div>
          <div class="sub">{bristol_tipo}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">Cor da urina</div>
          <div class="kpi" style="font-size:18px">Cor</div>
          <div class="sub">{cor_urina}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    chips = "".join([f"<span>{item}</span>" for item in comportamentos]) or '<span style="color:#718096;">Sem itens cadastrados.</span>'
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


def _render_charts(respostas: Dict[str, Any], insights: Dict[str, Any]) -> None:
    peso = float(respostas.get("peso") or 0.0)
    altura_cm = float(respostas.get("altura") or 0.0)
    altura_m = round(altura_cm / 100.0, 2) if altura_cm else 0.0

    consumo = insights.get("consumption", {})
    consumo_real = float(consumo.get("water_liters") or 0.0)
    recomendado = float(consumo.get("recommended_liters") or 0.0)

    colA, colB = st.columns(2, gap="medium")
    with colA:
        fig_imc, categoria_imc = plot_imc_horizontal(insights.get("bmi") or 0.0)
        has_imc = (insights.get("bmi") or 0.0) > 0
        categoria_display = categoria_imc if has_imc else "Indisponível"
        st.markdown('<div class="card"><div class="card-title">IMC</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_imc, use_container_width=True, config={"displayModeBar": False})
        imc_text = f"{insights.get('bmi', 0.0):.1f}" if has_imc else "--"
        peso_text = f"{peso:.1f} kg" if peso else "--"
        altura_text = f"{altura_m:.2f} m" if altura_m else "--"
        st.markdown(
            f"<div class='sub'><b>Categoria:</b> {categoria_display} &nbsp; "
            f"<b>IMC:</b> {imc_text} &nbsp; <b>Peso:</b> {peso_text} &nbsp; "
            f"<b>Altura:</b> {altura_text}</div></div>",
            unsafe_allow_html=True,
        )

    with colB:
        fig_agua = plot_agua(consumo_real, recomendado)
        st.markdown('<div class="card"><div class="card-title">Hidratação</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_agua, use_container_width=True, config={"displayModeBar": False})
        ok = recomendado and consumo_real >= recomendado
        badge = (
            '<span style="background:#e8f7ef;color:#127a46;padding:2px 8px;border-radius:999px;font-size:12px">Meta atingida</span>'
            if ok
            else '<span style="background:#fff5e6;color:#8a5200;padding:2px 8px;border-radius:999px;font-size:12px">Abaixo do ideal</span>'
        )
        st.markdown(f'<div class="sub">{badge}</div></div>', unsafe_allow_html=True)


def _render_plan_sections(plan: Dict[str, Any], compacto: Dict[str, Any], macros: Dict[str, Any]) -> None:
    if compacto:
        st.subheader("Plano alimentar — resumo")
        st.json(compacto)

    if plan:
        with st.expander("Plano alimentar completo"):
            st.json(plan)

    if macros:
        st.subheader("Distribuição de macronutrientes")
        items = list(macros.items())
        cols = st.columns(len(items)) if items else []
        for col, (key, value) in zip(cols, items):
            label = key.replace("_", " ").title()
            if isinstance(value, float):
                display = f"{value:.2f}"
            else:
                display = f"{value}"
            col.metric(label, display)


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


def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

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
    compacto = st.session_state.get("plano_compacto") or payload.get("plano_alimentar_compacto") or {}
    macros = st.session_state.get("macros") or payload.get("macros") or {}

    st.title("📊 Painel personalizado")
    st.caption("Todos os seus dados consolidados em um único lugar.")
    st.info(f"Identificador do paciente: `{pac_id}`")

    insights, ai_summary = _prepare_insights(respostas)

    _render_personal_header(respostas, insights)
    _render_charts(respostas, insights)

    with st.expander("Resumo dos insights"):
        st.write(ai_summary)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Exportar PDF",
            data=build_insights_pdf_bytes(insights),
            file_name="insights.pdf",
            mime="application/pdf",
        )
    with col2:
        st.download_button(
            "Baixar imagem",
            data=build_share_png_bytes(insights),
            file_name="insights.png",
            mime="image/png",
        )

    if st.button("Gerar plano nutricional e prosseguir para pagamento"):
        _redirect_to_form(pac_id)

    _render_plan_sections(plan, compacto, macros)

    st.page_link("pages/0_Acessar_Resultados.py", label="Reacessar resultados", icon="🔁")


if __name__ == "__main__":
    main()
