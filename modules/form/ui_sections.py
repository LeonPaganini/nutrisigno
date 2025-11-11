"""Streamlit UI sections for the form steps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time
from typing import Any, Dict, List, Optional

from PIL import Image
import streamlit as st

PATH_BRISTOL = "assets/escala_bistrol.jpeg"
PATH_URINA = "assets/escala_urina.jpeg"


@dataclass
class SectionResult:
    data: Dict[str, Any]
    errors: List[str]
    advance: bool = False
    go_back: bool = False


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return float(default)
    return float(default)


_BR_DATE_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")


def parse_br_date(value: str) -> date | None:
    if not isinstance(value, str):
        return None
    match = _BR_DATE_RE.match(value)
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


SIGNO_META: Dict[str, Dict[str, str]] = {
    "Áries": {"emoji": "♈", "color": "#E4572E", "img": "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1200&auto=format&fit=crop"},
    "Touro": {"emoji": "♉", "color": "#8FB339", "img": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?q=80&w=1200&auto=format&fit=crop"},
    "Gêmeos": {"emoji": "♊", "color": "#2E86AB", "img": "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?q=80&w=1200&auto=format&fit=crop"},
    "Câncer": {"emoji": "♋", "color": "#4ECDC4", "img": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=1200&auto=format&fit=crop"},
    "Leão": {"emoji": "♌", "color": "#F4B860", "img": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?q=80&w=1200&auto=format&fit=crop"},
    "Virgem": {"emoji": "♍", "color": "#90A955", "img": "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?q=80&w=1200&auto=format&fit=crop"},
    "Libra": {"emoji": "♎", "color": "#B497BD", "img": "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1200&auto=format&fit=crop"},
    "Escorpião": {"emoji": "♏", "color": "#8E3B46", "img": "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1200&auto=format&fit=crop"},
    "Sagitário": {"emoji": "♐", "color": "#F29E4C", "img": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?q=80&w=1200&auto=format&fit=crop"},
    "Capricórnio": {"emoji": "♑", "color": "#5B5B5B", "img": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?q=80&w=1200&auto=format&fit=crop"},
    "Aquário": {"emoji": "♒", "color": "#2E6F59", "img": "https://images.unsplash.com/photo-1519681391659-ecd76f2f8f82?q=80&w=1200&auto=format&fit=crop"},
    "Peixes": {"emoji": "♓", "color": "#6C91BF", "img": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=1200&auto=format&fit=crop"},
}

PRIMARY = "#2E6F59"
SOFT_BG = "#F1F5F4"
MUTED = "#5B5B5B"


def get_zodiac_sign(birth_date: date) -> str:
    day = birth_date.day
    month = birth_date.month
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "Áries"
    if (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "Touro"
    if (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "Gêmeos"
    if (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "Câncer"
    if (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "Leão"
    if (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "Virgem"
    if (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "Libra"
    if (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "Escorpião"
    if (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "Sagitário"
    if (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "Capricórnio"
    if (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "Aquário"
    if (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return "Peixes"
    return ""


def _inject_sign_grid_css() -> None:
    st.markdown(
        f"""
        <style>
        .sign-card {{
            border-radius: 14px;
            overflow: hidden;
            background: #fff;
            border: 1px solid #e9eeec;
            transition: transform .12s ease, box-shadow .12s ease;
            cursor: pointer;
        }}
        .sign-card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }}
        .sign-img {{ width: 100%; height: 140px; object-fit: cover; display:block; }}
        .sign-body {{ padding: 10px 12px 12px 12px; }}
        .sign-title {{ margin:0; font-weight: 800; color: {PRIMARY}; }}
        .sign-sub {{ margin:2px 0 0 0; color: {MUTED}; font-size:.92rem; }}
        .grid-title {{ margin-bottom: 8px; font-weight:800; color:{PRIMARY}; font-size:1.2rem; }}
        .soft-box {{ background: linear-gradient(135deg, {SOFT_BG}, #fff); border:1px solid #e8eceb; border-radius:16px; padding:18px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sign_grid(title: str = "Selecione seu signo", cols: int = 4) -> Optional[str]:
    _inject_sign_grid_css()
    st.markdown(f"<div class='grid-title'>{title}</div>", unsafe_allow_html=True)
    signos = list(SIGNO_META.keys())
    selected: Optional[str] = None
    for i in range(0, len(signos), cols):
        row = st.columns(cols, gap="small")
        for j, col in enumerate(row):
            idx = i + j
            if idx >= len(signos):
                continue
            name = signos[idx]
            meta = SIGNO_META[name]
            with col:
                st.markdown("<div class='sign-card'>", unsafe_allow_html=True)
                st.markdown(f"<img class='sign-img' src='{meta['img']}' alt='{name}'>", unsafe_allow_html=True)
                st.markdown("<div class='sign-body'>", unsafe_allow_html=True)
                st.markdown(f"<p class='sign-title'>{meta['emoji']} {name}</p>", unsafe_allow_html=True)
                st.markdown("<p class='sign-sub'>Clique para selecionar</p>", unsafe_allow_html=True)
                if st.button(f"Escolher {meta['emoji']}", key=f"sel_{name}"):
                    selected = name
                st.markdown("</div></div>", unsafe_allow_html=True)
    return selected


def render_selected_info(signo: Optional[str]) -> None:
    if not signo:
        return
    meta = SIGNO_META.get(signo, {"emoji": "•", "color": PRIMARY})
    st.markdown(
        f"<div class='soft-box'>Você selecionou: <b style='color:{meta['color']}'>{meta['emoji']} {signo}</b></div>",
        unsafe_allow_html=True,
    )


def personal_data_section(session_data: Dict[str, Any]) -> SectionResult:
    st.header("1. Dados pessoais")
    prev_weight = _to_float(session_data.get("peso"), 0.0)
    prev_height = _to_float(session_data.get("altura"), 0.0)

    with st.form("dados_pessoais"):
        nome = st.text_input("Nome completo", value=session_data.get("nome", ""))
        email = st.text_input("E-mail", value=session_data.get("email", ""))
        telefone = st.text_input("Telefone (WhatsApp)", value=session_data.get("telefone", ""))
        peso = st.number_input(
            "Peso (kg)",
            min_value=0.0,
            max_value=500.0,
            step=0.1,
            value=prev_weight,
            format="%.2f",
        )
        altura = st.number_input(
            "Altura (cm)",
            min_value=0.0,
            max_value=300.0,
            step=1.0,
            value=prev_height,
            format="%.0f",
        )
        data_nasc_str = st.text_input(
            "Data de nascimento (DD/MM/AAAA)",
            value=session_data.get("data_nascimento", ""),
            placeholder="ex: 27/03/1993",
        )
        hora_nasc = st.time_input(
            "Hora de nascimento",
            value=time.fromisoformat(session_data.get("hora_nascimento", "12:00:00"))
            if isinstance(session_data.get("hora_nascimento"), str)
            else time(12, 0),
        )
        local_nasc = st.text_input(
            "Cidade e estado de nascimento",
            value=session_data.get("local_nascimento", ""),
        )
        submitted = st.form_submit_button("Próximo", use_container_width=True)

    if not submitted:
        return SectionResult({}, [])

    errors: List[str] = []
    required_fields = [nome, email, telefone, data_nasc_str, local_nasc]
    if any(field in (None, "") for field in required_fields):
        errors.append("Por favor preencha todos os campos obrigatórios.")
    data_date = parse_br_date(data_nasc_str.strip())
    if not data_date:
        errors.append("Data de nascimento inválida. Use o formato DD/MM/AAAA.")

    if errors:
        for err in errors:
            st.error(err)
        return SectionResult({}, errors)

    signo_guess = get_zodiac_sign(data_date)
    section_data = {
        "nome": nome.strip().title(),
        "email": email.strip(),
        "telefone": telefone,
        "peso": _to_float(peso),
        "altura": _to_float(altura),
        "data_nascimento": data_nasc_str.strip(),
        "hora_nascimento": hora_nasc.isoformat(),
        "local_nascimento": local_nasc.strip(),
        "signo": signo_guess,
        "data_nasc_date": data_date,
    }
    return SectionResult(section_data, [], advance=True)


def sign_selection_section(current_sign: Optional[str]) -> SectionResult:
    st.header("2. Selecione seu signo")
    st.caption("Confirme seu signo escolhendo uma das imagens abaixo.")
    selected = render_sign_grid(cols=4)
    render_selected_info(current_sign or selected)
    cols = st.columns([1, 1])
    advance = False
    go_back = False
    with cols[0]:
        if st.button("Voltar ◀️"):
            go_back = True
    with cols[1]:
        if current_sign or selected:
            if st.button("Continuar ▶️"):
                advance = True
        else:
            st.info("Selecione um signo para continuar.")
    data = {}
    if selected:
        data["signo"] = selected
    return SectionResult(data, [], advance=advance, go_back=go_back)


def nutrition_section(session_data: Dict[str, Any]) -> SectionResult:
    st.header("3. Avaliação nutricional")
    with st.form("avaliacao_nutricional"):
        historico = st.text_area(
            "Histórico de saúde e medicamentos",
            help="Descreva brevemente quaisquer condições médicas ou medicamentos em uso.",
            value=session_data.get("historico_saude", ""),
        )
        consumo_agua = st.number_input(
            "Consumo diário de água (litros)",
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            value=_to_float(session_data.get("consumo_agua"), 1.5),
            format="%.1f",
        )
        atividade = st.selectbox(
            "Nível de atividade física",
            ["Sedentário", "Leve", "Moderado", "Intenso"],
            index=["Sedentário", "Leve", "Moderado", "Intenso"].index(
                session_data.get("nivel_atividade", "Moderado")
            ),
        )
        st.markdown("---")
        st.subheader("Tipo de Fezes (Escala de Bristol)")
        col_bristol1, col_bristol2 = st.columns([1, 2])
        with col_bristol1:
            try:
                st.image(Image.open(PATH_BRISTOL), caption="Escala de Bristol", use_column_width=True)
            except Exception:
                st.info("Imagem da escala de Bristol não encontrada.")
        with col_bristol2:
            tipo_fezes = st.radio(
                "Selecione o tipo correspondente:",
                [
                    "Tipo 1 - Pequenos fragmentos duros, semelhantes a nozes.",
                    "Tipo 2 - Em forma de salsicha, mas com grumos.",
                    "Tipo 3 - Em forma de salsicha, com fissuras à superfície.",
                    "Tipo 4 - Em forma de salsicha ou cobra, mais finas, mas suaves e macias.",
                    "Tipo 5 - Fezes fragmentadas, mas em pedaços com contornos bem definidos e macias.",
                    "Tipo 6 - Em pedaços esfarrapados.",
                    "Tipo 7 - Líquidas.",
                ],
                key="tipo_fezes",
                index=0,
            )
        st.markdown("---")
        st.subheader("Cor da Urina")
        col_urina1, col_urina2 = st.columns([1, 2])
        with col_urina1:
            try:
                st.image(Image.open(PATH_URINA), caption="Classificação da Urina", use_column_width=True)
            except Exception:
                st.info("Imagem da escala de cor da urina não encontrada.")
        with col_urina2:
            cor_urina = st.radio(
                "Selecione a cor que mais se aproxima da sua urina:",
                [
                    "Transparente (parabéns, você está hidratado(a)!)",
                    "Amarelo muito claro (parabéns, você está hidratado(a)!)",
                    "Amarelo claro (atenção, moderadamente desidratado)",
                    "Amarelo (atenção, moderadamente desidratado)",
                    "Amarelo escuro (perigo, procure atendimento!)",
                    "Castanho claro (perigo extremo, MUITO desidratado!)",
                    "Castanho escuro (perigo extremo, MUITO desidratado!)",
                ],
                key="cor_urina",
                index=1,
            )
        submitted = st.form_submit_button("Próximo", use_container_width=True)

    if not submitted:
        return SectionResult({}, [])

    required = [historico, consumo_agua, atividade, tipo_fezes, cor_urina]
    if any(field in (None, "") for field in required):
        msg = "Por favor preencha todos os campos."
        st.error(msg)
        return SectionResult({}, [msg])

    section_data = {
        "historico_saude": historico,
        "consumo_agua": _to_float(consumo_agua, 1.5),
        "nivel_atividade": atividade,
        "tipo_fezes": tipo_fezes,
        "cor_urina": cor_urina,
    }
    return SectionResult(section_data, [], advance=True)


def psychological_section(session_data: Dict[str, Any]) -> SectionResult:
    st.header("4. Avaliação psicológica e perfil")
    with st.form("avaliacao_psicologica"):
        motivacao = st.slider(
            "Nível de motivação para mudanças alimentares", 1, 5,
            int(session_data.get("motivacao", 3))
        )
        estresse = st.slider(
            "Nível de estresse atual", 1, 5,
            int(session_data.get("estresse", 3))
        )
        habitos = st.text_area(
            "Descreva brevemente seus hábitos alimentares",
            value=session_data.get("habitos_alimentares", ""),
        )
        energia = st.select_slider(
            "Como você descreveria sua energia diária?",
            options=["Baixa", "Moderada", "Alta"],
            value=session_data.get("energia_diaria", "Moderada"),
        )
        impulsividade = st.slider(
            "Quão impulsivo(a) você é em relação à alimentação?", 1, 5,
            int(session_data.get("impulsividade_alimentar", 3))
        )
        rotina = st.slider(
            "Quão importante é para você seguir uma rotina alimentar?", 1, 5,
            int(session_data.get("rotina_alimentar", 3))
        )
        submitted = st.form_submit_button("Próximo", use_container_width=True)

    if not submitted:
        return SectionResult({}, [])

    required = [motivacao, estresse, habitos]
    if any(field in (None, "") for field in required):
        msg = "Preencha todos os campos obrigatórios."
        st.error(msg)
        return SectionResult({}, [msg])

    section_data = {
        "motivacao": int(motivacao),
        "estresse": int(estresse),
        "habitos_alimentares": habitos,
        "energia_diaria": energia,
        "impulsividade_alimentar": int(impulsividade),
        "rotina_alimentar": int(rotina),
    }
    return SectionResult(section_data, [], advance=True)


def review_section(session_data: Dict[str, Any]) -> SectionResult:
    st.header("5. Avaliação geral")
    with st.form("avaliacao_geral"):
        observacoes = st.text_area(
            "Observações adicionais",
            help="Compartilhe qualquer informação extra que julgue relevante.",
            value=session_data.get("observacoes", ""),
        )
        submitted = st.form_submit_button("Prosseguir para insights", use_container_width=True)

    if not submitted:
        return SectionResult({}, [])

    return SectionResult({"observacoes": observacoes}, [], advance=True)
