"""Aplicação principal do NutriSigno."""

from __future__ import annotations

import streamlit as st

from modules.app_bootstrap import ensure_bootstrap

# Garante que as tabelas existam (Render/produção)
ok, msg = ensure_bootstrap()


def main() -> None:
    """Configurações globais e conteúdo de alto nível da aplicação."""
    st.set_page_config(page_title="NutriSigno", layout="wide")

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
