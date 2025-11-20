"""Aplicação principal do NutriSigno."""

from __future__ import annotations

import logging
from textwrap import dedent

import streamlit as st

from modules.app_bootstrap import init_models_and_migrate

log = logging.getLogger(__name__)


def _run_bootstrap() -> tuple[bool, str]:
    """Executa o bootstrap (migrations + init) e cacheia o resultado na sessão."""
    try:
        init_models_and_migrate()
        ok, msg = True, "Bootstrap executado com sucesso."
    except Exception as exc:  # noqa: BLE001
        log.exception("Falha ao executar bootstrap do NutriSigno.")
        ok, msg = False, f"Erro ao iniciar a aplicação. Detalhes nos logs. ({exc})"

    st.session_state["_bootstrap_ok"] = ok
    st.session_state["_bootstrap_msg"] = msg
    return ok, msg


def _apply_global_styles() -> None:
    """Define estilos customizados para a landing page."""
    st.markdown(
        dedent(
            """
            <style>
                :root {
                    --indigo: #4a3fbb;
                    --indigo-soft: #f3f0ff;
                    --gold: #c49a4a;
                    --text: #1f1f2c;
                    --muted: #4b4b63;
                }
                .main {
                    background: radial-gradient(circle at 20% 20%, #f8f6ff, #ffffff 35%),
                        radial-gradient(circle at 80% 0%, #f2f7ff, #ffffff 25%),
                        #ffffff;
                }
                .hero {
                    background: linear-gradient(135deg, #f7f2ff, #f9fbff);
                    border: 1px solid #ede9ff;
                    border-radius: 24px;
                    padding: 3rem 2.5rem;
                    position: relative;
                    overflow: hidden;
                }
                .hero::after {
                    content: "";
                    position: absolute;
                    inset: 10% -20% auto auto;
                    width: 320px;
                    height: 320px;
                    background: radial-gradient(circle, rgba(74, 63, 187, 0.1), transparent 60%);
                    filter: blur(6px);
                    transform: rotate(12deg);
                }
                .hero h1 {
                    font-size: clamp(2rem, 4vw, 2.8rem);
                    margin-bottom: 0.6rem;
                    color: var(--text);
                }
                .hero .subtitle {
                    font-size: 1.1rem;
                    color: var(--muted);
                    margin-bottom: 1.4rem;
                }
                .pill {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.35rem;
                    background: #ffffffaa;
                    border: 1px solid #ebe9ff;
                    color: var(--indigo);
                    padding: 0.35rem 0.9rem;
                    border-radius: 999px;
                    font-weight: 600;
                    font-size: 0.95rem;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.04);
                }
                .cta-primary button {
                    background: linear-gradient(120deg, var(--indigo), #5b4ce5);
                    color: #fff;
                    border: none;
                    padding: 0.9rem 1.35rem;
                    font-size: 1rem;
                    border-radius: 12px;
                    box-shadow: 0 20px 45px rgba(74, 63, 187, 0.3);
                }
                .cta-secondary {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.4rem;
                    color: var(--indigo);
                    padding: 0.75rem 1rem;
                    border-radius: 12px;
                    text-decoration: none;
                    font-weight: 600;
                    border: 1px dashed #d8d3f7;
                    background: #f9f7ff;
                }
                .placeholder-card {
                    background: radial-gradient(circle at 20% 20%, #f4ecff, #f8f8ff 55%);
                    border: 1px dashed #d6d0f8;
                    color: var(--muted);
                    border-radius: 18px;
                    padding: 1.25rem;
                    text-align: center;
                    min-height: 320px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    overflow: hidden;
                }
                .placeholder-card::after {
                    content: "✦";
                    position: absolute;
                    font-size: 4rem;
                    color: rgba(74, 63, 187, 0.08);
                    right: 18%;
                    top: 12%;
                }
                .section-title {
                    font-size: 1.7rem;
                    color: var(--text);
                    margin-bottom: 0.4rem;
                }
                .section-subtitle {
                    color: var(--muted);
                    margin-bottom: 1.4rem;
                }
                .mini-label {
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    font-weight: 700;
                    font-size: 0.72rem;
                    color: var(--indigo);
                    margin-bottom: 0.2rem;
                }
                .benefit-card {
                    border: 1px solid #eee9ff;
                    border-radius: 16px;
                    padding: 1.1rem 1.2rem;
                    background: #ffffff;
                    box-shadow: 0 18px 35px rgba(0,0,0,0.03);
                    height: 100%;
                }
                .benefit-card h4 {
                    margin-top: 0.6rem;
                    margin-bottom: 0.35rem;
                    color: var(--text);
                }
                .benefit-card p {
                    color: var(--muted);
                    font-size: 0.95rem;
                }
                .floating-card {
                    border-radius: 18px;
                    padding: 1.4rem;
                    border: 1px solid #efe8ff;
                    background: linear-gradient(180deg, #ffffff, #f7f5ff);
                    box-shadow: 0 18px 35px rgba(0,0,0,0.05);
                }
                .faq-item {
                    border: 1px solid #eae8fa;
                    border-radius: 14px;
                    padding: 1rem 1.2rem;
                    background: #ffffff;
                }
                footer {
                    color: var(--muted);
                    font-size: 0.9rem;
                }
                @media (max-width: 768px) {
                    .hero {
                        padding: 2.25rem 1.4rem;
                    }
                    .placeholder-card {
                        min-height: 220px;
                    }
                }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def _hero_section(ok: bool, msg: str) -> None:
    """Renderiza a seção de hero com CTAs principais."""
    with st.container():
        st.markdown("<div class='hero'>", unsafe_allow_html=True)
        cols = st.columns([1.05, 0.95])
        with cols[0]:
            st.markdown("<span class='pill'>NutriSigno • Página Início</span>", unsafe_allow_html=True)
            st.markdown("# Plano NutriSigno — título principal placeholder")
            st.markdown(
                "<p class='subtitle'>Subtítulo com benefício principal em placeholder, destacando personalização e credibilidade.</p>",
                unsafe_allow_html=True,
            )
            st.markdown("Plano a partir de R$XXX — detalhe discreto", help="Informação ilustrativa.")

            cta_col1, cta_col2 = st.columns([1.2, 1])
            with cta_col1:
                st.markdown("<div class='cta-primary'>", unsafe_allow_html=True)
                if st.button("Iniciar minha avaliação NutriSigno", use_container_width=True):
                    st.switch_page("pages/01_Formulario.py")
                st.markdown("</div>", unsafe_allow_html=True)
            with cta_col2:
                st.markdown(
                    "<a class='cta-secondary' href='#mockup'>Ver exemplo de plano →</a>",
                    unsafe_allow_html=True,
                )

            st.caption(
                "Chamada leve sobre compromisso com dados e astrologia, em placeholder para futura copy.")
            if not ok:
                st.error(
                    "Falha ao executar o bootstrap da aplicação. "
                    "Verifique os logs para mais detalhes.")
            elif msg:
                st.caption(msg)

        with cols[1]:
            st.markdown(
                "<div class='placeholder-card'>Imagem hero / mockup ilustrativo aqui</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


def _how_it_works_section() -> None:
    st.markdown("## Como funciona • explicação em três passos")
    st.markdown(
        "Texto breve placeholder explicando Nutrição + IA + astrologia com linguagem leve e confiável."
    )
    cols = st.columns(3)
    passos = [
        ("Preencha sua avaliação", "Descrição placeholder sobre responder perguntas importantes."),
        ("IA + nutrição + astrologia", "Explica processamento dos dados com rigor científico."),
        ("Receba seu plano", "Entrega de plano alimentar e insights personalizados."),
    ]
    for col, (titulo, desc) in zip(cols, passos):
        with col:
            st.markdown("### ✧ " + titulo)
            st.write(desc)


def _audience_section() -> None:
    st.markdown("## Para quem é e por que funciona")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Para quem é")
        st.markdown(
            """
            - Bullet placeholder sobre ansiedade com comida e recomeços.
            - Bullet placeholder para quem gosta de astrologia, mas quer base real.
            - Bullet placeholder para rotina corrida e busca de disciplina.
            - Bullet opcional para quem quer acompanhamento leve.
            """
        )
    with col2:
        st.markdown("#### Por que funciona")
        st.markdown(
            """
            - Personalização com dados e mapa de comportamento (placeholder).
            - Base validada por nutricionista e referências confiáveis.
            - Olhar para rotina, emoções e preferências (texto placeholder).
            - Entregas práticas e realistas, prontas para usar.
            """
        )


def _benefits_section() -> None:
    st.markdown("## Benefícios principais")
    st.markdown("Cards de benefícios com ícones sutis de astrologia, texto placeholder.")
    cols = st.columns(3)
    beneficios = [
        ("Digestão e bem-estar", "Descrição breve placeholder sobre digestão equilibrada."),
        ("Relação emocional", "Texto curto sobre apoiar emoções ligadas à comida."),
        ("Rotina organizada", "Placeholder sobre praticidade no dia a dia."),
        ("Autoconhecimento", "Benefício sobre signos e autoconsciência."),
        ("Energia e foco", "Texto placeholder sobre performance equilibrada."),
        ("Suporte contínuo", "Linha breve sobre ajustes e acompanhamento."),
    ]
    for idx, beneficio in enumerate(beneficios):
        col = cols[idx % 3]
        with col:
            st.markdown(
                "<div class='benefit-card'>" \
                f"<div class='mini-label'>✷ Benefício</div>" \
                f"<h4>{beneficio[0]}</h4>" \
                f"<p>{beneficio[1]}</p>" \
                "</div>",
                unsafe_allow_html=True,
            )


def _authority_section() -> None:
    st.markdown("## Quem está por trás")
    st.markdown(
        "Bloco placeholder sobre nutricionista responsável, CRN e validação científica."
    )
    col1, col2 = st.columns([0.9, 1.1])
    with col1:
        st.markdown("### Nome da profissional — CRN")
        st.write(
            "Mini bio placeholder destacando experiência clínica, base científica (ex.: TACO) "
            "e olhar integrado com astrologia.")
        st.markdown(
            "- Item placeholder: plano validado por nutricionista.\n"
            "- Item placeholder: metodologia combinando dados e signos.\n"
            "- Item placeholder: foco em recomendações realistas."
        )
    with col2:
        st.markdown(
            "<div class='floating-card'>Foto/ilustração da profissional (placeholder visual suave)</div>",
            unsafe_allow_html=True,
        )


def _mockup_section() -> None:
    st.markdown("<a id='mockup'></a>", unsafe_allow_html=True)
    st.markdown("## Exemplo de plano NutriSigno")
    st.markdown("Texto placeholder explicando o que o usuário recebe no plano e como utilizar.")
    col1, col2 = st.columns([1.05, 0.95])
    with col1:
        st.markdown(
            "<div class='placeholder-card'>Mockup do relatório/plano (imagem ou ilustração)</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div class='floating-card'>\n"
            "<div class='mini-label'>Plano personalizado</div>\n"
            "<h4>Card lateral com destaques</h4>\n"
            "<p>Placeholders para bullets que explicam módulos do plano, orientações e ajustes semanais.</p>\n"
            "</div>",
            unsafe_allow_html=True,
        )


def _testimonials_section() -> None:
    st.markdown("## Depoimentos")
    st.markdown("Prova social em placeholders, com 2–3 relatos breves.")
    cols = st.columns(3)
    depoimentos = [
        ("Nome 1", "Frase curta placeholder sobre resultado percebido."),
        ("Nome 2", "Comentário breve sobre rotina e autoconhecimento."),
        ("Nome 3", "Depoimento placeholder destacando confiança no método."),
    ]
    for col, (nome, frase) in zip(cols, depoimentos):
        with col:
            st.markdown(
                "<div class='benefit-card'>" \
                f"<div class='mini-label'>Depoimento</div>" \
                f"<h4>{nome}</h4>" \
                f"<p>{frase}</p>" \
                "</div>",
                unsafe_allow_html=True,
            )


def _faq_section() -> None:
    st.markdown("## Perguntas frequentes")
    st.markdown("Respostas em placeholders, prontas para serem editadas.")
    faq_items = [
        ("Como funciona o plano?", "Resposta placeholder explicando o fluxo da avaliação ao plano."),
        (
            "É realmente baseado em nutrição ou só astrologia?",
            "Resposta placeholder reforçando base nutricional e integração com astrologia.",
        ),
        ("Preciso informar horário de nascimento?", "Resposta placeholder sobre dados necessários."),
        ("É consulta médica?", "Resposta placeholder esclarecendo que não substitui acompanhamento."),
        ("Como recebo meu plano?", "Resposta placeholder sobre entrega digital e próximos passos."),
    ]
    for pergunta, resposta in faq_items:
        with st.expander(pergunta, expanded=False):
            st.write(resposta)


def _final_cta_section() -> None:
    st.markdown("## Pronta(o) para começar?")
    st.markdown(
        "Frase curta em placeholder reforçando benefício e convite para iniciar a avaliação."
    )
    st.markdown("<div class='cta-primary'>", unsafe_allow_html=True)
    if st.button("Iniciar minha avaliação NutriSigno", use_container_width=True, key="cta_final"):
        st.switch_page("pages/01_Formulario.py")
    st.markdown("</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown(
        """
        <footer>
        Plano com foco em bem-estar; não substitui acompanhamento médico ou nutricional presencial.<br>
        Links de política de privacidade e termos (placeholders).<br>
        Respeito à LGPD e cuidado com dados pessoais (placeholder de mensagem).
        </footer>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Configurações globais e conteúdo de alto nível da aplicação."""
    st.set_page_config(page_title="Início | NutriSigno", page_icon="✨", layout="wide")

    ok = st.session_state.get("_bootstrap_ok")
    msg = st.session_state.get("_bootstrap_msg")

    if ok is None:
        ok, msg = _run_bootstrap()

    msg = msg or ""

    _apply_global_styles()
    _hero_section(ok, msg)
    st.divider()
    _how_it_works_section()
    st.divider()
    _audience_section()
    st.divider()
    _benefits_section()
    st.divider()
    _authority_section()
    st.divider()
    _mockup_section()
    st.divider()
    _testimonials_section()
    st.divider()
    _faq_section()
    st.divider()
    _final_cta_section()


if __name__ == "__main__":
    main()
