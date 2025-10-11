"""Aplicação principal do NutriSigno.

Esta aplicação Streamlit coleta dados do usuário em quatro etapas,
interage com a API da OpenAI para criar um plano alimentar
personalizado, salva os dados no Firebase e envia um relatório em PDF
por e‑mail após a confirmação do pagamento.
"""

from __future__ import annotations
import os
from PIL import Image
import json
import uuid
from datetime import date, time
from typing import Dict, Any

import streamlit as st

from modules import firebase_utils, openai_utils, pdf_generator, email_utils
import io

# Caminho das imagens enviadas
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

def initialize_session():
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

def next_step():
    st.session_state.step += 1

def main():
    st.set_page_config(page_title="NutriSigno", layout="wide")
    initialize_session()
    st.title("NutriSigno")
    st.write(
        "Bem‑vindo ao NutriSigno! Preencha as etapas abaixo para receber um plano "
        "alimentar personalizado, combinando ciência e astrologia."
    )

    # Barra de progresso
    total_steps = 4
    progress = (st.session_state.step - 1) / total_steps
    st.progress(progress)

    if st.session_state.step == 1:
        st.header("1. Dados pessoais")
        with st.form("dados_pessoais"):
            nome = st.text_input("Nome completo")
            email = st.text_input("E‑mail")
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
                    # Armazena dados
                    signo = get_zodiac_sign(data_nasc)
                    st.session_state.data.update({
                        "nome": nome,
                        "email": email,
                        "telefone": telefone,
                        "peso": peso,
                        "altura": altura,
                        "data_nascimento": data_nasc.isoformat(),
                        "hora_nascimento": hora_nasc.isoformat(),
                        "local_nascimento": local_nasc,
                        "signo": signo,
                    })
                    next_step()

    elif st.session_state.step == 2:
        st.header("2. Avaliação nutricional")
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
                st.image(Image.open(PATH_BRISTOL), caption='Escala de Bristol', use_column_width=True)
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
                    key="tipo_fezes"
                )

            st.markdown("---")
            st.subheader("Cor da Urina")
            col_urina1, col_urina2 = st.columns([1, 2])
            with col_urina1:
                st.image(Image.open(PATH_URINA), caption='Classificação da Urina', use_column_width=True)
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
                    key="cor_urina"
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

    elif st.session_state.step == 3:
        st.header("3. Avaliação psicológica")
        with st.form("avaliacao_psicologica"):
            motivacao = st.slider(
                "Nível de motivação para mudanças alimentares", 1, 5, 3
            )
            estresse = st.slider("Nível de estresse atual", 1, 5, 3)
            habitos = st.text_area(
                "Descreva brevemente seus hábitos alimentares", value="",
            )
            submitted = st.form_submit_button("Próximo")
            if submitted:
                required = [motivacao, estresse, habitos]
                if any(field in (None, "") for field in required):
                    st.error("Preencha todos os campos.")
                else:
                    st.session_state.data.update({
                        "motivacao": motivacao,
                        "estresse": estresse,
                        "habitos_alimentares": habitos,
                    })
                    next_step()

    elif st.session_state.step == 4:
        st.header("4. Avaliação geral")
        with st.form("avaliacao_geral"):
            observacoes = st.text_area(
                "Observações adicionais",
                help="Compartilhe qualquer informação extra que julgue relevante.",
            )
            submitted = st.form_submit_button("Prosseguir para pagamento")
            if submitted:
                st.session_state.data.update({"observacoes": observacoes})
                next_step()

    elif st.session_state.step == 5:
        st.header("Pagamento e geração do plano")
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
                        st.session_state.data, st.session_state.plan, pdf_path
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
                st.success("Plano gerado e enviado com sucesso! Confira seu e-mail.")
        # Caso já exista plano, exibe resumo
        if st.session_state.plan:
            st.subheader("Resumo do Plano")
            plan_json = json.dumps(st.session_state.plan, ensure_ascii=False, indent=2)
            st.json(plan_json)
            with open(pdf_path, 'rb') as f:
                st.download_button(
                    label="Baixar relatório em PDF",
                    data=f.read(),
                    file_name=f"nutrisigno_plano_{st.session_state.user_id}.pdf",
                    mime="application/pdf",
                )

if __name__ == "__main__":
    main()
