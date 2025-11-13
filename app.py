"""Aplicação principal do NutriSigno."""

from __future__ import annotations

import logging

import streamlit as st

from modules.app_bootstrap import init_models_and_migrate

log = logging.getLogger(__name__)


def _run_bootstrap() -> tuple[bool, str]:
    """Executa o bootstrap (migrations + init) e cacheia o resultado na sessão."""
    try:
        init_models_and_migrate()
        ok, msg = True, "Bootstrap executado com sucesso."
    except Exception as exc:  # noqa: BLE001
        log.exception("Falha ao executar bootstrap do NutriSigno.")
        ok, msg = False, f"Erro ao iniciar a aplicação. Detalhes nos logs. ({exc})"

    st.session_state["_bootstrap_ok"] = ok
    st.session_state["_bootstrap_msg"] = msg
    return ok, msg


def main() -> None:
    """Configurações globais e conteúdo de alto nível da aplicação."""
    st.set_page_config(page_title="NutriSigno", layout="wide")

    ok = st.session_state.get("_bootstrap_ok")
    msg = st.session_state.get("_bootstrap_msg")

    if ok is None:
        ok, msg = _run_bootstrap()

    msg = msg or ""

    st.title("NutriSigno")
    st.write(
        "Use o menu lateral para acessar o formulário, dashboards e demais recursos do aplicativo."
    )

    if not ok:
        st.error(
            "Falha ao executar o bootstrap da aplicação. "
            "Verifique os logs para mais detalhes."
        )
    elif msg:
        st.caption(msg)


if __name__ == "__main__":
    main()