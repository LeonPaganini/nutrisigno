"""Aplicação principal do NutriSigno."""

from __future__ import annotations

import streamlit as st

from modules.app_bootstrap import ensure_bootstrap


def _run_bootstrap() -> tuple[bool, str]:
    """Executa o bootstrap da aplicação e cacheia o resultado na sessão."""
    ok, msg = ensure_bootstrap()
    st.session_state["_bootstrap_ok"] = ok
    st.session_state["_bootstrap_msg"] = msg
    return ok, msg


def main() -> None:
    """Configurações globais e conteúdo de alto nível da aplicação."""
    st.set_page_config(page_title="NutriSigno", layout="wide")

    ok, msg = st.session_state.get("_bootstrap_ok"), st.session_state.get("_bootstrap_msg")
    if ok is None:
        ok, msg = _run_bootstrap()
    msg = msg or ""

    st.title("NutriSigno")
    st.write(
        "Use o menu lateral para acessar o formulário, dashboards e demais recursos do aplicativo."
    )

    if not ok:
        st.error(
            "Falha ao executar o bootstrap da aplicação. Verifique os logs para mais detalhes."
        )
    elif msg:
        st.caption(msg)


if __name__ == "__main__":
    main()
