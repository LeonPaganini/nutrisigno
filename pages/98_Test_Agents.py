"""Página de testes dos agentes de IA (ambiente de desenvolvimento/QA)."""

from __future__ import annotations

import json
import logging
import os
import random
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Mapping

import streamlit as st

from agents import cardapio_builder, orchestrator, subs_loader
from modules import nutrisigno_refeicoes, pdf_generator_v2

logger = logging.getLogger("testes_agentes")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs")) / "testes"
TEMPLATES_PATH = Path("data") / "templates_refeicoes.json"
SUBSTITUICOES_PATH = Path("data") / "substituicoes.json"
DEFAULT_USER: Dict[str, Any] = {
    "nome": "Paciente Teste QA",
    "sexo": "feminino",
    "idade": 32,
    "peso_kg": 68,
    "altura_cm": 168,
    "nivel_atividade": "moderado",
    "objetivo": "perda de gordura",
    "signo": "Libra",
    "perfil_astrologico_resumido": "Busca equilíbrio e praticidade",
}


def _init_state() -> None:
    st.session_state.setdefault("log_orquestrador", [])
    st.session_state.setdefault("log_cardapio", [])
    st.session_state.setdefault("log_pdf_pre", [])
    st.session_state.setdefault("log_pdf_final", [])
    st.session_state.setdefault("log_e2e", [])
    st.session_state.setdefault("pre_plano_teste", None)
    st.session_state.setdefault("cardapio_teste", None)
    st.session_state.setdefault("pdf_pre_path", None)
    st.session_state.setdefault("pdf_final_path", None)
    st.session_state.setdefault("plano_templates", None)
    st.session_state.setdefault("plano_templates_erro", None)
    st.session_state.setdefault("refeicao_unitaria", None)
    st.session_state.setdefault("erro_refeicao_unitaria", None)


def _reset_log(key: str) -> None:
    st.session_state[key] = []


def _append_log(key: str, message: str, level: str = "info") -> None:
    entry = f"[{level.upper()}] {message}"
    st.session_state[key].append(entry)
    getattr(logger, level, logger.info)(message)


def _render_log_area(key: str, placeholder) -> None:
    content = "\n".join(st.session_state.get(key, [])) or "Aguardando execução..."
    placeholder.code(content)


def _simulate_payment_log(key: str) -> None:
    _append_log(key, "Pagamento simulado aprovado para este teste.")


@st.cache_data(show_spinner=False)
def _carregar_templates_e_substituicoes() -> Dict[str, Any]:
    """Carrega ``templates_refeicoes.json`` e ``substituicoes.json`` uma única vez.

    Retornamos um dicionário com erros amigáveis para que a UI consiga exibir
    feedback visual sem quebrar a página de testes.
    """

    try:
        templates = nutrisigno_refeicoes.carregar_templates(str(TEMPLATES_PATH))
    except Exception as exc:  # pragma: no cover - fluxo visual
        return {"erro": f"Falha ao carregar templates_refeicoes.json: {exc}"}

    try:
        substituicoes = nutrisigno_refeicoes.carregar_substituicoes(
            str(SUBSTITUICOES_PATH)
        )
    except Exception as exc:  # pragma: no cover - fluxo visual
        return {"erro": f"Falha ao carregar substituicoes.json: {exc}"}

    return {"templates": templates, "substituicoes": substituicoes}


def _slots_para_texto(slots: Mapping[str, int] | None) -> str:
    if not slots:
        return "Nenhum slot informado no template."
    partes = [f"{slot}: {quant} porção(ões)" for slot, quant in slots.items()]
    return ", ".join(partes)


def _render_refeicao_card(refeicao: Mapping[str, Any]) -> None:
    """Desenha um card visual para uma refeição gerada a partir dos templates."""

    itens = refeicao.get("itens_escolhidos", []) or refeicao.get("itens", [])
    slots = refeicao.get("slots", {})

    st.markdown("---")
    st.subheader(refeicao.get("tipo_refeicao", "Refeição"))
    st.caption(
        f"Template utilizado: {refeicao.get('template_id', 'N/A')} — "
        f"{refeicao.get('descricao', 'Sem descrição')}"
    )

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.write("Resumo de slots do template:")
        st.info(_slots_para_texto(slots))
    with col_b:
        st.write("Exemplo de prato informado no template:")
        exemplo = refeicao.get("exemplo_prato") or []
        if exemplo:
            for item in exemplo:
                st.caption(f"- {item.get('nome')} ({item.get('porcao')})")
        else:
            st.caption("Template não fornece exemplo de prato.")

    if itens:
        st.write("Itens escolhidos para esta refeição")
        st.table(itens)
    else:
        st.warning("Nenhum item foi gerado para esta refeição.")


