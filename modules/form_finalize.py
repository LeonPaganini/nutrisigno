# modules/form_finalize.py
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime

import streamlit as st

from . import repo

def finalizar_formulario_handler(
    pac_id: Optional[str],
    respostas: Dict[str, Any],
    plano: Dict[str, Any],
    plano_compacto: Dict[str, Any],
    macros: Dict[str, Any],
    name: Optional[str] = None,
    email: Optional[str] = None,
) -> str | None:
    """
    Salva/atualiza os dados do paciente no PostgreSQL.
    Exibe feedback na UI. Retorna o pac_id salvo/atualizado.
    """
    try:
        new_pac_id = repo.upsert_patient_payload(
            pac_id=pac_id,
            respostas=respostas,
            plano=plano,
            plano_compacto=plano_compacto,
            macros=macros,
            name=name,
            email=email,
        )
        st.session_state["pac_id"] = new_pac_id
        st.success(
            "Formulário finalizado! Em até 24h você receberá seu plano revisado pela Nutricionista Thaís.\n\n"
            "Você pode reabrir seu painel a qualquer momento em **Acessar Resultados** usando telefone e data de nascimento."
        )
        return new_pac_id
    except Exception as e:
        st.error(f"Erro ao finalizar: {e}")
        return None