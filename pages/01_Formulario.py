# pages/01_Formulario.py
"""Página multipage do formulário principal do NutriSigno."""

from __future__ import annotations

import os
import io
import uuid
import html
import unicodedata
from datetime import date, time, datetime
from typing import Dict

from PIL import Image
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go

import re

# Módulos internos do projeto
from modules import openai_utils, pdf_generator, email_utils
from modules import repo  # <- PostgreSQL (SQLAlchemy)

# Quando SIMULATE=1 (ou chaves faltarem), serviços externos são simulados
SIMULATE: bool = os.getenv("SIMULATE", "0") == "1"

# Caminhos de imagens ilustrativas (se não existirem, o app segue em fallback)
PATH_BRISTOL = "assets/escala_bistrol.jpeg"
PATH_URINA = "assets/escala_urina.jpeg"


# ---------------------------
# Helpers
# ---------------------------
def _to_float(v, default=0.0) -> float:
    """Converte qualquer valor (incluindo string '1,75') para float de forma segura."""
    if v is None:
        return float(default)
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.strip().replace(",", ".")
        try:
            return float(v)
        except ValueError:
            return float(default)
    return float(default)


_BR_DATE_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")

def parse_br_date(s: str) -> date | None:
    """
    Converte 'DD/MM/AAAA' -> datetime.date. Retorna None se inválida.
    """
    if not isinstance(s, str):
        return None
    m = _BR_DATE_RE.match(s)
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return date(y, mth, d)
    except ValueError:
        return None

def get_zodiac_sign(birth_date: date) -> str:
    """Retorna o signo do zodíaco para uma data de nascimento."""
    d = birth_date.day
    m = birth_date.month
    if (m == 3 and d >= 21) or (m == 4 and d <= 19):
        return "Áries"
    if (m == 4 and d >= 20) or (m == 5 and d <= 20):
        return "Touro"
    if (m == 5 and d >= 21) or (m == 6 and d <= 20):
        return "Gêmeos"
    if (m == 6 and d >= 21) or (m == 7 and d <= 22):
        return "Câncer"
    if (m == 7 and d >= 23) or (m == 8 and d <= 22):
        return "Leão"
    if (m == 8 and d >= 23) or (m == 9 and d <= 22):
        return "Virgem"
    if (m == 9 and d >= 23) or (m == 10 and d <= 22):
        return "Libra"
    if (m == 10 and d >= 23) or (m == 11 and d <= 21):
        return "Escorpião"
    if (m == 11 and d >= 22) or (m == 12 and d <= 21):
        return "Sagitário"
    if (m == 12 and d >= 22) or (m == 1 and d <= 19):
        return "Capricórnio"
    if (m == 1 and d >= 20) or (m == 2 and d <= 18):
        return "Aquário"
    if (m == 2 and d >= 19) or (m == 3 and d <= 20):
        return "Peixes"
    return ""


def initialize_session() -> None:
    """Inicializa variáveis na sessão do Streamlit."""
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())  # ainda usamos, mas pac_id será o id "canônico"
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "data" not in st.session_state:
        st.session_state.data = {}
    if "paid" not in st.session_state:
        st.session_state.paid = False
    if "plan" not in st.session_state:
        st.session_state.plan = None
    if "pac_id" not in st.session_state:
        st.session_state.pac_id = None  # id persistido no PostgreSQL


def next_step() -> None:
    """Incrementa o contador de etapas da sessão."""
    st.session_state.step += 1


# =========================
# UI — Seleção do Signo (GRID)
# =========================

