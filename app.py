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
                    --rosy: #f9f4f1;
                    --cream: #fff9f5;
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
                    box-shadow: 0 30px 70px rgba(74, 63, 187, 0.08);
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
                .hero .badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.4rem;
                    padding: 0.35rem 0.9rem;
                    border-radius: 999px;
                    background: #fff9f5;
                    border: 1px solid #f1e7d9;
                    color: #a26b20;
                    font-weight: 700;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.04);
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
                .cta-secondary:hover {
                    background: #f1edff;
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
                .eyebrow {
                    letter-spacing: 0.08em;
                    font-weight: 800;
                    font-size: 0.75rem;
                    color: var(--indigo);
                    text-transform: uppercase;
                    margin-bottom: 0.4rem;
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
                .muted-box {
                    border-radius: 16px;
                    padding: 1.2rem 1.4rem;
                    background: linear-gradient(160deg, #fff9f5, #f4f0ff);
                    border: 1px solid #efe3d8;
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
                    .cta-secondary {
                        width: 100%;
                        justify-content: center;
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
            st.markdown("<span class='badge'>Oferta de lançamento: de R$49,90 por R$27,90</span>", unsafe_allow_html=True)
            st.markdown("# NutriSigno: nutrição guiada pelo seu céu e pelo seu corpo")
            st.markdown(
                "<p class='subtitle'>Unimos ciência nutricional e astrologia comportamental para desenhar um plano alimentar sob medida para o seu ritmo natural.</p>",
                unsafe_allow_html=True,
            )
            st.markdown("<p class='eyebrow'>de R$49,90 por R$27,90 • oferta de lançamento</p>", unsafe_allow_html=True)

            cta_col1, cta_col2 = st.columns([1.2, 1])
            with cta_col1:
                st.markdown("<div class='cta-primary'>", unsafe_allow_html=True)
                if st.button("Iniciar minha avaliação NutriSigno", use_container_width=True):
                    st.switch_page("pages/01_Formulario.py")
                st.markdown("</div>", unsafe_allow_html=True)
            with cta_col2:
                st.markdown(
                    "<a class='cta-secondary' href='#como-funciona'>Ver como funciona →</a>",
                    unsafe_allow_html=True,
                )

            st.caption(
                "Método criado por nutricionista clínica, com referências na base TACO e diretrizes oficiais de nutrição."
            )
            if not ok:
                st.error(
                    "Falha ao executar o bootstrap da aplicação. "
                    "Verifique os logs para mais detalhes.")
            elif msg:
                st.caption(msg)

        with cols[1]:
            st.markdown(
                "<div class='placeholder-card' style=\"background-image:url('/mnt/data/gladia_template.html');background-size:cover;\">Mockup hero com plano e constelação suave</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


def _how_it_works_section() -> None:
    st.markdown("<a id='como-funciona'></a>", unsafe_allow_html=True)
    st.markdown("## Como funciona")
    st.markdown(
        "Linha clara em três passos para mostrar o fluxo NutriSigno, unindo avaliação, modelo nutricional e entrega automática do seu plano."
    )
    cols = st.columns(3)
    passos = [
        ("Avaliação completa", "Responda ao diagnóstico NutriSigno com dados de saúde, rotina e mapa natal."),
        (
            "Modelo nutricional + análise astrológica",
            "Cruzamos necessidades metabólicas com padrões astrológicos que influenciam seus impulsos e horários de maior disposição.",
        ),
        (
            "Receba seu plano + relatório",
            "Você recebe automaticamente o plano alimentar e um relatório em PDF com insights aplicáveis para o dia a dia.",
        ),
    ]
    for idx, (titulo, desc) in enumerate(passos, start=1):
        with cols[idx - 1]:
            st.markdown(f"### ✧ Passo {idx} — {titulo}")
            st.write(desc)


def _deliverables_section() -> None:
    st.markdown("## O que chega no seu e-mail")
    st.markdown(
        "Grade concisa com tudo que será enviado: plano alimentar, insights astrológicos de comportamento e relatório digital completo."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='mini-label'>Plano alimentar personalizado</div>", unsafe_allow_html=True)
        st.markdown(
            "Cardápios e trocas inteligentes alinhados ao seu metabolismo e preferências."
        )
        st.markdown("<div class='mini-label'>Insights astrológicos de comportamento</div>", unsafe_allow_html=True)
        st.markdown(
            "Pontos do seu mapa que impactam apetite, impulsividade e horários ideais para refeições."
        )
        st.markdown("<div class='mini-label'>Relatório digital em PDF</div>", unsafe_allow_html=True)
        st.markdown(
            "Documento elegante, com linguagem clara e referências usadas na construção do plano."
        )
    with col2:
        st.markdown("<div class='mini-label'>Feedback automático</div>", unsafe_allow_html=True)
        st.markdown(
            "Comentários objetivos sobre como ajustar porções, horários e hidratação ao longo da semana."
        )
        st.markdown("<div class='mini-label'>Recomendações práticas</div>", unsafe_allow_html=True)
        st.markdown(
            "Rotinas simples, hidratação guiada e preparações rápidas para manter consistência."
        )
        st.markdown(
            "<div class='muted-box'>Oferta de lançamento: de R$49,90 por R$27,90 — recebe tudo direto no seu e-mail</div>",
            unsafe_allow_html=True,
        )


def _benefits_section() -> None:
    st.markdown("## Benefícios percebidos")
    st.markdown("Cards simétricos com linguagem escaneável para mostrar ganhos concretos do método.")
    cols = st.columns(3)
    beneficios = [
        ("Equilíbrio emocional na alimentação", "Menos impulsos e mais estabilidade ao entender seus gatilhos astrológicos."),
        (
            "Hidratação e digestão alinhadas ao seu perfil",
            "Orientações de horários e combinações que respeitam seu metabolismo.",
        ),
        ("Clareza e estrutura diária", "Rotina de refeições organizada sem protocolos extremos."),
        ("Redução de impulsos alimentares", "Recomendações práticas para janelas críticas do dia e da noite."),
        ("Entendimento do próprio ritmo", "Uso do mapa natal para ajustar energia, sono e apetite."),
        ("Maior consciência alimentar", "Relatório explica o porquê de cada escolha em linguagem clara."),
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


def _why_it_works_section() -> None:
    st.markdown("## Por que o NutriSigno funciona")
    st.markdown(
        "Coluna dupla unindo ciência e astrologia comportamental, reforçando personalização profunda e linguagem acessível."
    )
    col1, col2 = st.columns([1.1, 0.9])
    with col1:
        st.markdown("<div class='mini-label'>Nutrição baseada em evidências</div>", unsafe_allow_html=True)
        st.markdown(
            "Planos construídos com base em diretrizes oficiais e base TACO, sem modismos."
        )
        st.markdown("<div class='mini-label'>Astrologia como ferramenta comportamental</div>", unsafe_allow_html=True)
        st.markdown(
            "Usamos o mapa natal para entender padrões de apetite, impulsividade e disciplina."
        )
        st.markdown("<div class='mini-label'>Personalização profunda</div>", unsafe_allow_html=True)
        st.markdown(
            "Integramos dados clínicos, preferências e rotina para ajustar porções, horários e combinações."
        )
        st.markdown("<div class='mini-label'>Linguagem técnica + acessível</div>", unsafe_allow_html=True)
        st.markdown("Você entende o porquê de cada escolha, em linguagem clara, sem perder o rigor.")
        st.markdown("<div class='mini-label'>Ciência + autoconhecimento</div>", unsafe_allow_html=True)
        st.markdown(
            "Nutrição aplicada ao seu momento de vida, com insights que estimulam consciência alimentar."
        )
    with col2:
        st.markdown(
            "<div class='placeholder-card' style=\"background-image:url('/mnt/data/gladia_template.html');background-size:cover;\">Mockup de insights astrológicos com estrelas e constelação suave</div>",
            unsafe_allow_html=True,
        )


def _founder_section() -> None:
    st.markdown("## Quem assina o método")
    st.markdown(
        "Apresentação profissional com transparência sobre referências, ética e integração entre nutrição e astrologia aplicada a hábitos."
    )
    col1, col2 = st.columns([0.9, 1.1])
    with col1:
        st.markdown("### Nutricionista clínica • CRN ativo")
        st.write(
            "Assinado por nutricionista clínica, especialista em comportamento alimentar, integrando protocolos validados e leitura astrológica orientada a hábitos."
        )
        st.markdown(
            "- Orientações alinhadas ao CFN; não substitui acompanhamento individual quando necessário.\n"
            "- Referências na base TACO, guias alimentares oficiais e literatura de comportamento alimentar.\n"
            "- Transparência nas fontes citadas no relatório e recomendações realistas."
        )
    with col2:
        st.markdown(
            "<div class='floating-card'>Foto/ilustração da profissional com halo suave e fundo claro</div>",
            unsafe_allow_html=True,
        )


def _mockup_section() -> None:
    st.markdown("<a id='mockup'></a>", unsafe_allow_html=True)
    st.markdown("## O que você recebe — exemplo do relatório")
    st.markdown(
        "Mockup realista do relatório nutricional com tom claro (16:9), reforçando a oferta promocional e o conteúdo entregue."
    )
    col1, col2 = st.columns([1.05, 0.95])
    with col1:
        st.markdown(
            "<div class='placeholder-card' style=\"background-image:url('/mnt/data/gladia_template.html');background-size:cover;\">Mockup 1 — Relatório nutricional</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p class='eyebrow'>Oferta de lançamento: de R$49,90 por R$27,90</p>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div class='floating-card'>\n"
            "<div class='mini-label'>Relatório digital em PDF</div>\n"
            "<h4>O que o relatório traz</h4>\n"
            "<p>Plano alimentar detalhado, gráficos suaves de progresso, insights astrológicos sobre apetite e disciplina, além de referências utilizadas (base TACO e diretrizes oficiais).</p>\n"
            "<ul>\n"
            "<li>Estrutura clara por horários e trocas inteligentes.</li>\n"
            "<li>Insights comportamentais para janelas de maior impulso.</li>\n"
            "<li>Dicas rápidas de hidratação e combinações fáceis.</li>\n"
            "</ul>\n"
            "</div>",
            unsafe_allow_html=True,
        )


def _plan_mockup_section() -> None:
    st.markdown("## Plano alimentar em ação")
    st.markdown(
        "Mockup em tom claro, minimalista, abaixo dos benefícios, mostrando a tela do plano alimentar alinhado às constelações discretas."
    )
    col1, col2 = st.columns([0.95, 1.05])
    with col1:
        st.markdown(
            "<div class='floating-card'>\n"
            "<div class='mini-label'>Plano alimentar</div>\n"
            "<h4>Organização diária</h4>\n"
            "<p>Cardápio com trocas rápidas, barras de progresso para macros e notas de horário alinhadas ao seu mapa.</p>\n"
            "<p>Rotina de hidratação guiada e preparações rápidas para manter consistência.</p>\n"
            "</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div class='placeholder-card' style=\"background-image:url('/mnt/data/gladia_template.html');background-size:cover;\">Mockup 2 — Plano alimentar</div>",
            unsafe_allow_html=True,
        )


def _testimonials_section() -> None:
    st.markdown("## O que elas sentiram na prática")
    st.markdown("Depoimentos reais para reforçar clareza, elegância e praticidade do método.")
    cols = st.columns(3)
    depoimentos = [
        (
            "Marina, 32",
            "Comecei a entender meus horários de maior foco e parei de pular refeições. O plano é prático e nada radical.",
        ),
        (
            "Bianca, 28",
            "Os insights do meu mapa explicaram minhas compulsões noturnas. Ajustei jantares e sono e já me sinto mais estável.",
        ),
        (
            "Fernanda, 41",
            "Gostei da linguagem clara e da proposta elegante. Sinto que o plano respeita meu ritmo e minhas escolhas.",
        ),
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
    st.markdown("Lista em acordeão com respostas diretas para dúvidas mais comuns.")
    faq_items = [
        (
            "NutriSigno substitui acompanhamento nutricional?",
            "Não. É um guia personalizado com base em evidências, mas não substitui consultas individuais quando necessárias.",
        ),
        (
            "Preciso saber meu horário de nascimento?",
            "Sim, para uma análise astrológica precisa. Caso não saiba, usamos janela aproximada com limitações descritas.",
        ),
        (
            "Quanto tempo leva para receber o plano?",
            "O envio é automático após o preenchimento completo do formulário: em poucos minutos você recebe o PDF.",
        ),
        (
            "É baseado em que tipo de nutrição?",
            "Nutrição baseada em evidências, referências da base TACO e diretrizes oficiais, sem protocolos extremos.",
        ),
        (
            "Como meus dados são tratados? (LGPD)",
            "Usamos apenas para gerar seu plano e relatório. Armazenamento seguro, sem compartilhamento com terceiros, conforme LGPD.",
        ),
    ]
    for pergunta, resposta in faq_items:
        with st.expander(pergunta, expanded=False):
            st.write(resposta)


def _final_cta_section() -> None:
    st.markdown("## Pronta para receber seu plano feito para o seu corpo e seu mapa?")
    st.markdown(
        "Bloco final com CTA amplo, preço promocional e mockup técnico do dashboard para reforçar clareza e confiabilidade."
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(
            "<div class='placeholder-card' style=\"background-image:url('/mnt/data/gladia_template.html');background-size:cover;\">Mockup 4 — Dashboard ou cálculo</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown("<div class='floating-card'>", unsafe_allow_html=True)
        st.markdown("<div class='mini-label'>Oferta de lançamento</div>", unsafe_allow_html=True)
        st.markdown("<h3>de R$49,90 por R$27,90 — geração automática após o questionário</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p>Pronta para receber seu plano feito para o seu corpo e seu mapa?</p>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='cta-primary'>", unsafe_allow_html=True)
        if st.button("Iniciar minha avaliação NutriSigno", use_container_width=True, key="cta_final"):
            st.switch_page("pages/01_Formulario.py")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            "<p class='eyebrow'>Selo de segurança: dados protegidos conforme LGPD</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown(
        """
        <footer>
        Plano com foco em bem-estar; não substitui acompanhamento médico ou nutricional presencial.<br>
        Política de privacidade e termos disponíveis; respeito à LGPD e cuidado com dados pessoais.
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
    _deliverables_section()
    st.divider()
    _mockup_section()
    st.divider()
    _benefits_section()
    st.divider()
    _plan_mockup_section()
    st.divider()
    _why_it_works_section()
    st.divider()
    _founder_section()
    st.divider()
    _testimonials_section()
    st.divider()
    _faq_section()
    st.divider()
    _final_cta_section()


if __name__ == "__main__":
    main()
