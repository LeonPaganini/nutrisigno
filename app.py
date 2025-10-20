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
    elif st.session_state.step == 6:
        """Painel de insights."""
        st.header("6. Painel de insights")
        # Computar insights e gráficos
        insights = dashboard_utils.compute_insights(st.session_state.data)
        charts = dashboard_utils.generate_dashboard_charts(insights)
        # Gerar insight comportamental via IA
        ai_insight = openai_utils.generate_insights(st.session_state.data)
        # Exibir métricas
        st.subheader("Resumo dos indicadores")

        def make_card(title: str, value: str, description: str = "") -> str:
            return f"""
                <div style=\"background-color: #F7F7F7; padding: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);\">
                    <h4 style=\"margin: 0; color: #333;\">{title}</h4>
                    <p style=\"margin: 4px 0 0; font-size: 24px; font-weight: bold; color: #007BFF;\">{value}</p>
                    <p style=\"margin: 2px 0 0; font-size: 12px; color: #555;\">{description}</p>
                </div>
            """

        cards: list[str] = []
        if insights.get("bmi"):
            cards.append(make_card(
                "IMC",
                f"{insights['bmi']:.1f}",
                insights.get("bmi_category", ""),
            ))
        cards.append(make_card(
            "Hidratação",
            f"{insights['recommended_water']:.1f} L",
            insights.get("water_status", ""),
        ))
        cards.append(make_card(
            "Escala de Bristol",
            "",
            insights.get("bristol", ""),
        ))
        cards.append(make_card(
            "Cor da urina",
            "",
            insights.get("urine", ""),
        ))
        if insights.get("mental_notes"):
            cards.append(make_card(
                "Nota psicológica",
                "",
                insights.get("mental_notes", ""),
            ))
        if insights.get("sign_hint"):
            cards.append(make_card(
                "Dica do signo",
                "",
                insights.get("sign_hint", ""),
            ))
        if ai_insight:
            cards.append(make_card(
                "Insight personalizado",
                "",
                ai_insight,
            ))
        # Display cards in rows of two
        for i in range(0, len(cards), 2):
            row = st.columns(2)
            with row[0]:
                st.markdown(cards[i], unsafe_allow_html=True)
            if i + 1 < len(cards):
                with row[1]:
                    st.markdown(cards[i + 1], unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("Gráficos")
        for name, fig in charts.items():
            st.pyplot(fig)
        st.markdown("### Exportar")
        # Botão para exportar PDF
        if st.button("Exportar insights em PDF"):
            pdf_out = f"/tmp/dashboard_{st.session_state.user_id}.pdf"
            try:
                dashboard_utils.create_dashboard_pdf(st.session_state.data, insights, charts, pdf_out)
                with open(pdf_out, 'rb') as f:
                    st.download_button(
                        label="Baixar PDF",
                        data=f.read(),
                        file_name=f"nutrisigno_insights_{st.session_state.user_id}.pdf",
                        mime="application/pdf",
                    )
            except Exception as e:
                st.error(f"Erro ao gerar PDF de insights: {e}")
        # Botão para exportar imagem
        if st.button("Baixar imagem para Instagram"):
            img_out = f"/tmp/insights_{st.session_state.user_id}.png"
            try:
                dashboard_utils.create_share_image(insights, charts, img_out)
                with open(img_out, 'rb') as f:
                    st.download_button(
                        label="Baixar imagem",
                        data=f.read(),
                        file_name=f"nutrisigno_insights_{st.session_state.user_id}.png",
                        mime="image/png",
                    )
            except Exception as e:
                st.error(f"Erro ao gerar imagem: {e}")
        st.markdown("---")
        if st.button("Gerar plano nutricional e prosseguir para pagamento"):
            next_step()

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