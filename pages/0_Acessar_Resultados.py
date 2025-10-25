# pages/0_Acessar_Resultados.py
from __future__ import annotations
import streamlit as st
from modules import repo, app_bootstrap, dashboard_utils

PAGE_TITLE = "Acessar Resultados"

def normalizar_telefone(tel: str) -> str:
    return ''.join(ch for ch in tel if ch.isdigit())

def _guard_logged() -> bool:
    return bool(st.session_state.get("pac_id"))

def _logout_button() -> None:
    if st.button("Sair", use_container_width=True):
        for k in ("pac_id", "paciente_data"):
            st.session_state.pop(k, None)
        st.success("Sessão encerrada.")

def render_dashboard(paciente_data: dict) -> None:
    st.success("✅ Acesso autorizado. Seus resultados estão abaixo.")
    try:
        dashboard_utils.render(paciente_data)
    except Exception as e:
        st.error(f"Não foi possível renderizar o painel: {e}")

def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title=PAGE_TITLE, page_icon="📊", layout="wide")
    st.title("📊 Acessar Resultados")
    st.caption("Insira seu telefone e a data de nascimento no formato DD/MM/AAAA.")

    with st.form("form_login_leve"):
        telefone = st.text_input("Telefone (com DDD; pode ter espaços/traços)")
        dob = st.text_input("Data de nascimento (DD/MM/AAAA)")
        submit = st.form_submit_button("Acessar", use_container_width=True)

    if submit:
        if not telefone or not dob:
            st.error("Por favor preencha os dois campos.")
            st.stop()

        telefone = normalizar_telefone(telefone)
        try:
            data = repo.get_by_phone_dob(telefone, dob)
            if not data:
                st.error("Não encontramos nenhum cadastro com esses dados.")
                st.stop()
            st.session_state["pac_id"] = data["pac_id"]
            st.session_state["paciente_data"] = data
            st.experimental_rerun()
        except ValueError as ve:
            st.error(str(ve))
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")

    if _guard_logged():
        _logout_button()
        payload = st.session_state.get("paciente_data") or repo.get_by_pac_id(st.session_state["pac_id"])
        if payload:
            render_dashboard(payload)
        else:
            st.warning("Não foi possível carregar seus dados agora. Tente novamente em instantes.")

if __name__ == "__main__":
    main()