def _render_plano_diario(plano: Mapping[str, Any]) -> None:
    """Exibe o plano diário de forma visual e expandível."""

    refeicoes: List[Mapping[str, Any]] = plano.get("plano_diario") or []
    if not refeicoes:
        st.warning("Nenhuma refeição foi gerada a partir dos templates.")
        return

    st.success(plano.get("resumo_textual", "Plano gerado com sucesso."))
    for refeicao in refeicoes:
        _render_refeicao_card(refeicao)

    with st.expander("JSON bruto do plano diário", expanded=False):
        st.json(plano, expanded=False)


def _render_templates_carregados(templates: Mapping[str, Any]) -> None:
    st.write("Modelos carregados do templates_refeicoes.json:")
    tipos = list(templates.keys())
    tipo_escolhido = st.selectbox(
        "Filtrar por tipo de refeição", tipos, index=0, key="tipo_template_debug"
    )
    modelos = templates.get(tipo_escolhido, [])
    st.caption(
        "Cada linha abaixo representa um template que pode ser utilizado no fluxo de teste."
    )
    st.dataframe(modelos, use_container_width=True)


def run_orquestrador_test() -> None:
    key = "log_orquestrador"
    _reset_log(key)
    _append_log(key, "Iniciando teste do orquestrador com payload mock.")
    dados_usuario = {**DEFAULT_USER}

    try:
        pre_plano = orchestrator.gerar_plano_pre_pagamento(dados_usuario)
        st.session_state["pre_plano_teste"] = pre_plano
        kcal = pre_plano.get("macros", {}).get("kcal")
        dieta_pdf = pre_plano.get("dieta_pdf_arquivo")
        _append_log(key, f"kcal alvo calculada: {kcal}")
        _append_log(key, f"Dieta escolhida: {pre_plano.get('dieta_pdf_kcal')} kcal ({dieta_pdf})")
        _append_log(key, f"Resumo das macros: {json.dumps(pre_plano.get('macros', {}), ensure_ascii=False)}")

        porcoes = pre_plano.get("porcoes_por_refeicao") or {}
        exemplo_refeicao = next(iter(porcoes.items()), None)
        if exemplo_refeicao:
            refeicao, itens = exemplo_refeicao
            _append_log(key, f"Exemplo de refeição '{refeicao}': {json.dumps(itens, ensure_ascii=False)}")
        _append_log(key, "Pré-plano gerado e armazenado em sessão.")
    except Exception as exc:  # pragma: no cover - apenas visualização
        trace = traceback.format_exc()
        _append_log(key, f"Erro ao gerar pré-plano: {exc}", level="error")
        _append_log(key, trace, level="error")
        st.session_state["pre_plano_teste"] = None


def run_cardapio_test() -> None:
    key = "log_cardapio"
    _reset_log(key)
    pre_plano = st.session_state.get("pre_plano_teste")
    if not pre_plano:
        _append_log(key, "Nenhum pré-plano disponível. Execute o teste do orquestrador primeiro.", level="error")
        return

    _append_log(key, "Carregando substituicoes.json...")
    try:
        substituicoes = subs_loader.load_substitutions()
        _append_log(key, f"Categorias de substituição carregadas: {len(substituicoes.get('categorias', {}))}")
    except Exception as exc:  # pragma: no cover - fallback visual
        _append_log(key, f"Erro ao carregar substituições: {exc}", level="error")
        _append_log(key, traceback.format_exc(), level="error")
        st.session_state["cardapio_teste"] = None
        return

    _append_log(key, "Disparando agente de cardápio (modo simulado/determinístico se IA ausente)...")
    try:
        start = time.perf_counter()
        input_size = len(json.dumps(pre_plano, ensure_ascii=False))
        cardapio = cardapio_builder.build_cardapio(pre_plano, substituicoes)
        elapsed = time.perf_counter() - start
        output_size = len(json.dumps(cardapio, ensure_ascii=False))

        if cardapio.get("erro"):
            raise RuntimeError(cardapio["erro"])

        st.session_state["cardapio_teste"] = cardapio
        _append_log(key, f"Tempo de geração: {elapsed:.2f}s | prompt ~{input_size} chars | resposta ~{output_size} chars")
        _append_log(key, "Cardápio IA recebido com sucesso.")
    except Exception as exc:  # pragma: no cover - visualização
        st.session_state["cardapio_teste"] = None
        _append_log(key, f"Falha na geração do cardápio: {exc}", level="error")
        _append_log(key, traceback.format_exc(), level="error")


