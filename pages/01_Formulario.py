"""Página multipage do formulário principal do NutriSigno."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import streamlit as st

from modules import email_utils, openai_utils, pdf_generator, repo
from modules.client_state import get_user_cached, load_client_state, save_client_state
from modules.form.mapper import map_ui_to_dto
from modules.form.service import FormService
from modules.form.state import ensure_bootstrap_ready, initialize_session, next_step
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
        return

    pac_id, step = load_client_state()
    if not pac_id:
        st.session_state._client_state_synced = True
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

    st.session_state.dashboard_insights = None
    st.session_state.dashboard_ai_summary = None
    st.success("Cadastro salvo com sucesso. Redirecionando para o painel...")

    try:
        st.switch_page("pages/02_Dashboard.py")
    except Exception:
        try:
            params = st.experimental_get_query_params()
            params["page"] = "02_Dashboard"
            st.experimental_set_query_params(**params)
            st.experimental_rerun()
        except Exception:
            st.info("Use o menu lateral para acessar o painel '02_Dashboard'.")
            st.stop()


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
