# pages/0_Acessar_Resultados.py
from __future__ import annotations

import re
from datetime import datetime
import logging
import streamlit as st

from modules.client_state import get_user_cached, load_client_state, save_client_state
from modules.repo import get_by_phone_dob, list_recent_patients
from modules.db import engine

log = logging.getLogger(__name__)

pac_id_cached, step_cached = load_client_state()
if pac_id_cached:
    if "pac_id" not in st.session_state:
        st.session_state.pac_id = pac_id_cached
    payload_cached = get_user_cached(pac_id_cached)
    if payload_cached:
        st.session_state.paciente_data = payload_cached
        if step_cached:
            try:
                st.session_state.step = max(1, int(str(step_cached)))
            except Exception:  # pragma: no cover - defensive
                pass

# ---------------------------------------------------------------------
# Helpers inline (sem criar módulos extras)
# ---------------------------------------------------------------------
def _canon_phone(s: str) -> str:
    # mantém apenas dígitos e remove zeros à esquerda
    return re.sub(r"\D+", "", (s or "")).lstrip("0")

def _canon_dob_to_br(s: str) -> str:
    """
    Aceita DD/MM/AAAA ou YYYY-MM-DD e padroniza para DD/MM/AAAA.
    Se não bater com os formatos esperados, retorna a string original
    para o repo tratar (e falhar de forma clara, se necessário).
    """
    s = (s or "").strip()
    for fmt_in in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt_in).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return s

# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
st.set_page_config(page_title="Acessar resultados", page_icon="🔎", layout="centered")

st.title("Acessar resultados")
st.caption("Digite seu telefone (com DDD) e data de nascimento para localizar seu cadastro.")

with st.form("form_acesso"):
    col1, col2 = st.columns(2)
    with col1:
        telefone_input = st.text_input("Telefone (com DDD)", placeholder="(11) 9 8765-4321")
    with col2:
        data_nasc_input = st.text_input("Data de nascimento", placeholder="DD/MM/AAAA ou 1990-05-21")

    submitted = st.form_submit_button("Acessar")

if submitted:
    telefone_norm = _canon_phone(telefone_input)
    dob_br = _canon_dob_to_br(data_nasc_input)

    log.info(
        "AcessarResultados: dialect=%s phone_norm=%s dob_norm=%s",
        engine.dialect.name, telefone_norm, dob_br
    )

    if not telefone_norm or not dob_br:
        st.error("Informe telefone com DDD e data de nascimento válidos.")
    else:
        st.info(f"Buscando cadastro para **{telefone_norm}** | **{dob_br}**...")
        try:
            user = get_by_phone_dob(telefone_norm, dob_br)
        except Exception as e:
            st.error(f"Erro ao buscar cadastro: {e}")
            user = None

        if user:
            st.success("Cadastro encontrado.")
            pac_id_found = user.get("pac_id")
            st.session_state.pac_id = pac_id_found
            st.session_state.paciente_data = user
            step_to_persist = st.session_state.get("step")
            if pac_id_found:
                save_client_state(
                    pac_id_found,
                    str(step_to_persist) if step_to_persist else None,
                )
                get_user_cached(pac_id_found)
            # Exibição mínima para validação — ajuste conforme seu layout do Dashboard
            with st.expander("Dados brutos do cadastro (debug)"):
                st.json(user, expanded=False)

            # -----------------------------------------------------------------
            # AQUI você pode chamar seu renderer de cards/dash, ex.:
            # render_dashboard(user)
            # -----------------------------------------------------------------

        else:
            st.warning("Não encontramos nenhum cadastro com esses dados.")

# ---------------------------------------------------------------------
# Painel de debug — últimos cadastros
# ---------------------------------------------------------------------
with st.expander("Debug — últimos cadastros na base atual"):
    st.caption(f"Dialeto ativo: {engine.dialect.name}")
    try:
        rows = list_recent_patients(10)
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("Sem registros recentes nesta base.")
    except Exception as e:
        st.error(f"Erro ao listar cadastros: {e}")