def run_pdf_pre_test() -> None:
    key = "log_pdf_pre"
    _reset_log(key)
    pre_plano = st.session_state.get("pre_plano_teste")
    if not pre_plano:
        _append_log(key, "Pré-plano ausente. Rode o teste do orquestrador primeiro.", level="error")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"pre_pagamento_{int(time.time())}.pdf"
    path = OUTPUT_DIR / filename
    _append_log(key, f"Gerando PDF pré-pagamento em {path}...")
    try:
        pdf_path = pdf_generator_v2.generate_pre_payment_pdf(pre_plano, path, incluir_cardapio=False)
        st.session_state["pdf_pre_path"] = pdf_path
        _append_log(key, "PDF pré-pagamento gerado com sucesso.")
    except Exception as exc:  # pragma: no cover - visualização
        st.session_state["pdf_pre_path"] = None
        _append_log(key, f"Erro ao gerar PDF pré-pagamento: {exc}", level="error")
        _append_log(key, traceback.format_exc(), level="error")


def run_pdf_final_test() -> None:
    key = "log_pdf_final"
    _reset_log(key)
    pre_plano = st.session_state.get("pre_plano_teste")
    cardapio = st.session_state.get("cardapio_teste")

    if not pre_plano:
        _append_log(key, "Pré-plano ausente. Rode o teste do orquestrador primeiro.", level="error")
        return
    if not cardapio:
        _append_log(key, "Cardápio ausente. Rode o teste do agente de cardápio primeiro.", level="error")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"cardapio_final_{int(time.time())}.pdf"
    path = OUTPUT_DIR / filename
    _append_log(key, f"Gerando PDF final com cardápio IA em {path}...")

    payload = dict(pre_plano)
    payload["cardapio_ia"] = cardapio
    try:
        pdf_path = pdf_generator_v2.generate_pre_payment_pdf(payload, path, incluir_cardapio=True)
        st.session_state["pdf_final_path"] = pdf_path
        _append_log(key, "PDF final gerado com sucesso (modo teste).")
    except Exception as exc:  # pragma: no cover - visualização
        st.session_state["pdf_final_path"] = None
        _append_log(key, f"Erro ao gerar PDF final: {exc}", level="error")
        _append_log(key, traceback.format_exc(), level="error")


def run_e2e() -> None:
    key = "log_e2e"
    _reset_log(key)
    _append_log(key, "Iniciando fluxo end-to-end simulado...")
    start = time.perf_counter()

    try:
        run_orquestrador_test()
        _render_log_area("log_orquestrador", st.empty())
        _append_log(key, "Orquestrador concluído.")

        _simulate_payment_log(key)

        run_cardapio_test()
        _render_log_area("log_cardapio", st.empty())
        if not st.session_state.get("cardapio_teste"):
            raise RuntimeError("Cardápio não gerado; encerrando E2E.")
        _append_log(key, "Agente de cardápio concluído.")

        run_pdf_final_test()
        _render_log_area("log_pdf_final", st.empty())
        if not st.session_state.get("pdf_final_path"):
            raise RuntimeError("PDF final não foi gerado.")

        elapsed = time.perf_counter() - start
        _append_log(key, f"Fluxo E2E finalizado com sucesso em {elapsed:.2f}s.")
    except Exception as exc:  # pragma: no cover - visualização
        _append_log(key, f"Falha no fluxo E2E: {exc}", level="error")
        _append_log(key, traceback.format_exc(), level="error")


# ----------------------------- Teste de templates/refeições -----------------------------
def run_teste_templates(paciente: Mapping[str, Any], rng_seed: int | None) -> None:
    """Roda o teste End-to-End (simulado) baseado em templates de refeição.

    Esta função é usada apenas na página de testes e não afeta usuários finais.
    """

    st.session_state["plano_templates_erro"] = None
    resultado = nutrisigno_refeicoes.gerar_plano_diario_simulado(
        paciente=paciente,
        templates_path=str(TEMPLATES_PATH),
        substituicoes_path=str(SUBSTITUICOES_PATH),
        rng_seed=rng_seed,
    )

    if resultado.get("erro"):
        st.session_state["plano_templates"] = None
        st.session_state["plano_templates_erro"] = resultado
    else:
        st.session_state["plano_templates"] = resultado


