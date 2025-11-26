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


def generate_pre_payment_pdf(
    payload: Mapping[str, Any],
    output_path: str | Path,
    *,
    incluir_cardapio: bool = False,  # compatibilidade futura
) -> str:
    """Gera um PDF resumido do pré-plano.

    Parameters
    ----------
    payload:
        Dicionário contendo o pré-plano (plano_alimentar/macros/porções).
    output_path:
        Caminho para salvar o arquivo.
    incluir_cardapio:
        Mantido apenas para compatibilidade com chamadas do dashboard;
        atualmente ignorado porque o pré-plano não inclui cardápio IA.
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

            if y < 3 * cm:
                c.showPage()
                y = height - 2 * cm
                c.setFont("Helvetica", 10)

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(2 * cm, 1.8 * cm, "Documento gerado automaticamente para diagnóstico interno.")

    c.save()
    return str(out_path)


__all__ = ["generate_pre_payment_pdf"]
