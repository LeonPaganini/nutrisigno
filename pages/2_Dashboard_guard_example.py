# pages/2_Dashboard_guard_example.py
from __future__ import annotations

import streamlit as st

from modules import repo
from modules import app_bootstrap
from modules import dashboard_utils  # já existente

def require_login() -> None:
    if "pac_id" not in st.session_state:
        st.error("Acesso restrito. Vá em **Acessar Resultados** e faça login com telefone + data de nascimento.")
        st.stop()

def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title="Meu Painel", page_icon="📈", layout="wide")
    require_login()
    pac_id = st.session_state["pac_id"]
    data = st.session_state.get("paciente_data") or repo.get_by_pac_id(pac_id)
    if not data:
        st.warning("Não foi possível carregar seus dados.")
        st.stop()
    dashboard_utils.render(data)

if __name__ == "__main__":
    main()