def run_refeicao_unitaria(tipo_refeicao: str, template_id: str, rng_seed: int | None):
    """Gera uma refeição unitária e sugestões de substituição a partir de um template."""

    st.session_state["erro_refeicao_unitaria"] = None
    st.session_state["refeicao_unitaria"] = None

    try:
        resultado = nutrisigno_refeicoes.montar_refeicao_e_substituicoes(
            templates_path=str(TEMPLATES_PATH),
            substituicoes_path=str(SUBSTITUICOES_PATH),
            tipo_refeicao=tipo_refeicao,
            template_id=template_id,
            rng=None if rng_seed is None else random.Random(rng_seed),
        )
    except Exception as exc:  # pragma: no cover - visualização
        st.session_state["erro_refeicao_unitaria"] = str(exc)
        return

    st.session_state["refeicao_unitaria"] = resultado


# ----------------------------- UI -----------------------------
st.set_page_config(page_title="Testes de Agentes de IA - NutriSigno", page_icon="🧪", layout="wide")
st.title("🧪 Testes de Agentes de IA - NutriSigno")
st.caption("Ambiente isolado para QA dos fluxos de IA (não afeta usuários finais).")

_init_state()
tabs = st.tabs([
    "Templates de Refeição (NutriSigno)",
    "Pipeline de IA e PDFs",
])

with tabs[0]:
    st.header("Teste NutriSigno – Templates de Refeição")
    st.write(
        "Fluxo guiado para garantir que `templates_refeicoes.json` e o catálogo de "
        "substituições estão sendo usados ao gerar planos simulados."
    )

    # Carregamento único dos arquivos templates_refeicoes.json e substituicoes.json.
    recursos = _carregar_templates_e_substituicoes()
    if recursos.get("erro"):
        st.error(recursos["erro"])
    else:
        st.success(
            "Templates e catálogo de substituições carregados com sucesso. "
            "Eles serão usados em todos os testes abaixo."
        )

    st.subheader("Configurações do Teste")
    col_a, col_b, col_c = st.columns(3)
    nome_paciente = col_a.text_input("Nome do paciente", value=DEFAULT_USER["nome"])
    objetivo = col_b.text_input("Objetivo", value=DEFAULT_USER.get("objetivo", ""))
    usar_seed = col_c.checkbox("Usar semente fixa?", value=True)
    seed_valor = col_c.number_input("Valor da semente", value=42, step=1)
    rng_seed = int(seed_valor) if usar_seed else None

    paciente_teste = {
        **DEFAULT_USER,
        "nome": nome_paciente or DEFAULT_USER["nome"],
        "objetivo": objetivo or DEFAULT_USER.get("objetivo"),
    }

    st.subheader("Seleção de Teste")
    col_left, col_right = st.columns(2)
    botao_desabilitado = bool(recursos.get("erro"))

    with col_left:
        st.markdown("**Teste End-to-End (simulado) usando templates**")
        st.caption(
            "Gera um plano diário completo. Cada refeição escolhe um template do JSON, "
            "respeita os slots e aplica substituições."
        )
        # Botão principal para o fluxo End-to-End (simulado) com templates.
        if st.button(
            "Gerar plano diário a partir dos templates",
            type="primary",
            disabled=botao_desabilitado,
        ):
            run_teste_templates(paciente_teste, rng_seed)

    with col_right:
        st.markdown("**Teste unitário de refeição**")
        st.caption(
            "Escolha manualmente um tipo e ID de template para gerar apenas uma refeição "
            "e visualizar sugestões de substituição."
        )
        if recursos.get("templates"):
            tipos = list(recursos["templates"].keys())
            tipo_escolhido = st.selectbox(
                "Tipo de refeição",
                tipos,
                key="tipo_refeicao_unitario",
            )
            modelos = recursos["templates"].get(tipo_escolhido, [])
            ids_modelos = [m.get("id", "") for m in modelos]
            template_escolhido = st.selectbox(
                "Template", ids_modelos, key="template_id_unitario"
            )
        else:
            tipo_escolhido = ""
            template_escolhido = ""
            st.info("Carregue os templates para habilitar este teste.")

        if st.button(
            "Gerar refeição unitária",
            disabled=botao_desabilitado or not template_escolhido,
        ):
            run_refeicao_unitaria(tipo_escolhido, template_escolhido, rng_seed)

    st.subheader("Resultados visuais")
    if st.session_state.get("plano_templates_erro"):
        st.error(
            "Falha ao executar o teste End-to-End com templates.",
            icon="🚨",
        )
        with st.expander("Detalhes do erro"):
            st.json(st.session_state["plano_templates_erro"])
    elif st.session_state.get("plano_templates"):
        # Resultado visual do fluxo End-to-End (simulado) com templates e substituições.
        _render_plano_diario(st.session_state["plano_templates"])
    else:
        st.info("Gere um plano diário para visualizar o uso dos templates na prática.")

    if st.session_state.get("erro_refeicao_unitaria"):
        st.error(st.session_state["erro_refeicao_unitaria"])
    elif st.session_state.get("refeicao_unitaria"):
        st.success("Refeição gerada a partir do template selecionado.")
        dados_refeicao = st.session_state["refeicao_unitaria"]
        _render_refeicao_card(dados_refeicao.get("refeicao", {}))
        with st.expander("Substituições sugeridas por slot"):
            st.json(dados_refeicao.get("substituicoes", {}))

    if recursos.get("templates"):
        with st.expander("Templates carregados do JSON", expanded=False):
            _render_templates_carregados(recursos["templates"])
    if recursos.get("substituicoes"):
        with st.expander("Categorias de substituição disponíveis", expanded=False):
            st.json({"categorias": list(recursos["substituicoes"].keys())})


