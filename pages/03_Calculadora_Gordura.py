"""Calculadora de % de gordura corporal (Marinha Americana) com captura de leads."""

from __future__ import annotations

import logging
import math
import re
from typing import Any

import streamlit as st

from modules import app_bootstrap
from modules.leads import salvar_lead_calculadora

log = logging.getLogger(__name__)

FEMALE_ACTIVE = "#f77fb0"
MALE_ACTIVE = "#16a34a"
INACTIVE_BG = "#f4f6fb"


def _apply_global_styles() -> None:
    st.markdown(
        f"""
        <style>
        div[data-testid="stRadio"] label[data-baseweb="radio"] {{
            border: 1px solid #d9dfe7;
            padding: 10px 16px;
            border-radius: 14px;
            background: {INACTIVE_BG};
            transition: all 0.15s ease;
            box-shadow: inset 0 1px 0 #fff;
        }}
        div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {{
            border-color: #c7cfdd;
        }}
        div[data-testid="stRadio"] > div {{
            margin-right: 8px;
        }}
        div[data-testid="stRadio"] input:checked + div {{
            color: #0f172a;
            font-weight: 700;
        }}
        div[data-testid="stRadio"] > div:nth-child(1) input:checked + div {{
            background: linear-gradient(135deg, {FEMALE_ACTIVE}, #f89abe);
            color: #fff;
            border-color: {FEMALE_ACTIVE};
        }}
        div[data-testid="stRadio"] > div:nth-child(2) input:checked + div {{
            background: linear-gradient(135deg, {MALE_ACTIVE}, #22c55e);
            color: #fff;
            border-color: {MALE_ACTIVE};
        }}
        .stTextInput>div>div>input::placeholder {{
            color: #94a3b8;
        }}
        .error-text {{
            color: #b91c1c;
            font-size: 0.9rem;
            margin-top: -4px;
            margin-bottom: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_phone_mask(digits: str) -> str:
    """Aplica máscara brasileira (11 dígitos) somente para exibição."""

    digits = re.sub(r"\D", "", digits or "")[:11]
    if len(digits) <= 2:
        return digits
    if len(digits) <= 7:
        return f"({digits[:2]}) {digits[2:]}"
    return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"


def _normalize_phone_state() -> None:
    digits = re.sub(r"\D", "", st.session_state.get("celular_raw", ""))[:11]
    st.session_state.celular_raw = _format_phone_mask(digits)
    st.session_state.celular_digits = digits


def _validate_nome(nome: str) -> tuple[bool, str | None]:
    nome_clean = (nome or "").strip()
    if len(nome_clean) < 3 or len(nome_clean) > 80:
        return False, "Informe um nome válido (mínimo 3 caracteres)."
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ\s]+", nome_clean):
        return False, "Informe um nome válido (apenas letras e espaços)."
    return True, None


def _validate_celular(celular: str) -> tuple[bool, str | None, str]:
    digits = re.sub(r"\D", "", celular or "")[:11]
    if len(digits) != 11:
        return False, "Informe um celular válido com DDD (11 dígitos).", digits
    return True, None, digits


def _validate_float(value: Any) -> float | None:
    try:
        v = float(value)
        return v if v > 0 else None
    except Exception:
        return None


def _calculate_body_fat(
    genero: str,
    altura_cm: float,
    pescoco_cm: float,
    cintura_cm: float | None,
    quadril_cm: float | None,
    abdomen_cm: float | None,
) -> float:
    """Calcula a % de gordura pelo método da Marinha Americana."""

    if genero == "feminino":
        if cintura_cm is None or quadril_cm is None:
            raise ValueError("Medidas de cintura e quadril são obrigatórias para o cálculo feminino.")
        base = cintura_cm + quadril_cm - pescoco_cm
        if base <= 0:
            raise ValueError("As medidas devem resultar em um valor válido para log10.")
        return 163.205 * math.log10(base) - 97.684 * math.log10(altura_cm) - 78.387

    if abdomen_cm is None:
        raise ValueError("Medida de abdômen é obrigatória para o cálculo masculino.")
    base = abdomen_cm - pescoco_cm
    if base <= 0:
        raise ValueError("As medidas devem resultar em um valor válido para log10.")
    return 86.010 * math.log10(base) - 70.041 * math.log10(altura_cm) + 36.76


def _render_result(resultado: float) -> None:
    st.success("Cálculo concluído com sucesso!")
    st.metric("% de gordura estimada", f"{resultado:.1f}%")


def main() -> None:
    app_bootstrap.ensure_bootstrap()
    st.set_page_config(page_title="Calculadora de % de gordura", page_icon="📐", layout="centered")

    _apply_global_styles()

    st.title("Calculadora de % de gordura corporal")
    st.caption("Método Marinha Americana — agora com captura de leads")

    if "genero" not in st.session_state:
        st.session_state.genero = "feminino"
    if "celular_digits" not in st.session_state:
        st.session_state.celular_digits = ""
    if "celular_raw" not in st.session_state:
        st.session_state.celular_raw = ""

    with st.form("form_calculadora", clear_on_submit=False):
        nome = st.text_input("Nome completo", placeholder="Ex.: Ana Silva")
        st.text_input(
            "Celular (WhatsApp)",
            key="celular_raw",
            on_change=_normalize_phone_state,
            placeholder="(11) 98765-4321",
        )

        nome_ok, nome_error = _validate_nome(nome)
        celular_ok, celular_error, celular_digits = _validate_celular(st.session_state.get("celular_raw", ""))

        st.markdown("<div class='mini-label'>Gênero</div>", unsafe_allow_html=True)
        genero = st.radio(
            "",
            ("feminino", "masculino"),
            horizontal=True,
            key="genero",
            label_visibility="collapsed",
            format_func=lambda x: "Feminino" if x == "feminino" else "Masculino",
            help="Escolha o gênero para aplicar a fórmula correta",
        )

        col1, col2 = st.columns(2)
        with col1:
            altura = st.text_input("Altura (cm)")
        with col2:
            pescoco = st.text_input("Circunferência do pescoço (cm)")

        cintura: str | None = None
        quadril: str | None = None
        abdomen: str | None = None

        col3, col4 = st.columns(2)
        with col3:
            if genero == "feminino":
                cintura = st.text_input("Cintura (cm)")
            else:
                abdomen = st.text_input("Abdômen (cm)")
        with col4:
            if genero == "feminino":
                quadril = st.text_input("Quadril (cm)")

        altura_v = _validate_float(altura)
        pescoco_v = _validate_float(pescoco)
        cintura_v = _validate_float(cintura) if genero == "feminino" else None
        quadril_v = _validate_float(quadril) if genero == "feminino" else None
        abdomen_v = _validate_float(abdomen) if genero == "masculino" else None

        medidas_validas = altura_v and pescoco_v and ((cintura_v and quadril_v) if genero == "feminino" else abdomen_v)

        if not nome_ok:
            st.markdown(f"<div class='error-text'>{nome_error}</div>", unsafe_allow_html=True)
        if not celular_ok:
            st.markdown(f"<div class='error-text'>{celular_error}</div>", unsafe_allow_html=True)

        errors = []
        if altura and not altura_v:
            errors.append("Altura deve ser um número válido em cm.")
        if pescoco and not pescoco_v:
            errors.append("Pescoço deve ser um número válido em cm.")
        if genero == "feminino":
            if cintura and not cintura_v:
                errors.append("Cintura deve ser um número válido em cm.")
            if quadril and not quadril_v:
                errors.append("Quadril deve ser um número válido em cm.")
        else:
            if abdomen and not abdomen_v:
                errors.append("Abdômen deve ser um número válido em cm.")

        for err in errors:
            st.markdown(f"<div class='error-text'>{err}</div>", unsafe_allow_html=True)

        form_valid = bool(nome_ok and celular_ok and medidas_validas)
        submitted = st.form_submit_button("Calcular agora", disabled=not form_valid)

    if submitted and form_valid:
        try:
            resultado = _calculate_body_fat(
                genero,
                altura_v,
                pescoco_v,
                cintura_v,
                quadril_v,
                abdomen_v,
            )
            _render_result(resultado)

            dados_medidas = {
                "altura_cm": altura_v,
                "pescoco_cm": pescoco_v,
                "cintura_cm": cintura_v,
                "quadril_cm": quadril_v,
                "abdomen_cm": abdomen_v,
            }
            salvar_lead_calculadora(
                nome=nome,
                celular=celular_digits,
                genero=genero,
                resultado_gordura=resultado,
                dados_medidas=dados_medidas,
            )
        except Exception:  # pragma: no cover - cálculo defensivo
            log.exception("Erro ao calcular gordura corporal")
            st.error("Não foi possível concluir o cálculo. Verifique as medidas e tente novamente.")


if __name__ == "__main__":
    main()