# Mock de imagens/cores/ícones para os 12 signos (frontend)
SIGNO_META: Dict[str, Dict[str, str]] = {
    "Áries":       {"emoji": "♈", "color": "#E4572E", "img": "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1200&auto=format&fit=crop"},
    "Touro":       {"emoji": "♉", "color": "#8FB339", "img": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?q=80&w=1200&auto=format&fit=crop"},
    "Gêmeos":      {"emoji": "♊", "color": "#2E86AB", "img": "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?q=80&w=1200&auto=format&fit=crop"},
    "Câncer":      {"emoji": "♋", "color": "#4ECDC4", "img": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=1200&auto=format&fit=crop"},
    "Leão":        {"emoji": "♌", "color": "#F4B860", "img": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?q=80&w=1200&auto=format&fit=crop"},
    "Virgem":      {"emoji": "♍", "color": "#90A955", "img": "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?q=80&w=1200&auto=format&fit=crop"},
    "Libra":       {"emoji": "♎", "color": "#B497BD", "img": "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1200&auto=format&fit=crop"},
    "Escorpião":   {"emoji": "♏", "color": "#8E3B46", "img": "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1200&auto=format&fit=crop"},
    "Sagitário":   {"emoji": "♐", "color": "#F29E4C", "img": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?q=80&w=1200&auto=format&fit=crop"},
    "Capricórnio": {"emoji": "♑", "color": "#5B5B5B", "img": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?q=80&w=1200&auto=format&fit=crop"},
    "Aquário":     {"emoji": "♒", "color": "#2E6F59", "img": "https://images.unsplash.com/photo-1519681391659-ecd76f2f8f82?q=80&w=1200&auto=format&fit=crop"},
    "Peixes":      {"emoji": "♓", "color": "#6C91BF", "img": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=1200&auto=format&fit=crop"},
}

PRIMARY = "#2E6F59"
SOFT_BG = "#F1F5F4"
MUTED = "#5B5B5B"


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


def render_sign_grid(title: str = "Selecione seu signo", cols: int = 4) -> str | None:
    """Renderiza um grid com 12 imagens de signos. Retorna o signo escolhido ou None."""
    _inject_sign_grid_css()
    st.markdown(f"<div class='grid-title'>{title}</div>", unsafe_allow_html=True)

    signos = list(SIGNO_META.keys())
    selected: str | None = None
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
                st.markdown(f"<p class='sign-sub'>Clique para selecionar</p>", unsafe_allow_html=True)
                if st.button(f"Escolher {meta['emoji']}", key=f"sel_{name}"):
                    st.session_state["signo"] = name
                    st.session_state.data["signo"] = name
                    selected = name
                st.markdown("</div></div>", unsafe_allow_html=True)
    return selected


def render_selected_info() -> None:
    """Mostra um resumo do signo selecionado."""
    signo = st.session_state.get("signo") or st.session_state.data.get("signo")
    if not signo:
        return
    meta = SIGNO_META.get(signo, {"emoji": "•", "color": PRIMARY})
    st.markdown(
        f"<div class='soft-box'>Você selecionou: <b style='color:{meta['color']}'>{meta['emoji']} {signo}</b></div>",
        unsafe_allow_html=True,
    )


# =========================
# Dashboard helpers (compartilhados com o demo)
# =========================
DASH_MUTED = "#6b7280"

ZODIAC_SYMBOLS = {
    "áries": "♈︎", "touro": "♉︎", "gêmeos": "♊︎", "gemeos": "♊︎",
    "câncer": "♋︎", "cancer": "♋︎", "leão": "♌︎", "leao": "♌︎",
    "virgem": "♍︎", "libra": "♎︎", "escorpião": "♏︎", "escorpiao": "♏︎",
    "sagitário": "♐︎", "sagitario": "♐︎", "capricórnio": "♑︎", "capricornio": "♑︎",
    "aquário": "♒︎", "aquario": "♒︎", "peixes": "♓︎",
}

ELEMENT_MAP = {
    "Terra":  {"touro", "virgem", "capricornio", "capricórnio"},
    "Ar":     {"gêmeos", "gemeos", "libra", "aquário", "aquario"},
    "Fogo":   {"áries", "aries", "leão", "leao", "sagitário", "sagitario"},
    "Água":   {"câncer", "cancer", "escorpião", "escorpiao", "peixes"},
}

ELEMENT_ICONS = {
    "Terra": "🜃",
    "Ar": "🜁",
    "Fogo": "🜂",
    "Água": "🜄",
}

IMC_FAIXAS = [
    ("Magreza", 0.0, 18.5, "#7aa6f9"),
    ("Normal", 18.5, 25.0, "#55c169"),
    ("Sobrepeso", 25.0, 30.0, "#ffb347"),
    ("Obesidade I", 30.0, 35.0, "#ff7f50"),
    ("Obesidade II/III", 35.0, 60.0, "#e74c3c"),
]


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn"
    ).lower()


def _imc_categoria_cor(imc: float) -> tuple[str, str]:
    for nome, lo, hi, cor in IMC_FAIXAS:
        if lo <= imc < hi:
            return nome, cor
    return "Indefinido", "#95a5a6"


def _signo_symbol(signo: str) -> str:
    return ZODIAC_SYMBOLS.get((signo or "").strip().lower(), "✦")


def _signo_elemento(signo: str) -> str:
    s = (signo or "").strip().lower()
    s_norm = _strip_accents(s)
    for elem, conj in ELEMENT_MAP.items():
        if s in conj or s_norm in conj:
            return elem
    return "—"


def _element_icon(elem: str) -> str:
    return ELEMENT_ICONS.get(elem, "◆")


def _dashboard_style() -> None:
    st.markdown(
        f"""
        <style>
        .card {{
          background:#fff;border:1px solid #e6e6e6;border-radius:12px;
          padding:14px;box-shadow:0 2px 10px rgba(0,0,0,0.04);
        }}
        .card-title {{
          font-weight:700;font-size:0.95rem;color:#2c3e50;margin-bottom:8px;
        }}
        .square {{
          aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;
          font-size:64px;font-weight:700;border-radius:16px;border:1px dashed #e5e7eb;
          background:#fbfcfd;
        }}
        .square-element {{
          aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;
          font-size:56px;font-weight:700;border-radius:16px;border:1px dashed #e5e7eb;
          background:#fafbff;
        }}
        .small-muted {{ color:#718096;font-size:0.82rem;text-align:center;margin-top:6px;}}
        .kpi {{font-size:26px;font-weight:700;margin:6px 0;}}
        .sub {{color:{DASH_MUTED};font-size:13px;margin-top:2px;}}
        .chips > span {{
          display:inline-block;padding:6px 10px;margin:4px 6px 0 0;
          background:#f4f6f8;border:1px solid #e6ebef;border-radius:10px;
          font-size:0.85rem;color:#34495e;
        }}
        .two-col {{ display:grid;grid-template-columns:1fr 1fr;gap:12px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _plot_imc_horizontal(imc: float) -> tuple[go.Figure, str]:
    faixa_max = 40.0
    imc_clip = max(0.0, min(faixa_max, imc))
    categoria, cor = _imc_categoria_cor(imc_clip)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[faixa_max],
            y=["IMC"],
            orientation="h",
            marker=dict(color="#ecf0f1"),
            hoverinfo="skip",
            showlegend=False,
            width=0.5,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[imc_clip],
            y=["IMC"],
            orientation="h",
            marker=dict(color=cor),
            hovertemplate=f"IMC: {imc:.1f}<extra>{categoria}</extra>",
            showlegend=False,
            width=0.5,
        )
    )
    shapes = []
    for _, lim, _, _ in IMC_FAIXAS[1:]:
        shapes.append(
            dict(
                type="line",
                x0=lim,
                x1=lim,
                y0=-0.5,
                y1=0.5,
                line=dict(color="#d9dde1", width=1, dash="dot"),
            )
        )
    fig.update_layout(shapes=shapes)
    fig.update_layout(
        barmode="overlay",
        height=140,
        margin=dict(l=30, r=30, t=0, b=10),
        xaxis=dict(range=[0, faixa_max], showgrid=False, zeroline=False, title=None),
        yaxis=dict(showticklabels=False),
    )
    return fig, categoria


def _plot_agua(consumido: float, recomendado: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[consumido, recomendado],
            y=["Consumido", "Recomendado"],
            orientation="h",
            marker=dict(color=[PRIMARY, "#cbd5e1"]),
            showlegend=False,
            hovertemplate="%{y}: %{x:.1f} L<extra></extra>",
            width=0.45,
        )
    )
    fig.update_layout(
        height=180,
        margin=dict(l=30, r=30, t=0, b=10),
        xaxis=dict(showgrid=False, zeroline=False, title="Litros"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def _build_perfil_text(payload: Dict[str, object]) -> str:
    motiv = payload.get("motivacao")
    estresse = payload.get("estresse")
    energia = payload.get("energia_diaria")
    partes = []
    if motiv:
        partes.append(f"motivação {int(_to_float(motiv, motiv))}/5")
    if estresse:
        partes.append(f"estresse {int(_to_float(estresse, estresse))}/5")
    if energia:
        partes.append(f"energia {str(energia).lower()}")
    if partes:
        return "Perfil com " + "; ".join(partes) + "."
    return "Perfil em construção."


def _build_estrategia_text(peso: float, recomendado: float, categoria: str) -> str:
    partes = []
    if categoria and categoria != "Indefinido":
        partes.append(f"IMC na faixa {categoria.lower()}")
    if recomendado:
        partes.append(f"hidratação alvo ≈ {recomendado:.1f} L/dia")
    if not partes:
        return "Estratégia em construção com base nos próximos dados coletados."
    return "; ".join(partes) + "."


def _extract_bristol_tipo(texto: str | None, fallback: str = "") -> str:
    if not texto:
        return fallback or "—"
    match = re.search(r"tipo\s*(\d)", str(texto), flags=re.IGNORECASE)
    if match:
        return f"Tipo {match.group(1)}"
    return str(texto)


def _extract_cor_urina(texto: str | None, fallback: str = "") -> str:
    if not texto:
        return fallback or "—"
    base = str(texto).split("(")[0].strip()
    return base or (fallback or "—")


def _collect_comportamentos(payload: Dict[str, object]) -> list[str]:
    itens: list[str] = []
    for key in ("habitos_alimentares", "observacoes", "historico_saude"):
        raw = payload.get(key)
        if not raw:
            continue
        parts = [p.strip(" .\n") for p in re.split(r"[,;\n•]+", str(raw))]
        itens.extend([p for p in parts if p])
    return itens


# =========================
# APP
# =========================
def main() -> None:
    """Renderiza o formulário multipage do NutriSigno."""
    st.title("Formulário")
    st.write(
        "Bem-vindo ao NutriSigno! Preencha as etapas abaixo para receber um plano "
        "alimentar personalizado, combinando ciência e astrologia."
    )
    initialize_session()

    # Reabrir sessões antigas via parâmetro ?id=<pac_id> (PostgreSQL)
    pac_id_param = st.query_params.get("id")
    if pac_id_param and not st.session_state.get("loaded_external"):
        try:
            loaded = repo.get_by_pac_id(pac_id_param)
        except Exception:
            loaded = None
        if loaded:
            st.session_state.pac_id = loaded["pac_id"]
            st.session_state.data = loaded.get("respostas", {}) or {}
            st.session_state.plan = loaded.get("plano_alimentar")
            st.session_state.step = 6  # Painel de insights
            st.session_state.loaded_external = True

    # Barra de progresso: 7 etapas
    total_steps = 7
    progress = (st.session_state.step - 1) / total_steps
    st.progress(progress)

    # Etapa 1: dados pessoais
    if st.session_state.step == 1:
        st.header("1. Dados pessoais")

        # valores prévios (podem vir como string do session/query; garantimos float)
        _prev_peso = _to_float(st.session_state.data.get("peso"), 0.0)
        _prev_altura = _to_float(st.session_state.data.get("altura"), 0.0)

        with st.form("dados_pessoais"):
            nome = st.text_input("Nome completo", value=st.session_state.data.get("nome", ""))
            email = st.text_input("E-mail", value=st.session_state.data.get("email", ""))
            telefone = st.text_input("Telefone (WhatsApp)", value=st.session_state.data.get("telefone", ""))

            peso = st.number_input(
                "Peso (kg)",
                min_value=0.0,
                max_value=500.0,
                step=0.1,                 # float
                value=_prev_peso,         # float garantido
                format="%.2f",
            )
            altura = st.number_input(
                "Altura (cm)",
                min_value=0.0,
                max_value=300.0,
                step=1.0,                 # float (evita mistura int/float)
                value=_prev_altura,       # float garantido
                format="%.0f",
            )

            data_nasc_str = st.text_input(
                "Data de nascimento (DD/MM/AAAA)",
                value=st.session_state.data.get("data_nascimento", ""),  # preenche com string se já existir
                placeholder="ex: 27/03/1993",
            )
            hora_nasc = st.time_input(
                "Hora de nascimento",
                value=time.fromisoformat(st.session_state.data.get("hora_nascimento", "12:00:00"))
                if isinstance(st.session_state.data.get("hora_nascimento"), str) else time(12, 0)
            )
            local_nasc = st.text_input("Cidade e estado de nascimento", value=st.session_state.data.get("local_nascimento", ""))

            submitted = st.form_submit_button("Próximo", use_container_width=True)

            if submitted:
                # validação básica de preenchimento
                required_fields = [nome, email, telefone, data_nasc_str, local_nasc]
                if any(field in (None, "") for field in required_fields):
                    st.error("Por favor preencha todos os campos obrigatórios.")
                else:
                    # parse da data BR
                    data_nasc_date = parse_br_date(data_nasc_str)
                    if not data_nasc_date:
                        st.error("Data de nascimento inválida. Use o formato DD/MM/AAAA.")
                        st.stop()
                
                    signo_guess = get_zodiac_sign(data_nasc_date)
                    telefone_normalizado = repo.normalize_phone(telefone)
                
                    # guarda também o objeto date para ajudar em cálculos e defaults futuros
                    st.session_state.data["data_nasc_date"] = data_nasc_date
                
                    st.session_state.data.update({
                        "nome": nome.strip().title(),
                        "email": email.strip(),
                        "telefone": telefone_normalizado,
                        "peso": _to_float(peso),
                        "altura": _to_float(altura),
                        "data_nascimento": data_nasc_str.strip(),     # <<< string BR no banco
                        "hora_nascimento": hora_nasc.isoformat(),
                        "local_nascimento": local_nasc.strip(),
                        "signo": signo_guess,
                    })
                
                    st.session_state["signo"] = signo_guess
                    next_step()
    # Etapa 2: Seleção do Signo (GRID)
    elif st.session_state.step == 2:
        st.header("2. Selecione seu signo")
        st.caption("Confirme seu signo escolhendo uma das imagens abaixo.")
        _ = render_sign_grid(cols=4)
        render_selected_info()
        cols = st.columns([1, 1])
        with cols[0]:
            if st.button("Voltar ◀️"):
                st.session_state.step = 1
        with cols[1]:
            if st.session_state.get("signo"):
                if st.button("Continuar ▶️"):
                    next_step()
            else:
                st.info("Selecione um signo para continuar.")

    # Etapa 3: avaliação nutricional
    elif st.session_state.step == 3:
        st.header("3. Avaliação nutricional")
        with st.form("avaliacao_nutricional"):
            historico = st.text_area(
                "Histórico de saúde e medicamentos",
                help="Descreva brevemente quaisquer condições médicas ou medicamentos em uso.",
                value=st.session_state.data.get("historico_saude", "")
            )
            consumo_agua = st.number_input(
                "Consumo diário de água (litros)",
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                value=_to_float(st.session_state.data.get("consumo_agua"), 1.5),
                format="%.1f",
            )
            atividade = st.selectbox(
                "Nível de atividade física",
                ["Sedentário", "Leve", "Moderado", "Intenso"],
                index=["Sedentário", "Leve", "Moderado", "Intenso"].index(
                    st.session_state.data.get("nivel_atividade", "Moderado")
                ),
            )
            st.markdown("---")
            st.subheader("Tipo de Fezes (Escala de Bristol)")
            col_bristol1, col_bristol2 = st.columns([1, 2])
            with col_bristol1:
                try:
                    st.image(Image.open(PATH_BRISTOL), caption='Escala de Bristol', use_column_width=True)
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
                    index=0
                )
            st.markdown("---")
            st.subheader("Cor da Urina")
            col_urina1, col_urina2 = st.columns([1, 2])
            with col_urina1:
                try:
                    st.image(Image.open(PATH_URINA), caption='Classificação da Urina', use_column_width=True)
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
                    index=1
                )
            submitted = st.form_submit_button("Próximo", use_container_width=True)
            if submitted:
                required = [historico, consumo_agua, atividade, tipo_fezes, cor_urina]
                if any(field in (None, "") for field in required):
                    st.error("Por favor preencha todos os campos.")
                else:
                    st.session_state.data.update({
                        "historico_saude": historico,
                        "consumo_agua": _to_float(consumo_agua, 1.5),
                        "nivel_atividade": atividade,
                        "tipo_fezes": tipo_fezes,
                        "cor_urina": cor_urina,
                    })
                    next_step()

    # Etapa 4: avaliação psicológica e de perfil
    elif st.session_state.step == 4:
        st.header("4. Avaliação psicológica e perfil")
        with st.form("avaliacao_psicologica"):
            motivacao = st.slider(
                "Nível de motivação para mudanças alimentares", 1, 5,
                int(st.session_state.data.get("motivacao", 3))
            )
            estresse = st.slider(
                "Nível de estresse atual", 1, 5,
                int(st.session_state.data.get("estresse", 3))
            )
            habitos = st.text_area(
                "Descreva brevemente seus hábitos alimentares",
                value=st.session_state.data.get("habitos_alimentares", ""),
            )
            energia = st.select_slider(
                "Como você descreveria sua energia diária?",
                options=["Baixa", "Moderada", "Alta"],
                value=st.session_state.data.get("energia_diaria", "Moderada"),
            )
            impulsividade = st.slider(
                "Quão impulsivo(a) você é em relação à alimentação?", 1, 5,
                int(st.session_state.data.get("impulsividade_alimentar", 3))
            )
            rotina = st.slider(
                "Quão importante é para você seguir uma rotina alimentar?", 1, 5,
                int(st.session_state.data.get("rotina_alimentar", 3))
            )
            submitted = st.form_submit_button("Próximo", use_container_width=True)
            if submitted:
                required = [motivacao, estresse, habitos]
                if any(field in (None, "") for field in required):
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    st.session_state.data.update({
                        "motivacao": int(motivacao),
                        "estresse": int(estresse),
                        "habitos_alimentares": habitos,
                        "energia_diaria": energia,
                        "impulsividade_alimentar": int(impulsividade),
                        "rotina_alimentar": int(rotina),
                    })
                    next_step()

    # Etapa 5: avaliação geral
    elif st.session_state.step == 5:
        st.header("5. Avaliação geral")
        with st.form("avaliacao_geral"):
            observacoes = st.text_area(
                "Observações adicionais",
                help="Compartilhe qualquer informação extra que julgue relevante.",
                value=st.session_state.data.get("observacoes", "")
            )
            submitted = st.form_submit_button("Prosseguir para insights", use_container_width=True)
            if submitted:
                st.session_state.data.update({"observacoes": observacoes})
                next_step()

    # Etapa 6: painel de insights
    elif st.session_state.step == 6:
        st.header("6. Painel de insights")

        # 1) Obter insights (com fallback hard)
        try:
            ai_pack = openai_utils.generate_insights(st.session_state.data)
            insights = ai_pack.get("insights", {})
            ai_summary = ai_pack.get("ai_summary", "Resumo indisponível (modo simulado).")
        except Exception as e:
            st.warning(f"Modo fallback automático: {e}")
            peso_fallback = _to_float(st.session_state.data.get("peso"), 70)
            altura_fallback = _to_float(st.session_state.data.get("altura"), 170)
            altura_m_fallback = max(0.1, altura_fallback / 100.0)
            bmi = round(peso_fallback / (altura_m_fallback ** 2), 1)
            insights = {
                "bmi": bmi,
                "bmi_category": "Eutrofia" if 18.5 <= bmi < 25 else ("Baixo peso" if bmi < 18.5 else ("Sobrepeso" if bmi < 30 else "Obesidade")),
                "water_status": "OK",
                "bristol": "Padrão dentro do esperado",
                "urine": "Hidratado",
                "motivacao": int(st.session_state.data.get("motivacao") or 3),
                "estresse": int(st.session_state.data.get("estresse") or 3),
                "sign_hint": "Use seu signo como inspiração, não como prescrição.",
                "consumption": {
                    "water_liters": _to_float(st.session_state.data.get("consumo_agua"), 1.5),
                    "recommended_liters": round(max(1.5, peso_fallback * 0.035), 1),
                },
            }
            ai_summary = "Resumo simulado (fallback hard)."

        payload = st.session_state.data
        peso = _to_float(payload.get("peso"), 0.0)
        altura_cm = _to_float(payload.get("altura"), 0.0)
        altura_m = round(altura_cm / 100.0, 2) if altura_cm else 0.0
        imc = round(peso / (altura_m ** 2), 1) if peso and altura_m else 0.0

        imc_value = insights.get("bmi")
        if not imc_value and imc:
            imc_value = imc
        if imc_value is None:
            imc_value = 0.0
        insights["bmi"] = _to_float(imc_value, 0.0)
        categoria_base = insights.get("bmi_category") or _imc_categoria_cor(insights["bmi"])[0]
        insights["bmi_category"] = categoria_base

        consumo_info = insights.get("consumption") or {}
        consumo_real = _to_float(consumo_info.get("water_liters"), _to_float(payload.get("consumo_agua"), 0.0))
        recomendado = _to_float(
            consumo_info.get("recommended_liters"),
            round(max(1.5, peso * 0.035), 1) if peso else 2.0,
        )
        insights["consumption"] = {
            "water_liters": consumo_real,
            "recommended_liters": recomendado,
        }
        insights.setdefault("water_status", "OK" if recomendado and consumo_real >= recomendado else "Abaixo do ideal")
        insights.setdefault("motivacao", int(_to_float(payload.get("motivacao"), 0)))
        insights.setdefault("estresse", int(_to_float(payload.get("estresse"), 0)))
        insights.setdefault("bristol", _extract_bristol_tipo(payload.get("tipo_fezes")))
        insights.setdefault("urine", _extract_cor_urina(payload.get("cor_urina")))
        insights.setdefault("sign_hint", "Use seu signo como inspiração de hábitos saudáveis.")

        signo = payload.get("signo") or "—"
        elemento = _signo_elemento(signo)
        elemento_icon = _element_icon(elemento)
        perfil_text = _build_perfil_text(payload)
        estrategia_text = _build_estrategia_text(peso, recomendado, categoria_base)
        bristol_tipo = _extract_bristol_tipo(payload.get("tipo_fezes"), insights.get("bristol", ""))
        cor_urina = _extract_cor_urina(payload.get("cor_urina"), insights.get("urine", ""))
        comportamentos = _collect_comportamentos(payload)

        _dashboard_style()

        col_signo, col_elem, col_perfil, col_estrat = st.columns([1, 1, 2, 2], gap="medium")

        with col_signo:
            st.markdown('<div class="card"><div class="card-title">Signo</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="square">{html.escape(_signo_symbol(signo))}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="small-muted">{html.escape(str(signo))}</div></div>',
                unsafe_allow_html=True,
            )

        with col_elem:
            st.markdown('<div class="card"><div class="card-title">Elemento</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="square-element">{html.escape(elemento_icon)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="small-muted">{html.escape(elemento)}</div></div>',
                unsafe_allow_html=True,
            )

        with col_perfil:
            st.markdown(
                f'''
                <div class="card">
                  <div class="card-title">Perfil da Pessoa</div>
                  <div class="kpi" style="font-size:18px">{html.escape(perfil_text)}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

        with col_estrat:
            st.markdown(
                f'''
                <div class="card">
                  <div class="card-title">Estratégia Nutricional</div>
                  <div class="kpi" style="font-size:18px">{html.escape(estrategia_text)}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="two-col">', unsafe_allow_html=True)
        st.markdown(
            f'''
            <div class="card">
              <div class="card-title">Bristol (fezes)</div>
              <div class="kpi" style="font-size:18px">Bristol</div>
              <div class="sub">{html.escape(str(bristol_tipo))}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'''
            <div class="card">
              <div class="card-title">Cor da urina</div>
              <div class="kpi" style="font-size:18px">Cor</div>
              <div class="sub">{html.escape(str(cor_urina))}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        colA, colB = st.columns(2, gap="medium")
        with colA:
            fig_imc, categoria_imc = _plot_imc_horizontal(insights["bmi"] or 0.0)
            has_imc = insights["bmi"] > 0
            categoria_display = categoria_imc if has_imc else "Indisponível"
            st.markdown('<div class="card"><div class="card-title">IMC</div>', unsafe_allow_html=True)
            st.plotly_chart(fig_imc, use_container_width=True, config={"displayModeBar": False})
            imc_text = f"{insights['bmi']:.1f}" if has_imc else "--"
            peso_text = f"{peso:.1f} kg" if peso else "--"
            altura_text = f"{altura_m:.2f} m" if altura_m else "--"
            st.markdown(
                f'<div class="sub"><b>Categoria:</b> {html.escape(categoria_display)} &nbsp; '
                f'<b>IMC:</b> {imc_text} &nbsp; '
                f'<b>Peso:</b> {peso_text} &nbsp; '
                f'<b>Altura:</b> {altura_text}</div></div>',
                unsafe_allow_html=True,
            )

        with colB:
            fig_agua = _plot_agua(consumo_real, recomendado)
            st.markdown('<div class="card"><div class="card-title">Hidratação</div>', unsafe_allow_html=True)
            st.plotly_chart(fig_agua, use_container_width=True, config={"displayModeBar": False})
            ok = recomendado and consumo_real >= recomendado
            badge = (
                '<span style="background:#e8f7ef;color:#127a46;padding:2px 8px;border-radius:999px;font-size:12px">Meta atingida</span>'
                if ok
                else '<span style="background:#fff5e6;color:#8a5200;padding:2px 8px;border-radius:999px;font-size:12px">Abaixo do ideal</span>'
            )
            st.markdown(f'<div class="sub">{badge}</div></div>', unsafe_allow_html=True)

        chips = "".join([f"<span>{html.escape(x)}</span>" for x in comportamentos]) or '<span style="color:#718096;">Sem itens cadastrados.</span>'
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">Comportamento</div>
              <div class="card" style="background:#fbfcfd;border:1px dashed #e6ebef;">
                <div class="chips">{chips}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Resumo dos insights"):
            st.write(ai_summary)

        def build_insights_pdf_bytes(ins):
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import cm
                buf = io.BytesIO()
                c = canvas.Canvas(buf, pagesize=A4)
                y = 28 * cm
                c.setFont("Helvetica-Bold", 14)
                c.drawString(2 * cm, y, "NutriSigno — Painel de Insights")
                y -= 1 * cm
                c.setFont("Helvetica", 10)
                for k, v in [
                    ("IMC", f"{ins['bmi']} ({ins['bmi_category']})"),
                    (
                        "Hidratação",
                        f"{ins['consumption']['water_liters']} / {ins['consumption']['recommended_liters']} L",
                    ),
                    ("Bristol", ins["bristol"]),
                    ("Urina", ins["urine"]),
                    ("Motivação/Estresse", f"{ins['motivacao']}/5 · {ins['estresse']}/5"),
                    ("Insight do signo", ins["sign_hint"]),
                ]:
                    c.drawString(2 * cm, y, f"{k}: {v}")
                    y -= 0.8 * cm
                    if y < 2 * cm:
                        c.showPage()
                        y = 28 * cm
                c.save()
                buf.seek(0)
                return buf.getvalue()
            except Exception:
                return b"%PDF-1.4\n% fallback vazio"

        def build_share_png_bytes(ins):
            fig = plt.figure(figsize=(6, 6), dpi=200)
            plt.title("NutriSigno — Resumo", pad=12)
            text = (
                f"IMC: {ins['bmi']} ({ins['bmi_category']})\n"
                f"Hidratação: {ins['consumption']['water_liters']} / {ins['consumption']['recommended_liters']} L\n"
                f"Bristol: {ins['bristol']}\nUrina: {ins['urine']}\n"
                f"Motivação/Estresse: {ins['motivacao']}/5 · {ins['estresse']}/5\n"
                f"Signo: {ins.get('sign_hint','')}\n#NutriSigno"
            )
            plt.axis("off")
            plt.text(0.02, 0.98, text, va="top", ha="left", wrap=True)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            plt.close(fig)
            return buf.getvalue()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "Exportar PDF",
                data=build_insights_pdf_bytes(insights),
                file_name="insights.pdf",
                mime="application/pdf",
            )
        with c2:
            st.download_button(
                "Baixar imagem",
                data=build_share_png_bytes(insights),
                file_name="insights.png",
                mime="image/png",
            )
        with c3:
            if st.button("Gerar plano nutricional e prosseguir para pagamento"):
                st.session_state.step += 1
                st.rerun()

    # Etapa 7: pagamento e geração do plano
    elif st.session_state.step == 7:
        st.header("7. Pagamento e geração do plano")
        st.write(
            "Para finalizar, realize o pagamento abaixo. Este exemplo utiliza um "
            "botão simbólico; substitua por sua integração de pagamento real em produção."
        )
        if not st.session_state.paid:
            if st.button("Realizar pagamento (exemplo)"):
                st.session_state.paid = True
                st.success("Pagamento confirmado! Gerando seu plano...")

        if st.session_state.paid and st.session_state.plan is None:
            with st.spinner("Gerando plano personalizado, por favor aguarde..."):
                # 1) Gera o plano via OpenAI
                try:
                    plan_dict = openai_utils.generate_plan(st.session_state.data)
                    st.session_state.plan = plan_dict
                except Exception as e:
                    st.error(f"Erro ao gerar plano com a OpenAI: {e}")
                    return

                # 2) (Opcional) calcular macros e plano_compacto, se seu openai_utils não já retornar
                try:
                    macros = openai_utils.calcular_macros(st.session_state.plan)
                except Exception:
                    macros = {}
                try:
                    plano_compacto = openai_utils.resumir_plano(st.session_state.plan)
                except Exception:
                    plano_compacto = {}

                # 3) Persiste tudo no PostgreSQL (cria/atualiza e obtém pac_id)
                try:
                    pac_id = repo.upsert_patient_payload(
                        pac_id=st.session_state.get("pac_id"),
                        respostas=st.session_state.data,   # contém "data_nascimento" em DD/MM/AAAA
                        plano=st.session_state.plan,
                        plano_compacto=plano_compacto,
                        macros=macros,
                        name=st.session_state.data.get("nome"),
                        email=st.session_state.data.get("email"),
                    )
                    st.session_state.pac_id = pac_id
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")
                    return

                # 4) Gera PDF (plano final)
                pdf_path = f"/tmp/{st.session_state.pac_id or st.session_state.user_id}.pdf"
                try:
                    pdf_generator.create_pdf_report(
                        st.session_state.data,
                        st.session_state.plan,
                        pdf_path,
                    )
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                except Exception as e:
                    st.error(f"Erro ao gerar o PDF: {e}")
                    return

                # 5) Envia e-mail com link de reabertura (via ?id=<pac_id>)
                try:
                    base_url = os.getenv("PUBLIC_BASE_URL", "")
                    # Link estável para reabrir painel por pac_id
                    panel_link = f"{base_url}/?id={st.session_state.pac_id}" if base_url else f"/?id={st.session_state.pac_id}"
                    subject = "Seu Plano Alimentar NutriSigno"
                    body = (
                        "Olá {nome},\n\n"
                        "Em anexo está o seu plano alimentar personalizado gerado pelo NutriSigno. "
                        "Siga as orientações com responsabilidade e, se possível, consulte um profissional "
                        "da saúde antes de iniciar qualquer mudança significativa.\n\n"
                        "Você poderá acessar novamente o painel de insights por meio do link abaixo:\n"
                        f"{panel_link}\n\n"
                        "Atenciosamente,\nEquipe NutriSigno"
                    ).format(nome=st.session_state.data.get('nome'))
                    attachments = [(f"nutrisigno_plano_{st.session_state.pac_id}.pdf", pdf_bytes)]
                    if not SIMULATE:
                        email_utils.send_email(
                            recipient=st.session_state.data.get('email'),
                            subject=subject,
                            body=body,
                            attachments=attachments,
                        )
                except Exception as e:
                    st.error(f"Erro ao enviar e-mail: {e}")
                    return

                st.success("Plano gerado e enviado por e-mail!")
                st.download_button(
                    label="Baixar plano em PDF",
                    data=pdf_bytes,
                    file_name=f"nutrisigno_plano_{st.session_state.pac_id}.pdf",
                    mime="application/pdf",
                )
                st.markdown(
                    f"Você pode revisitar seus insights quando quiser através deste link: "
                    f"[Painel de Insights](/?id={st.session_state.pac_id})"
                )


if __name__ == "__main__":
    main()