with tabs[1]:
    st.header("Pipeline de IA, PDFs e agentes auxiliares")
    st.info(
        "Use os botões abaixo para disparar cada etapa do pipeline. "
        "Os logs são limpos a cada execução para facilitar a leitura."
    )

    with st.expander("Teste do Orquestrador (Pré-plano, sem IA)", expanded=True):
        log_placeholder = st.empty()
        if st.button("Rodar teste do orquestrador", type="primary"):
            run_orquestrador_test()
        _render_log_area("log_orquestrador", log_placeholder)
        pre_plano = st.session_state.get("pre_plano_teste")
        if pre_plano:
            st.json(pre_plano)

    with st.expander("Teste do Agente de Cardápio (IA OpenAI / fallback determinístico)", expanded=True):
        log_placeholder = st.empty()
        if st.button("Rodar teste do agente de cardápio", type="primary"):
            run_cardapio_test()
        _render_log_area("log_cardapio", log_placeholder)
        cardapio = st.session_state.get("cardapio_teste")
        if cardapio:
            st.json(cardapio)

    with st.expander("Teste do PDF Pré-pagamento", expanded=False):
        log_placeholder = st.empty()
        if st.button("Gerar PDF de teste (pré-pagamento)", type="primary"):
            run_pdf_pre_test()
        _render_log_area("log_pdf_pre", log_placeholder)
        pdf_path = st.session_state.get("pdf_pre_path")
        if pdf_path and Path(pdf_path).exists():
            pdf_bytes = Path(pdf_path).read_bytes()
            st.download_button(
                "Baixar PDF pré-pagamento (teste)",
                data=pdf_bytes,
                file_name=Path(pdf_path).name,
                mime="application/pdf",
            )
            st.caption(f"Arquivo: {pdf_path}")

    with st.expander("Teste do PDF Final + Cardápio IA", expanded=False):
        log_placeholder = st.empty()
        if st.button("Gerar PDF final com cardápio IA (teste)", type="primary"):
            run_pdf_final_test()
        _render_log_area("log_pdf_final", log_placeholder)
        pdf_path = st.session_state.get("pdf_final_path")
        if pdf_path and Path(pdf_path).exists():
            pdf_bytes = Path(pdf_path).read_bytes()
            st.download_button(
                "Baixar PDF final (teste)",
                data=pdf_bytes,
                file_name=Path(pdf_path).name,
                mime="application/pdf",
            )
            st.caption(f"Arquivo: {pdf_path}")
            st.warning("PDF gerado apenas para testes locais (não enviado a pacientes).")

    with st.expander("Teste End-to-End (simulado)", expanded=False):
        log_placeholder = st.empty()
        if st.button("Rodar fluxo E2E (pré-plano → IA → PDF final)", type="primary"):
            run_e2e()
        _render_log_area("log_e2e", log_placeholder)
        if st.session_state.get("pdf_final_path"):
            st.caption(f"Último PDF final gerado: {st.session_state['pdf_final_path']}")
