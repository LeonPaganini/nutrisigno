"""Session helpers for the form page."""

from __future__ import annotations

import uuid
from typing import Tuple

import streamlit as st

from modules.app_bootstrap import ensure_bootstrap


def initialize_session() -> None:
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    st.session_state.setdefault("step", 1)
    st.session_state.setdefault("data", {})
    st.session_state.setdefault("paid", False)
    st.session_state.setdefault("plan", None)
    st.session_state.setdefault("plano_compacto", None)
    st.session_state.setdefault("macros", None)
    st.session_state.setdefault("pac_id", None)


def next_step() -> None:
    st.session_state.step += 1


def ensure_bootstrap_ready() -> Tuple[bool, str]:
    ok = st.session_state.get("_bootstrap_ok")
    msg = st.session_state.get("_bootstrap_msg")
    if ok is None:
        ok, msg = ensure_bootstrap()
        st.session_state["_bootstrap_ok"] = ok
        st.session_state["_bootstrap_msg"] = msg or ""
    return bool(ok), (msg or "")
