# pages/2_Dashboard_guard_example.py
from __future__ import annotations

import streamlit as st
from modules import app_bootstrap, repo
from modules.client_state import get_user_cached, load_client_state, save_client_state


def _rehydrate_dashboard_state() -> None:
    if st.session_state.get("pac_id"):
        return

    pac_id, step = load_client_state()
    if not pac_id:
        return

    st.session_state.pac_id = pac_id
    if step:
        try:
            st.session_state.step = max(1, int(str(step)))
        except Exception:  # pragma: no cover - defensive
            pass

    payload = get_user_cached(pac_id)
    if payload:
        st.session_state.paciente_data = payload

    save_client_state(pac_id, str(st.session_state.get("step")) if st.session_state.get("step") else None)

def require_login() -> None:
    """Impede acesso se não houver sessão com pac_id."""
    if "pac_id" not in st.session_state:
        st.error("🔒 Acesso restrito")
        st.caption(
            "Para visualizar seu painel, acesse a página **Acessar Resultados** "
            "e informe **telefone + data de nascimento** (login leve)."
        )
        st.page_link("pages/0_Acessar_Resultados.py", label="Ir para Acessar Resultados", icon="➡️")
        st.stop()

def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title="Meu Painel (Guard)", page_icon="🔒", layout="wide")

    st.title("📊 Meu Painel — Exemplo com Guard")
    st.write("Esta página ilustra o bloqueio de acesso quando não há sessão ativa (pac_id).")

    _rehydrate_dashboard_state()

    # exige sessão
    require_login()

    # Se chegou aqui, há sessão
    pac_id = st.session_state["pac_id"]
    st.success(f"✅ Sessão válida. pac_id: `{pac_id}`")

    # Busca payload real
    payload = st.session_state.get("paciente_data") or get_user_cached(pac_id) or repo.get_by_pac_id(pac_id)
    if payload:
        st.session_state.paciente_data = payload
        save_client_state(pac_id, str(st.session_state.get("step")) if st.session_state.get("step") else None)
    if not payload:
        st.warning("Cadastro encontrado, mas sem dados carregados agora. Tente novamente em instantes.")
        st.stop()

    # Render mínimo só pra ilustrar
    respostas = payload.get("respostas", {})
    plano = payload.get("plano_alimentar", {})
    macros = payload.get("macros", {})

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nome", respostas.get("nome", "—"))
    with col2:
        st.metric("Signo", respostas.get("signo", "—"))
    with col3:
        st.metric("Status", payload.get("status", "—"))

    st.subheader("Resumo do Plano (amostra)")
    st.json({ "plano_compacto": payload.get("plano_alimentar_compacto", {}), "macros": macros })

    st.info("Este é só um *mock* para mostrar o guard. Para a versão completa, use o Dashboard de amostra abaixo.")

if __name__ == "__main__":
    main()