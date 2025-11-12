"""Página multipage do formulário principal do NutriSigno."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import streamlit as st

from modules import email_utils, openai_utils, pdf_generator, repo
from modules.client_state import get_user_cached, load_client_state, save_client_state
from modules.form.exporters import build_insights_pdf_bytes, build_share_png_bytes
from modules.form.mapper import map_ui_to_dto
from modules.form.service import FormService
from modules.form.state import ensure_bootstrap_ready, initialize_session, next_step
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
from modules.form.ui_sections import (
    SectionResult,
    nutrition_section,
    personal_data_section,
    psychological_section,
    review_section,
    sign_selection_section,
)

log = logging.getLogger(__name__)

SIMULATE: bool = os.getenv("SIMULATE", "0") == "1"


def _rehydrate_form_state() -> None:
    """Reidrata a sessão usando camadas cliente/servidor quando necessário."""

    hydrated = st.session_state.get("_client_state_synced")
    if hydrated:
        return

    pac_id_existing = st.session_state.get("pac_id")
    data_existing = st.session_state.get("data") or {}
    if pac_id_existing and data_existing:
        st.session_state._client_state_synced = True
        st.session_state.pop("_client_state_attempts", None)
        return

    pac_id, step = load_client_state()
    if not pac_id:
        attempts = int(st.session_state.get("_client_state_attempts", 0)) + 1
        st.session_state._client_state_attempts = attempts
        if attempts < 3:
            return
        st.session_state._client_state_synced = True
        st.session_state.pop("_client_state_attempts", None)
        return

    if not pac_id_existing:
        st.session_state.pac_id = pac_id

    target_step: int | None = None
    if step:
        try:
            target_step = max(1, int(str(step)))
        except (TypeError, ValueError):
            target_step = None

    payload = get_user_cached(pac_id)
    if payload:
        st.session_state.data = payload.get("respostas") or {}
        st.session_state.plan = payload.get("plano_alimentar")
        st.session_state.plano_compacto = payload.get("plano_alimentar_compacto")
        st.session_state.macros = payload.get("macros")
        st.session_state.paciente_data = payload
        st.session_state.loaded_external = True
        if target_step is None and (st.session_state.get("step") or 1) < 6:
            target_step = 6

    if target_step is not None:
        st.session_state.step = target_step

    if pac_id:
        step_for_save = target_step if target_step is not None else st.session_state.get("step")
        save_client_state(pac_id, str(step_for_save) if step_for_save else None)

    st.session_state._client_state_synced = True
    st.session_state.pop("_client_state_attempts", None)


def _persist_form(service: FormService, data: Dict[str, Any]) -> str | None:
    """Persist the current form state using the service layer."""

    dto = map_ui_to_dto(data)
    try:
        log.info(
            "submit.start phone=%s dob=%s",
            data.get("telefone"),
            data.get("data_nascimento"),
        )
        pac_id = service.save_from_form(
            dto,
            pac_id=st.session_state.get("pac_id"),
            plano=st.session_state.get("plan") or {},
            plano_compacto=st.session_state.get("plano_compacto") or {},
            macros=st.session_state.get("macros") or {},
        )
        st.session_state.pac_id = pac_id
        save_client_state(pac_id, str(st.session_state.get("step") or ""))
        get_user_cached(pac_id)
        log.info("submit.ok pac_id=%s", pac_id)
        return pac_id
    except ValueError as exc:
        log.info("submit.fail exc=%s", exc)
        st.error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("submit.fail")
        st.error("Erro ao salvar os dados. Tente novamente em instantes.")
    return None


def _render_section(result: SectionResult) -> None:
    if result.data:
        st.session_state.data.update(result.data)
        if "signo" in result.data:
            st.session_state["signo"] = result.data["signo"]
    step_changed = False
    if result.advance:
        next_step()
        step_changed = True
    if result.go_back:
        st.session_state.step = max(1, st.session_state.step - 1)
        step_changed = True
    if step_changed and st.session_state.get("pac_id"):
        save_client_state(st.session_state.pac_id, str(st.session_state.step))


def _fallback_insights(payload: Dict[str, Any]) -> Dict[str, Any]:
    peso = float(payload.get("peso") or 70)
    altura_cm = float(payload.get("altura") or 170)
    altura_m = max(0.1, altura_cm / 100.0)
    bmi = round(peso / (altura_m**2), 1)
    recomendado = round(max(1.5, peso * 0.035), 1)
    return {
        "bmi": bmi,
        "bmi_category": "Eutrofia"
        if 18.5 <= bmi < 25
        else ("Baixo peso" if bmi < 18.5 else ("Sobrepeso" if bmi < 30 else "Obesidade")),
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


def _render_insights(service: FormService, payload: Dict[str, Any]) -> None:
    pac_id = _persist_form(service, payload)
    if not pac_id:
        return

    try:
        log.info("submit.read phone=%s dob=%s", payload.get("telefone"), payload.get("data_nascimento"))
        repo.get_by_pac_id(pac_id)
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("Formulario persist sanity check failed")
        st.error("Não foi possível validar seu cadastro após o salvamento. Tente novamente.")
        return

    try:
        ai_pack = openai_utils.generate_insights(payload)
        insights = ai_pack.get("insights", {})
        ai_summary = ai_pack.get("ai_summary", "Resumo indisponível (modo simulado).")
    except Exception as exc:  # pragma: no cover - fallback
        st.warning(f"Modo fallback automático: {exc}")
        insights = _fallback_insights(payload)
        ai_summary = "Resumo simulado (fallback hard)."

    peso = float(payload.get("peso") or 0.0)
    altura_cm = float(payload.get("altura") or 0.0)
    altura_m = round(altura_cm / 100.0, 2) if altura_cm else 0.0
    imc = round(peso / (altura_m**2), 1) if peso and altura_m else 0.0

    imc_value = insights.get("bmi") or imc or 0.0
    insights["bmi"] = float(imc_value)
    categoria_base = insights.get("bmi_category") or imc_categoria_cor(insights["bmi"])[0]
    insights["bmi_category"] = categoria_base

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

    signo = payload.get("signo") or "—"
    elemento = signo_elemento(signo)
    elemento_icon = element_icon(elemento)
    perfil_text = build_perfil_text(payload)
    estrategia_text = build_estrategia_text(peso, recomendado, categoria_base)
    bristol_tipo = extract_bristol_tipo(payload.get("tipo_fezes"), insights.get("bristol", ""))
    cor_urina = extract_cor_urina(payload.get("cor_urina"), insights.get("urine", ""))
    comportamentos = collect_comportamentos(payload)

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

    colA, colB = st.columns(2, gap="medium")
    with colA:
        fig_imc, categoria_imc = plot_imc_horizontal(insights["bmi"] or 0.0)
        has_imc = insights["bmi"] > 0
        categoria_display = categoria_imc if has_imc else "Indisponível"
        st.markdown('<div class="card"><div class="card-title">IMC</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_imc, use_container_width=True, config={"displayModeBar": False})
        imc_text = f"{insights['bmi']:.1f}" if has_imc else "--"
        peso_text = f"{peso:.1f} kg" if peso else "--"
        altura_m = round(altura_cm / 100.0, 2) if altura_cm else 0.0
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

    with st.expander("Resumo dos insights"):
        st.write(ai_summary)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Exportar PDF",
            data=build_insights_pdf_bytes(insights),
            file_name="insights.pdf",
            mime="application/pdf",
        )
    with c2:
        st.download_button(
            "Baixar imagem",
            data=build_share_png_bytes(insights),
            file_name="insights.png",
            mime="image/png",
        )
    with c3:
        if st.button("Gerar plano nutricional e prosseguir para pagamento"):
            st.session_state.step += 1
            if st.session_state.get("pac_id"):
                save_client_state(st.session_state.pac_id, str(st.session_state.step))
            st.rerun()


def _render_payment(service: FormService) -> None:
    st.header("7. Pagamento e geração do plano")
    st.write(
        "Para finalizar, realize o pagamento abaixo. Este exemplo utiliza um "
        "botão simbólico; substitua por sua integração de pagamento real em produção."
    )
    if not st.session_state.paid:
        if st.button("Realizar pagamento (exemplo)"):
            st.session_state.paid = True
            st.success("Pagamento confirmado! Gerando seu plano...")

    if st.session_state.paid and st.session_state.plan is None:
        with st.spinner("Gerando plano personalizado, por favor aguarde..."):
            try:
                plan_dict = openai_utils.generate_plan(st.session_state.data)
                st.session_state.plan = plan_dict
            except Exception as exc:  # pragma: no cover - external
                st.error(f"Erro ao gerar plano com a OpenAI: {exc}")
                return

            try:
                macros = openai_utils.calcular_macros(st.session_state.plan)
            except Exception:
                macros = {}
            st.session_state.macros = macros

            try:
                plano_compacto = openai_utils.resumir_plano(st.session_state.plan)
            except Exception:
                plano_compacto = {}
            st.session_state.plano_compacto = plano_compacto

            dto = map_ui_to_dto(st.session_state.data)
            try:
                log.info(
                    "submit.start phone=%s dob=%s",
                    st.session_state.data.get("telefone"),
                    st.session_state.data.get("data_nascimento"),
                )
                pac_id = service.save_from_form(
                    dto,
                    pac_id=st.session_state.get("pac_id"),
                    plano=st.session_state.plan,
                    plano_compacto=plano_compacto,
                    macros=macros,
                )
                st.session_state.pac_id = pac_id
                save_client_state(pac_id, str(st.session_state.get("step") or ""))
                get_user_cached(pac_id)
                log.info("submit.ok pac_id=%s", pac_id)
            except ValueError as exc:
                log.info("submit.fail exc=%s", exc)
                st.error(str(exc))
                return
            except Exception as exc:  # pragma: no cover - defensive
                log.exception("submit.fail")
                st.error(f"Erro ao salvar no banco: {exc}")
                return

            pdf_path = f"/tmp/{st.session_state.pac_id or st.session_state.user_id}.pdf"
            try:
                pdf_generator.create_pdf_report(
                    st.session_state.data,
                    st.session_state.plan,
                    pdf_path,
                )
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
            except Exception as exc:
                st.error(f"Erro ao gerar o PDF: {exc}")
                return

            try:
                base_url = os.getenv("PUBLIC_BASE_URL", "")
                panel_link = (
                    f"{base_url}/?id={st.session_state.pac_id}"
                    if base_url
                    else f"/?id={st.session_state.pac_id}"
                )
                subject = "Seu Plano Alimentar NutriSigno"
                body = (
                    "Olá {nome},\n\n"
                    "Em anexo está o seu plano alimentar personalizado gerado pelo NutriSigno. "
                    "Siga as orientações com responsabilidade e, se possível, consulte um profissional "
                    "da saúde antes de iniciar qualquer mudança significativa.\n\n"
                    "Você poderá acessar novamente o painel de insights por meio do link abaixo:\n"
                    f"{panel_link}\n\n"
                    "Atenciosamente,\nEquipe NutriSigno"
                ).format(nome=st.session_state.data.get("nome"))
                attachments = [(f"nutrisigno_plano_{st.session_state.pac_id}.pdf", pdf_bytes)]
                if not SIMULATE:
                    email_utils.send_email(
                        recipient=st.session_state.data.get("email"),
                        subject=subject,
                        body=body,
                        attachments=attachments,
                    )
            except Exception as exc:
                st.error(f"Erro ao enviar e-mail: {exc}")
                return

            st.success("Plano gerado e enviado por e-mail!")
            st.download_button(
                label="Baixar plano em PDF",
                data=pdf_bytes,
                file_name=f"nutrisigno_plano_{st.session_state.pac_id}.pdf",
                mime="application/pdf",
            )
            st.markdown(
                f"Você pode revisitar seus insights quando quiser através deste link: "
                f"[Painel de Insights](/?id={st.session_state.pac_id})"
            )


def main() -> None:
    service = FormService()
    ok, msg = ensure_bootstrap_ready()
    if not ok:
        st.error("Não foi possível inicializar os recursos da aplicação. Tente novamente mais tarde.")
        if msg:
            st.caption(msg)
        return

    st.title("Formulário")
    st.write(
        "Bem-vindo ao NutriSigno! Preencha as etapas abaixo para receber um plano "
        "alimentar personalizado, combinando ciência e astrologia."
    )
    if msg:
        st.caption(msg)

    initialize_session()
    _rehydrate_form_state()

    total_steps = 7
    progress = (st.session_state.step - 1) / total_steps
    st.progress(progress)

    step = st.session_state.step
    if step == 1:
        result = personal_data_section(st.session_state.data)
        _render_section(result)
    elif step == 2:
        current_sign = st.session_state.get("signo") or st.session_state.data.get("signo")
        result = sign_selection_section(current_sign)
        _render_section(result)
    elif step == 3:
        result = nutrition_section(st.session_state.data)
        _render_section(result)
    elif step == 4:
        result = psychological_section(st.session_state.data)
        _render_section(result)
    elif step == 5:
        result = review_section(st.session_state.data)
        _render_section(result)
    elif step == 6:
        _render_insights(service, st.session_state.data)
    elif step == 7:
        _render_payment(service)


if __name__ == "__main__":
    main()
