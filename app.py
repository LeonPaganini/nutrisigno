"""Aplicação principal do NutriSigno.

Esta aplicação Streamlit coleta dados do usuário em várias etapas,
interage com a API da OpenAI para criar um plano alimentar
personalizado, salva os dados no Firebase e envia um relatório em PDF
por e-mail após a confirmação do pagamento. Nesta versão a
apresentação de dados foi enriquecida com um painel de insights
personalizados, uma etapa visual de seleção do signo (grid com 12
imagens) e um mecanismo para reabrir sessões antigas a partir de
um identificador na URL.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, time
from typing import Dict, Any

from PIL import Image
import streamlit as st

from modules import firebase_utils, openai_utils, pdf_generator, email_utils, dashboard_utils

# When SIMULATE=1 (or unspecified keys are missing) the external
# services (OpenAI, Firebase and SMTP) will be simulated. This is
# configured entirely in the environment and reused by the modules.
SIMULATE: bool = os.getenv("SIMULATE", "0") == "1"

# Paths to the illustrative images for the Bristol stool scale and urine colour
PATH_BRISTOL = "assets/escala_bistrol.jpeg"
PATH_URINA = "assets/escala_urina.jpeg"


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
        st.session_state.user_id = str(uuid.uuid4())
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "data" not in st.session_state:
        st.session_state.data = {}
    if "paid" not in st.session_state:
        st.session_state.paid = False
    if "plan" not in st.session_state:
        st.session_state.plan = None


def next_step() -> None:
    """Incrementa o contador de etapas da sessão."""
    st.session_state.step += 1


# =========================
# UI — Seleção do Signo (GRID)
# =========================

# Mock de imagens/cores/ícones para os 12 signos (apenas frontend)
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
# APP
# =========================
def main() -> None:
    """Função principal invocada pelo Streamlit para renderizar a app."""
    # Configuração da página
    st.set_page_config(page_title="NutriSigno", layout="wide")
    initialize_session()

    # Reabrir sessões antigas via parâmetro ?id=<uuid>
    params = st.query_params
    session_id = params.get("id", [None])[0] if params else None
    if session_id and not st.session_state.get("loaded_external"):
        saved_data = firebase_utils.load_user_data(session_id)
        if saved_data:
            st.session_state.user_id = session_id
            st.session_state.data = saved_data
            st.session_state.step = 6  # Painel de insights agora é a etapa 6
            st.session_state.loaded_external = True

    # Título e introdução
    st.title("NutriSigno")
    st.write(
        "Bem-vindo ao NutriSigno! Preencha as etapas abaixo para receber um plano "
        "alimentar personalizado, combinando ciência e astrologia."
    )

    # Barra de progresso: agora com 7 etapas
    total_steps = 7
    progress = (st.session_state.step - 1) / total_steps
    st.progress(progress)

    # Etapa 1: dados pessoais
    if st.session_state.step == 1:
        st.header("1. Dados pessoais")
        with st.form("dados_pessoais"):
            nome = st.text_input("Nome completo")
            email = st.text_input("E-mail")
            telefone = st.text_input("Telefone (WhatsApp)")
            peso = st.number_input("Peso (kg)", min_value=0.0, max_value=500.0, step=0.1)
            altura = st.number_input("Altura (cm)", min_value=0.0, max_value=300.0, step=0.1)
            data_nasc = st.date_input("Data de nascimento", min_value=date(1900, 1, 1), max_value=date.today())
            hora_nasc = st.time_input("Hora de nascimento", value=time(12, 0))
            local_nasc = st.text_input("Cidade e estado de nascimento")
            submitted = st.form_submit_button("Próximo")
            if submitted:
                required_fields = [nome, email, telefone, peso, altura, data_nasc, local_nasc]
                if any(field in (None, "") for field in required_fields):
                    st.error("Por favor preencha todos os campos obrigatórios.")
                else:
                    # Podemos pré-preencher um palpite de signo (será confirmado na Etapa 2)
                    signo_guess = get_zodiac_sign(data_nasc)
                    st.session_state.data.update({
                        "nome": nome,
                        "email": email,
                        "telefone": telefone,
                        "peso": peso,
                        "altura": altura,
                        "data_nascimento": data_nasc.isoformat(),
                        "hora_nascimento": hora_nasc.isoformat(),
                        "local_nascimento": local_nasc,
                        "signo": signo_guess,  # será confirmado/ajustado no grid
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
            if st.button("Voltar ◀"):
                st.session_state.step = 1
        with cols[1]:
            if st.session_state.get("signo"):
                if st.button("Continuar ▶"):
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
            )
            consumo_agua = st.number_input("Consumo diário de água (litros)", min_value=0.0, max_value=10.0, step=0.1)
            atividade = st.selectbox(
                "Nível de atividade física",
                ["Sedentário", "Leve", "Moderado", "Intenso"],
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
                )
            submitted = st.form_submit_button("Próximo")
            if submitted:
                required = [historico, consumo_agua, atividade, tipo_fezes, cor_urina]
                if any(field in (None, "") for field in required):
                    st.error("Por favor preencha todos os campos.")
                else:
                    st.session_state.data.update({
                        "historico_saude": historico,
                        "consumo_agua": consumo_agua,
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
                "Nível de motivação para mudanças alimentares", 1, 5, 3
            )
            estresse = st.slider("Nível de estresse atual", 1, 5, 3)
            habitos = st.text_area(
                "Descreva brevemente seus hábitos alimentares", value="",
            )
            energia = st.select_slider(
                "Como você descreveria sua energia diária?",
                options=["Baixa", "Moderada", "Alta"],
                value="Moderada",
            )
            impulsividade = st.slider(
                "Quão impulsivo(a) você é em relação à alimentação?", 1, 5, 3
            )
            rotina = st.slider(
                "Quão importante é para você seguir uma rotina alimentar?", 1, 5, 3
            )
            submitted = st.form_submit_button("Próximo")
            if submitted:
                required = [motivacao, estresse, habitos]
                if any(field in (None, "") for field in required):
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    st.session_state.data.update({
                        "motivacao": motivacao,
                        "estresse": estresse,
                        "habitos_alimentares": habitos,
                        "energia_diaria": energia,
                        "impulsividade_alimentar": impulsividade,
                        "rotina_alimentar": rotina,
                    })
                    next_step()

    # Etapa 5: avaliação geral
    elif st.session_state.step == 5:
        st.header("5. Avaliação geral")
        with st.form("avaliacao_geral"):
            observacoes = st.text_area(
                "Observações adicionais",
                help="Compartilhe qualquer informação extra que julgue relevante.",
            )
            submitted = st.form_submit_button("Prosseguir para insights")
            if submitted:
                st.session_state.data.update({"observacoes": observacoes})
                next_step()

    # Etapa 6: painel de insights
    import io
    from modules import openai_utils
    try:
        from modules import dashboard_utils  # se você já tiver este módulo
    except Exception:
        dashboard_utils = None

    # --- dentro do passo "Painel de insights" ---
    elif st.session_state.step ==6:
        st.header("6. Painel de insights")

        # 1) Obter insights (com fallback hard)
        try:
            ai_pack = openai_utils.generate_insights(st.session_state.data)
            insights = ai_pack.get("insights", {})
            ai_summary = ai_pack.get("ai_summary", "Resumo indisponível (modo simulado).")
        except Exception as e:
            st.warning(f"Modo fallback automático: {e}")
            # fallback mínimo (se openai_utils tiver sido quebrado por algum motivo)
            peso = float(st.session_state.data.get("peso") or 70)
            altura = float(st.session_state.data.get("altura") or 170)
            altura_m = altura/100
            bmi = round(peso/(altura_m**2),1)
            insights = {
                "bmi": bmi,
                "bmi_category": "Eutrofia" if 18.5 <= bmi < 25 else ("Baixo peso" if bmi < 18.5 else ("Sobrepeso" if bmi < 30 else "Obesidade")),
                "recommended_water": round(max(1.5, peso*0.035),1),
                "water_status": "OK",
                "bristol": "Padrão dentro do esperado",
                "urine": "Hidratado",
                "motivacao": int(st.session_state.data.get("motivacao") or 3),
                "estresse": int(st.session_state.data.get("estresse") or 3),
                "sign_hint": "Use seu signo como inspiração, não como prescrição.",
                "consumption": {"water_liters": float(st.session_state.data.get("consumo_agua") or 1.5),
                                "recommended_liters": round(max(1.5, peso*0.035),1)}
            }
            ai_summary = "Resumo simulado (fallback hard)."

        # 2) Cards (HTML/CSS leve para visual limpo)
        card_css = """
        <style>
        .grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:8px;}
        .card {background:#fff;border:1px solid #e6e6e6;border-radius:12px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);}
        .kpi {font-size:26px;font-weight:700;margin:6px 0;}
        .sub {color:#6b7280;font-size:13px;margin-top:2px;}
        .badge-ok{display:inline-block;padding:2px 8px;border-radius:999px;background:#e8f7ef;color:#127a46;font-size:12px}
        .badge-warn{display:inline-block;padding:2px 8px;border-radius:999px;background:#fff5e6;color:#8a5200;font-size:12px}
        </style>
        """
        st.markdown(card_css, unsafe_allow_html=True)

        st.markdown('<div class="grid">', unsafe_allow_html=True)
        def badge(text, ok=True):
            cls = "badge-ok" if ok else "badge-warn"
            return f'<span class="{cls}">{text}</span>'

        st.markdown(f'''
        <div class="card">
        <div>IMC</div>
        <div class="kpi">{insights.get("bmi","--")}</div>
        <div class="sub">{insights.get("bmi_category","")}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="card">
        <div>Hidratação</div>
        <div class="kpi">{insights["consumption"]["water_liters"]} / {insights["consumption"]["recommended_liters"]} L</div>
        <div class="sub">{badge(insights.get("water_status","OK")=="OK" and "Meta atingida" or "Abaixo do ideal", ok=insights.get("water_status","OK")=="OK")}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="card">
        <div>Digestão</div>
        <div class="kpi">Bristol</div>
        <div class="sub">{insights.get("bristol","")}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="card">
        <div>Urina</div>
        <div class="kpi">Cor</div>
        <div class="sub">{insights.get("urine","")}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="card">
        <div>Comportamento</div>
        <div class="kpi">Motivação {insights.get("motivacao",0)}/5</div>
        <div class="sub">Estresse {insights.get("estresse",0)}/5</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="card">
        <div>Insight do signo</div>
        <div class="kpi">🜚</div>
        <div class="sub">{insights.get("sign_hint","")}</div>
        </div>
        ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 3) Gráficos (matplotlib) – seguros no free tier
        import matplotlib.pyplot as plt

        col1, col2 = st.columns(2)
        with col1:
            fig = plt.figure()
            plt.title("Consumo de água (L)")
            vals = [insights["consumption"]["water_liters"], insights["consumption"]["recommended_liters"]]
            plt.bar(["Consumido", "Recomendado"], vals)
            st.pyplot(fig, clear_figure=True)

        with col2:
            fig2 = plt.figure()
            plt.title("IMC")
            plt.bar(["IMC"], [insights.get("bmi", 0)])
            plt.axhline(18.5, linestyle="--"); plt.axhline(25, linestyle="--")
            st.pyplot(fig2, clear_figure=True)

        # 4) Resumo textual (da IA ou simulado)
        with st.expander("Resumo dos insights"):
            st.write(ai_summary)

        # 5) Exportações (PDF/Imagem) – usando seus utilitários se existirem, com fallback
        from modules import pdf_generator
        btn1, btn2, btn3 = st.columns(3)

        # PDF (insights) – fallback: gerar PDF simples com reportlab direto
        def build_insights_pdf_bytes(ins):
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import cm
                buf = io.BytesIO()
                c = canvas.Canvas(buf, pagesize=A4)
                y = 28*cm
                c.setFont("Helvetica-Bold", 14); c.drawString(2*cm, y, "NutriSigno — Painel de Insights"); y -= 1*cm
                c.setFont("Helvetica", 10)
                for k,v in [
                ("IMC", f"{ins['bmi']} ({ins['bmi_category']})"),
                ("Hidratação", f"{ins['consumption']['water_liters']} / {ins['consumption']['recommended_liters']} L"),
                ("Bristol", ins["bristol"]),
                ("Urina", ins["urine"]),
                ("Motivação/Estresse", f"{ins['motivacao']}/5 · {ins['estresse']}/5"),
                ("Insight do signo", ins["sign_hint"]),
                ]:
                    c.drawString(2*cm, y, f"{k}: {v}"); y -= 0.8*cm
                    if y < 2*cm: c.showPage(); y = 28*cm
                c.save()
                buf.seek(0)
                return buf.getvalue()
            except Exception:
                return b"%PDF-1.4\n% fallback vazio"

        with btn1:
            pdf_bytes = build_insights_pdf_bytes(insights)
            st.download_button("Exportar PDF", data=pdf_bytes, file_name="insights.pdf", mime="application/pdf")

        # Imagem compartilhável (post)
        def build_share_png_bytes(ins):
            import matplotlib.pyplot as plt
            import numpy as np
            fig = plt.figure(figsize=(6,6), dpi=200)
            plt.title("NutriSigno — Resumo", pad=12)
            text = (
                f"IMC: {ins['bmi']} ({ins['bmi_category']})\n"
                f"Hidratação: {ins['consumption']['water_liters']} / {ins['consumption']['recommended_liters']} L\n"
                f"Bristol: {ins['bristol']}\nUrina: {ins['urine']}\n"
                f"Motivação/Estresse: {ins['motivacao']}/5 · {ins['estresse']}/5\n"
                f"Signo: {ins.get('sign_hint','')}\n"
                f"#NutriSigno"
            )
            plt.axis("off")
            plt.text(0.02, 0.98, text, va="top", ha="left", wrap=True)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            plt.close(fig)
            return buf.getvalue()

        with btn2:
            img_bytes = build_share_png_bytes(insights)
            st.download_button("Baixar imagem", data=img_bytes, file_name="insights.png", mime="image/png")

        with btn3:
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
                try:
                    # Salva dados no Firebase
                    firebase_utils.save_user_data(st.session_state.user_id, st.session_state.data)
                except Exception as e:
                    st.error(f"Erro ao salvar dados no Firebase: {e}")
                try:
                    plan_dict = openai_utils.generate_plan(st.session_state.data)
                    st.session_state.plan = plan_dict
                except Exception as e:
                    st.error(f"Erro ao gerar plano com a OpenAI: {e}")
                    return
                # Gera PDF
                pdf_path = f"/tmp/{st.session_state.user_id}.pdf"
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
                # Envia e-mail
                try:
                    subject = "Seu Plano Alimentar NutriSigno"
                    body = (
                        "Olá {nome},\n\n"
                        "Em anexo está o seu plano alimentar personalizado gerado pelo NutriSigno. "
                        "Siga as orientações com responsabilidade e, se possível, consulte um profissional "
                        "da saúde antes de iniciar qualquer mudança significativa.\n\n"
                        "Você poderá acessar novamente o painel de insights por meio do link abaixo:\n"
                        f"{st.request.url.split('?')[0]}?id={st.session_state.user_id}\n\n"
                        "Atenciosamente,\nEquipe NutriSigno"
                    ).format(nome=st.session_state.data.get('nome'))
                    attachments = [(f"nutrisigno_plano_{st.session_state.user_id}.pdf", pdf_bytes)]
                    email_utils.send_email(
                        recipient=st.session_state.data.get('email'),
                        subject=subject,
                        body=body,
                        attachments=attachments,
                    )
                except Exception as e:
                    st.error(f"Erro ao enviar e-mail: {e}")
                    return
                # Após o envio do e-mail, disponibiliza o PDF para download imediato
                st.success("Plano gerado e enviado por e-mail!")
                st.download_button(
                    label="Baixar plano em PDF",
                    data=pdf_bytes,
                    file_name=f"nutrisigno_plano_{st.session_state.user_id}.pdf",
                    mime="application/pdf",
                )
                st.markdown(
                    f"Você pode revisitar seus insights quando quiser através deste link: "
                    f"[Painel de Insights](/?id={st.session_state.user_id})"
                )


if __name__ == "__main__":
    main()

