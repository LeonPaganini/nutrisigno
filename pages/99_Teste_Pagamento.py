"""Página de teste/diagnóstico do fluxo de pagamentos (Mercado Pago)."""
from __future__ import annotations

import importlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger(__name__)

_db_spec = importlib.util.find_spec("services.db")
_pay_spec = importlib.util.find_spec("services.payments")
_db = importlib.import_module("services.db") if _db_spec else None
_payments = importlib.import_module("services.payments") if _pay_spec else None


DEFAULT_PAYMENT_PAYLOAD: Dict[str, Any] = {
    "status_pagamento": "nao_encontrado",
    "metodo": "Mercado Pago",
    "valor": None,
    "created_at": None,
    "updated_at": None,
    "preference_id": None,
    "external_reference": None,
    "checkout_url": None,
}


def load_payment_status(pac_id: str) -> Dict[str, Any]:
    """Carrega status de pagamento do paciente, com fallback seguro."""
    payload = {"pac_id": pac_id, **DEFAULT_PAYMENT_PAYLOAD}

    if not pac_id:
        return payload

    if not _db or not hasattr(_db, "fetch_payment_by_pac_id"):
        logger.warning("services.db não disponível; retornando payload mock.")
        return {
            **payload,
            "status_pagamento": "nao_encontrado",
            "valor": 0.0,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    try:
        db_payload = _db.fetch_payment_by_pac_id(pac_id)
    except Exception as exc:  # pragma: no cover - defensivo
        logger.exception("Erro ao carregar status de pagamento: %s", exc)
        return payload

    if not db_payload:
        return payload

    payload.update({k: v for k, v in db_payload.items() if k in payload or k == "pac_id"})
    return payload


def create_payment(pac_id: str, valor: float) -> Dict[str, Any]:
    """Cria um link de pagamento (Mercado Pago ou mock)."""
    logger.info("Solicitando criação de pagamento para %s (valor=%.2f)", pac_id, valor)

    if not pac_id:
        return {"ok": False, "msg": "pac_id ausente."}

    resp: Dict[str, Any]
    if _payments and hasattr(_payments, "create_checkout"):
        try:
            resp = _payments.create_checkout(pac_id, valor)
        except Exception as exc:  # pragma: no cover - defensivo
            logger.exception("Falha ao criar checkout real; usando fallback. Detalhe: %s", exc)
            resp = {}
    else:
        resp = {}

    if not resp:
        fake_pref = f"pref-{pac_id}-{int(datetime.now().timestamp())}"
        resp = {
            "ok": True,
            "msg": "Checkout mock gerado (fallback).",
            "checkout_url": f"https://pay.fake.local/checkout/{fake_pref}?pac_id={pac_id}",
            "preference_id": fake_pref,
            "valor": valor,
            "method": "Mercado Pago",
        }

    if _db and hasattr(_db, "persist_checkout_metadata"):
        try:
            _db.persist_checkout_metadata(
                pac_id,
                {
                    "status_pagamento": "pendente",
                    "preference_id": resp.get("preference_id"),
                    "valor": resp.get("valor"),
                    "checkout_url": resp.get("checkout_url"),
                },
            )
        except Exception as exc:  # pragma: no cover - defensivo
            logger.exception("Não foi possível registrar metadados do checkout: %s", exc)

    return resp


def simulate_webhook(pac_id: str, novo_status: str) -> Optional[bool]:
    """Atualiza manualmente o status de pagamento (uso local/dev)."""
    if not pac_id:
        return False

    if not _db or not hasattr(_db, "update_payment_status"):
        logger.error("DB não disponível para simular webhook.")
        return False

    try:
        return _db.update_payment_status(pac_id, novo_status)
    except Exception as exc:  # pragma: no cover - defensivo
        logger.exception("Erro ao simular webhook: %s", exc)
        return False


_STATUS_COLORS = {
    "aprovado": "green",
    "pago": "green",
    "em_analise": "orange",
    "pendente": "orange",
    "recusado": "red",
    "cancelado": "red",
    "nao_encontrado": "gray",
}


def _render_status_badge(status: str) -> str:
    status_norm = (status or "").strip().lower() or "nao_encontrado"
    color = _STATUS_COLORS.get(status_norm, "gray")
    return f"<span style='color:{color}; font-weight: 700;'>{status_norm}</span>"


def _format_datetime(dt: Any) -> str:
    if not dt:
        return "-"
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat(timespec="seconds")
    return str(dt)


def render_payment_test_page() -> None:
    """Renderiza a página de testes de pagamento."""
    st.set_page_config(page_title="Teste de Pagamentos - NutriSigno", page_icon="💳")

    st.title("Teste de Pagamentos - NutriSigno")
    st.write(
        "Página exclusiva para testar integração com Mercado Pago, status e fluxo de pagamento."
    )

    st.info("Área de testes. NÃO usar em produção.")

    with st.container():
        st.subheader("Identificação")
        pac_id_session = st.session_state.get("pac_id")
        pac_id_input = st.text_input(
            "pac_id (preenche automaticamente se vier da sessão)",
            value=pac_id_session or "",
            key="payment_pac_id_input",
        ).strip()
        pac_id = pac_id_input or pac_id_session or ""

        if pac_id:
            st.write(f"Usando pac_id: **{pac_id}**")
        else:
            st.warning("Informe um pac_id para testar pagamentos.")

        if st.button("Carregar status", type="primary", disabled=not pac_id):
            st.session_state.payment_status = load_payment_status(pac_id)

    status_payload = st.session_state.get("payment_status") if pac_id else None
    if pac_id and not status_payload:
        status_payload = load_payment_status(pac_id)
        st.session_state.payment_status = status_payload

    with st.container():
        st.subheader("Status atual do pagamento")
        if not pac_id:
            st.info("Informe um pac_id para visualizar o status.")
        elif not status_payload or status_payload.get("status_pagamento") == "nao_encontrado":
            st.info("Nenhum pagamento encontrado para este pac_id. Crie um novo link.")
        else:
            with st.expander("Detalhes do pagamento", expanded=True):
                st.markdown(
                    f"Status: {_render_status_badge(status_payload.get('status_pagamento'))}",
                    unsafe_allow_html=True,
                )
                st.write("Método:", status_payload.get("metodo") or "-")
                st.write("Valor:", status_payload.get("valor") or "-")
                st.write("Criado em:", _format_datetime(status_payload.get("created_at")))
                st.write("Atualizado em:", _format_datetime(status_payload.get("updated_at")))
                st.write("preference_id:", status_payload.get("preference_id") or "-")
                st.write("external_reference:", status_payload.get("external_reference") or "-")
                checkout_url = status_payload.get("checkout_url")
                if checkout_url:
                    st.write("Checkout URL:", checkout_url)
                    st.link_button("Abrir tela de pagamento", checkout_url, type="primary")
                else:
                    st.write("Checkout URL: -")

    with st.container():
        st.subheader("Criar/renovar link de pagamento")
        valor = st.number_input("Valor em R$", min_value=0.0, step=1.0, value=50.0)
        if st.button("Criar link de pagamento (Mercado Pago)", disabled=not pac_id):
            result = create_payment(pac_id, valor)
            if result.get("ok"):
                st.success(result.get("msg") or "Checkout criado com sucesso")
                if result.get("checkout_url"):
                    st.link_button(
                        "Abrir tela de pagamento", result.get("checkout_url"), type="primary"
                    )
            else:
                st.error(result.get("msg") or "Não foi possível criar o checkout.")
            st.session_state.payment_status = load_payment_status(pac_id)

    with st.container():
        st.subheader("Simular webhook / atualizar status (DEV)")
        st.warning("Apenas para desenvolvimento local. Não usar em produção.")
        novo_status = st.selectbox(
            "Novo status",
            ["pendente", "em_analise", "aprovado", "recusado", "cancelado"],
        )
        if st.button("Aplicar status (simular webhook)", disabled=not pac_id):
            ok = simulate_webhook(pac_id, novo_status)
            if ok:
                st.success(f"Status atualizado para '{novo_status}'.")
                st.session_state.payment_status = load_payment_status(pac_id)
            else:
                st.error("Não foi possível atualizar o status (ver logs ou DB).")

    with st.container():
        st.subheader("Impacto no fluxo do plano")
        status_atual = (status_payload or {}).get("status_pagamento") or "nao_encontrado"
        if status_atual == "aprovado":
            st.success(
                "No fluxo oficial, o botão 'Gerar plano nutricional' estará HABILITADO no Dashboard."
            )
        else:
            st.info(
                "No fluxo oficial, o botão 'Gerar plano nutricional' deve permanecer DESABILITADO."
            )

    with st.container():
        st.subheader("Navegação")
        if st.button("Ir para Dashboard / Resultado", type="secondary"):
            try:
                st.switch_page("pages/02_Dashboard.py")
            except Exception as exc:  # pragma: no cover - defensivo
                st.error(
                    "Não foi possível abrir o Dashboard. Verifique se 'pages/02_Dashboard.py' existe."
                )
                logger.exception("Erro ao trocar de página: %s", exc)


if __name__ == "__main__":
    render_payment_test_page()
