"""Geração simples de PDF para o pré-pagamento.

Esta versão é usada em ambientes de diagnóstico para validar o pipeline
determinístico do NutriSigno sem dependências de IA. O objetivo é apenas
confirmar que os dados do pré-plano podem ser serializados em um PDF e
gravados no diretório de saída configurado.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def _normalize_porcoes(porcoes: Any) -> dict[str, dict[str, str]]:
    if not isinstance(porcoes, Mapping):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for refeicao, itens in porcoes.items():
        itens_map: dict[str, str] = {}
        if isinstance(itens, Mapping):
            itens_map = {str(alimento): str(porcao) for alimento, porcao in itens.items()}
        normalized[str(refeicao)] = itens_map
    return normalized


def _normalize_cardapio(cardapio: Any) -> dict[str, Any]:
    """Sanitize payload de cardápio para escrita no PDF."""

    if not isinstance(cardapio, Mapping):
        return {}

    if "cardapio_dia" in cardapio:
        cardapio = cardapio.get("cardapio_dia") or {}

    if not isinstance(cardapio, Mapping):
        return {}

    refeicoes = cardapio.get("refeicoes") if isinstance(cardapio, Mapping) else []
    refeicoes_norm = []
    if isinstance(refeicoes, list):
        for refeicao in refeicoes:
            if not isinstance(refeicao, Mapping):
                continue
            refeicoes_norm.append(
                {
                    "nome_refeicao": refeicao.get("nome_refeicao") or "Refeição",
                    "refeicao_padrao": refeicao.get("refeicao_padrao") or [],
                    "opcoes_substituicao": refeicao.get("opcoes_substituicao") or {},
                    "comentario_astrologico": refeicao.get("comentario_astrologico") or "",
                }
            )

    return {
        "descricao_dia": cardapio.get("descricao_dia"),
        "refeicoes": refeicoes_norm,
    }


def _ensure_space(c: canvas.Canvas, y: float, height: float, *, reset_font: bool = True) -> float:
    """Garante espaço disponível; cria nova página quando necessário."""

    if y < 3 * cm:
        c.showPage()
        if reset_font:
            c.setFont("Helvetica", 10)
        return height - 2 * cm
    return y


def generate_pre_payment_pdf(
    payload: Mapping[str, Any],
    output_path: str | Path,
    *,
    incluir_cardapio: bool = False,
) -> str:
    """Gera um PDF resumido do pré-plano.

    Parameters
    ----------
    payload:
        Dicionário contendo o pré-plano (plano_alimentar/macros/porções).
    output_path:
        Caminho para salvar o arquivo.
    incluir_cardapio:
        Quando ``True``, tenta incluir "cardapio_ia" em formato resumido
        (campo opcional do payload).
    """

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    plan = {}
    if isinstance(payload, Mapping):
        plan = (
            payload.get("plano_alimentar")
            or payload.get("plano")
            or payload
        )

    dados_usuario = {}
    if isinstance(payload, Mapping):
        dados_usuario = plan.get("dados_usuario") or payload.get("respostas") or {}

    macros = plan.get("macros") if isinstance(plan, Mapping) else {}
    porcoes_por_refeicao = _normalize_porcoes(plan.get("porcoes_por_refeicao") if isinstance(plan, Mapping) else {})
    cardapio_ia = _normalize_cardapio(plan.get("cardapio_ia") or payload.get("cardapio_ia")) if incluir_cardapio else {}

    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setTitle("Pré-plano NutriSigno (diagnóstico)")
    width, height = A4
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "NutriSigno · Pré-plano (modo teste)")
    y -= 1.2 * cm

    c.setFont("Helvetica", 11)
    nome = dados_usuario.get("nome") or dados_usuario.get("nome_completo") or "Paciente"
    objetivo = dados_usuario.get("objetivo") or "N/D"
    c.drawString(2 * cm, y, f"Paciente: {nome}")
    y -= 0.8 * cm
    c.drawString(2 * cm, y, f"Objetivo: {objetivo}")
    y -= 1.0 * cm

    if macros:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Metas de macronutrientes")
        y -= 0.8 * cm
        c.setFont("Helvetica", 10)
        for label, value in macros.items():
            c.drawString(2.2 * cm, y, f"- {label}: {value}")
            y -= 0.6 * cm
        y -= 0.4 * cm

    if porcoes_por_refeicao:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Porções por refeição (pré-pagamento)")
        y -= 0.8 * cm
        c.setFont("Helvetica", 10)
        for refeicao, itens in porcoes_por_refeicao.items():
            c.drawString(2.0 * cm, y, f"• {refeicao}")
            y -= 0.6 * cm
            for alimento, porcao in itens.items():
                c.drawString(2.6 * cm, y, f"- {alimento}: {porcao}")
                y -= 0.5 * cm
            y -= 0.2 * cm

            y = _ensure_space(c, y, height)

    if cardapio_ia:
        y -= 0.2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Cardápio IA (teste)")
        y -= 0.8 * cm
        c.setFont("Helvetica", 10)
        descricao = cardapio_ia.get("descricao_dia")
        if descricao:
            c.drawString(2.0 * cm, y, descricao)
            y -= 0.6 * cm

        for refeicao in cardapio_ia.get("refeicoes", []):
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2.0 * cm, y, f"• {refeicao.get('nome_refeicao')}")
            y -= 0.5 * cm
            c.setFont("Helvetica", 10)

            padrao = refeicao.get("refeicao_padrao") or []
            for item in padrao:
                alimento = item.get("alimento") or item.get("item") or "Alimento"
                categoria = item.get("categoria_porcoes") or "Categoria"
                porcoes = item.get("porcoes_equivalentes") or 1
                c.drawString(2.6 * cm, y, f"- {alimento} ({categoria}) · {porcoes} porção(ões)")
                y -= 0.45 * cm

            substituicoes = refeicao.get("opcoes_substituicao") or {}
            for categoria, opcoes in substituicoes.items():
                c.drawString(2.6 * cm, y, f"Substituições para {categoria}:")
                y -= 0.4 * cm
                for opcao in opcoes:
                    c.drawString(3.0 * cm, y, f"· {opcao}")
                    y -= 0.35 * cm

            comentario = refeicao.get("comentario_astrologico")
            if comentario:
                c.setFont("Helvetica-Oblique", 9)
                c.drawString(2.6 * cm, y, comentario)
                c.setFont("Helvetica", 10)
                y -= 0.45 * cm

            y -= 0.15 * cm
            y = _ensure_space(c, y, height)

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(2 * cm, 1.8 * cm, "Documento gerado automaticamente para diagnóstico interno.")

    c.save()
    return str(out_path)


__all__ = ["generate_pre_payment_pdf"]
