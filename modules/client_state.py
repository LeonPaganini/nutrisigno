"""Helpers for lightweight client/session persistence."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, Optional, Tuple

import streamlit as st

from modules import repo
from modules.db import engine

log = logging.getLogger(__name__)

try:  # opcional
    from streamlit_js_eval import streamlit_js_eval  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    streamlit_js_eval = None  # type: ignore

_LOCAL_STORAGE_PREFIX = "nutrisigno"
_DEFAULT_CACHE_TTL = int(os.getenv("USER_CACHE_TTL", "3600") or 3600)
_CACHE_LOADERS: Dict[int, Callable[[str, str], Optional[Dict[str, Any]]]] = {}


def _ls_key(name: str) -> str:
    return f"{_LOCAL_STORAGE_PREFIX}_{name}"


def _local_storage_available() -> bool:
    return streamlit_js_eval is not None


def _local_storage_get(name: str) -> Optional[str]:
    if not _local_storage_available():
        return None
    try:
        result = streamlit_js_eval(
            js_expressions=f"window.localStorage.getItem('{_ls_key(name)}')",
            key=f"ls-get-{name}",
        )
        if isinstance(result, str):
            return result or None
    except Exception:  # pragma: no cover - defensive
        return None
    return None


def _local_storage_set(name: str, value: Optional[str]) -> None:
    if not _local_storage_available():
        return
    try:
        if value is None:
            streamlit_js_eval(
                js_expressions=f"window.localStorage.removeItem('{_ls_key(name)}')",
                key=f"ls-del-{name}",
            )
        else:
            encoded = json.dumps(value)
            streamlit_js_eval(
                js_expressions=f"window.localStorage.setItem('{_ls_key(name)}', {encoded})",
                key=f"ls-set-{name}-{value}",
            )
    except Exception:  # pragma: no cover - defensive
        return


def _update_query_params(updates: Dict[str, Optional[str]]) -> None:
    try:
        qp = st.query_params
        for key, value in updates.items():
            if value is None:
                if key in qp:
                    del qp[key]
            else:
                qp[key] = value
    except Exception:  # pragma: no cover - fallback para versões antigas
        params = st.experimental_get_query_params()
        for key, value in updates.items():
            if value is None:
                params.pop(key, None)
            else:
                params[key] = value
        st.experimental_set_query_params(**params)


def save_client_state(pac_id: str, step: Optional[str] = None) -> None:
    """Persiste pac_id/step em query params e localStorage (quando possível)."""

    updates = {"pac_id": pac_id}
    updates["step"] = step if step else None
    _update_query_params(updates)

    _local_storage_set("pac_id", pac_id)
    _local_storage_set("step", step if step else None)

    log.info("save_client_state pac_id=%s step=%s", pac_id, step)


def load_client_state() -> Tuple[Optional[str], Optional[str]]:
    """Carrega pac_id e step prioritariamente da URL e, se vazio, do localStorage."""

    qp = st.query_params
    pac_id_qp = qp.get("pac_id") or qp.get("id")
    step_qp = qp.get("step")

    pac_id_ls = _local_storage_get("pac_id")
    step_ls = _local_storage_get("step")

    pac_id = pac_id_qp or pac_id_ls
    step = step_qp or step_ls

    if pac_id:
        log.info("rehydrate: pac_id=%s step=%s", pac_id, step)
        return pac_id, step

    log.warning("rehydrate: no client state found")
    return None, None


def _get_loader(ttl: int) -> Callable[[str, str], Optional[Dict[str, Any]]]:
    loader = _CACHE_LOADERS.get(ttl)
    if loader is None:
        @st.cache_data(ttl=ttl, show_spinner=False)
        def _load(pac_id: str, dialect: str) -> Optional[Dict[str, Any]]:
            user = repo.get_by_pac_id(pac_id)
            log.info("cache hit user=%s", user.get("name") if user else None)
            return user

        _CACHE_LOADERS[ttl] = _load
        loader = _load
    return loader


def get_user_cached(pac_id: str, ttl: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Busca paciente com cache de dados para acelerar reidratação."""

    ttl_value = ttl or _DEFAULT_CACHE_TTL
    log.info(
        "cache.fetch pac_id=%s ttl=%s dialect=%s",
        pac_id,
        ttl_value,
        engine.dialect.name,
    )
    loader = _get_loader(ttl_value)
    return loader(pac_id, engine.dialect.name)
