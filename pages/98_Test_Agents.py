"""Página de testes dos agentes de IA (ambiente de desenvolvimento/QA)."""

from __future__ import annotations

import json
import logging
import os
import time
import traceback
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from agents import cardapio_builder, orchestrator, subs_loader
from modules import pdf_generator_v2

logger = logging.getLogger("testes_agentes")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs")) / "testes"
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


# ----------------------------- UI -----------------------------
st.set_page_config(page_title="Testes de Agentes de IA - NutriSigno", page_icon="🧪", layout="wide")
st.title("🧪 Testes de Agentes de IA - NutriSigno")
st.caption("Ambiente isolado para QA dos fluxos de IA (não afeta usuários finais).")

_init_state()

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
