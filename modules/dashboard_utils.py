"""Utilities for generating health insights and dashboards.

This module contains helper functions to compute derived insights from the
user's raw input data, generate charts with matplotlib for interactive
display in Streamlit, and produce exportable artefacts such as PDF
reports and shareable images.  The implementation mirrors the original
project with minor formatting adjustments for clarity.
"""

from __future__ import annotations

import io
import json
import os
from typing import Any, Dict

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

def _bmi_status(bmi: float) -> str:
    """Classify BMI into categories."""
    if bmi < 18.5:
        return "Abaixo do peso"
    if 18.5 <= bmi < 25:
        return "Peso normal"
    if 25 <= bmi < 30:
        return "Sobrepeso"
    return "Obesidade"

def _water_status(consumption_l: float, recommended_l: float) -> str:
    """Return a descriptive hydration status comparing consumption to recommended."""
    ratio = consumption_l / recommended_l if recommended_l > 0 else 0
    if ratio >= 1.0:
        return "Excelente, vocÃª estÃ¡ bem hidratado(a)!"
    if 0.8 <= ratio < 1.0:
        return "Bom, porÃ©m vocÃª pode aumentar um pouco a ingestÃ£o de Ã¡gua."
    return "AtenÃ§Ã£o: aumente o consumo de Ã¡gua para evitar desidrataÃ§Ã£o."

def _interpret_bristol(selection: str) -> str:
    """Interpret the Bristol stool scale selection into a concise description."""
    mapping = {
        1: "Fezes muito duras, indicar possÃ­vel constipaÃ§Ã£o e baixa ingestÃ£o de fibras.",
        2: "Fezes duras, sinal de constipaÃ§Ã£o e necessidade de mais fibras e Ã¡gua.",
        3: "Fezes com fissuras, indicam tendÃªncia Ã  constipaÃ§Ã£o; aumentar fibras e lÃ­quidos.",
        4: "Fezes normais, consistÃªncia saudÃ¡vel.",
        5: "Fezes moles, podem indicar alimentaÃ§Ã£o leve ou possÃ­vel intolerÃ¢ncia alimentar.",
        6: "Fezes pastosas, sugerem possÃ­vel diarreia ou intolerÃ¢ncia; consulte um profissional se persistir.",
        7: "Fezes lÃ­quidas, sinal de diarreia; hidrateâse e procure atendimento se necessÃ¡rio.",
    }
    try:
        num = int(selection.split(" ")[1]) if selection.startswith("Tipo") else int(selection.split("-")[0])
    except Exception:
        return "NÃ£o foi possÃ­vel interpretar o tipo de fezes."
    return mapping.get(num, "Tipo de fezes desconhecido.")

def _interpret_urine(selection: str) -> str:
    """Interpret urine colour selection into hydration advice."""
    if "Transparente" in selection or "Amarelo muito claro" in selection:
        return "Excelente hidrataÃ§Ã£o! Mantenha o consumo de Ã¡gua."
    if "Amarelo claro" in selection or "Amarelo" in selection:
        return "HidrataÃ§Ã£o moderada; aumente sua ingestÃ£o de Ã¡gua."
    if "Amarelo escuro" in selection:
        return "AtenÃ§Ã£o! PossÃ­vel desidrataÃ§Ã£o; beba mais Ã¡gua."
    return "Perigo extremo! Procure atendimento mÃ©dico; vocÃª estÃ¡ muito desidratado(a)."

def _sign_hints() -> Dict[str, str]:
    """Return behavioural hints by zodiac sign for nutrition adherence."""
    return {
        "Ãries": "Evite decisÃµes impulsivas: planeje suas refeiÃ§Ãµes e escolha opÃ§Ãµes saciantes.",
        "Touro": "Valorize a qualidade, evitando excessos; comidas prazerosas podem ser saudÃ¡veis.",
        "GÃªmeos": "Varie os alimentos para evitar tÃ©dio e mantenha refeiÃ§Ãµes regulares.",
        "CÃ¢ncer": "Prefira refeiÃ§Ãµes leves e frequentes para evitar desconfortos gÃ¡stricos.",
        "LeÃ£o": "Evite exagerar para impressionar; busque equilÃ­brio e moderaÃ§Ã£o.",
        "Virgem": "Mantenha uma rotina organizada, preparando refeiÃ§Ãµes caseiras sempre que possÃ­vel.",
        "Libra": "Planeje seu cardÃ¡pio semanal para reduzir indecisÃ£o e escolhas de Ãºltima hora.",
        "EscorpiÃ£o": "Evite extremos alimentares; consuma porÃ§Ãµes controladas e variadas.",
        "SagitÃ¡rio": "Cuidado com o entusiasmo excessivo: busque equilÃ­brio entre prazer e nutriÃ§Ã£o.",
        "CapricÃ³rnio": "EstabeleÃ§a pausas alimentares e evite rigidez excessiva; permita pequenas indulgÃªncias.",
        "AquÃ¡rio": "Experimente novos ingredientes, mas mantenha constÃ¢ncia e variedade.",
        "Peixes": "Escute seu corpo e hidrateâse; refeiÃ§Ãµes intuitivas podem ajudar na saciedade.",
    }

def compute_insights(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute derived insights from the user's input data.

    Parameters
    ----------
    data : dict
        Raw data collected from the user during the Streamlit form.

    Returns
    -------
    dict
        A dictionary containing derived metrics and textual interpretations.
    """
    weight = data.get("peso")
    height = data.get("altura")
    water = data.get("consumo_agua")
    sign = data.get("signo") or ""

    bmi: Optional[float] = None
    bmi_category = ""
    if weight and height:
        try:
            h_m = float(height) / 100.0
            bmi = float(weight) / (h_m ** 2) if h_m > 0 else None
            if bmi is not None:
                bmi_category = _bmi_status(bmi)
        except Exception:
            bmi = None

    # Recommended water intake: 35 ml per kg body weight (approx.)
    recommended_water = float(weight) * 35 / 1000 if weight else 0
    water_status = _water_status(float(water) if water else 0, recommended_water)

    # Interpret Bristol stool scale and urine colour
    bristol_text = _interpret_bristol(data.get("tipo_fezes", ""))
    urine_text = _interpret_urine(data.get("cor_urina", ""))

    # Sign hint
    sign_hint = _sign_hints().get(sign, "")

    # Motivation and stress recommendations
    motivacao = data.get("motivacao")
    estresse = data.get("estresse")
    mental_notes = ""
    if motivacao and estresse:
        if motivacao >= 4 and estresse <= 2:
            mental_notes = "VocÃª estÃ¡ motivado(a) e com baixo estresse, Ã³timo cenÃ¡rio para mudanÃ§as!"
        elif motivacao >= 4 and estresse > 2:
            mental_notes = "Alta motivaÃ§Ã£o, mas com estresse; tente tÃ©cnicas de relaxamento para manter o foco."
        elif motivacao < 4 and estresse <= 2:
            mental_notes = "VocÃª tem baixa motivaÃ§Ã£o, mas baixo estresse; busque fontes de inspiraÃ§Ã£o para engajar."
        else:
            mental_notes = "MotivaÃ§Ã£o e estresse merecem atenÃ§Ã£o; considere apoio psicolÃ³gico para mudanÃ§as sustentÃ¡veis."

    return {
        "bmi": bmi,
        "bmi_category": bmi_category,
        "recommended_water": recommended_water,
        "water_status": water_status,
        "bristol": bristol_text,
        "urine": urine_text,
        "sign_hint": sign_hint,
        "mental_notes": mental_notes,
        # Include the raw water consumption so charts can display both consumption and recommendation
        "consumption": float(water) if water else 0,
    }

def generate_dashboard_charts(insights: Dict[str, Any]) -> Dict[str, Figure]:
    """Generate matplotlib figures for the dashboard.

    Currently generates two bar charts: one for BMI categories and one for water
    consumption versus recommendation.

    Parameters
    ----------
    insights : dict
        The insights computed by ``compute_insights``.

    Returns
    -------
    dict
        A dictionary mapping chart names to matplotlib Figure objects.
    """
    charts: Dict[str, Figure] = {}
    # BMI bar chart
    bmi = insights.get("bmi")
    if bmi is not None:
        fig_bmi, ax_bmi = plt.subplots(figsize=(5, 3))
        ax_bmi.barh([0], [bmi], height=0.5)
        ax_bmi.set_xlabel("IMC")
        ax_bmi.set_yticks([])
        ax_bmi.set_title("Ãndice de Massa Corporal (IMC)")
        ax_bmi.axvline(18.5, color="gray", linestyle="--", linewidth=1)
        ax_bmi.axvline(25, color="gray", linestyle="--", linewidth=1)
        ax_bmi.axvline(30, color="gray", linestyle="--", linewidth=1)
        ax_bmi.text(17, 0.3, "Abaixo", fontsize=8)
        ax_bmi.text(20.5, 0.3, "Normal", fontsize=8)
        ax_bmi.text(27.5, 0.3, "Sobrepeso", fontsize=8)
        ax_bmi.text(33, 0.3, "Obesidade", fontsize=8)
        ax_bmi.set_xlim(10, 40)
        charts["bmi"] = fig_bmi
    # Water bar chart
    recommended = insights.get("recommended_water", 0)
    consumption = insights.get("consumption", 0)
    fig_water, ax_water = plt.subplots(figsize=(5, 3))
    ax_water.bar(["Recomendado", "VocÃª"], [recommended, consumption])
    ax_water.set_title("Consumo de Ã¡gua (litros)")
    ax_water.set_ylabel("Litros")
    charts["water"] = fig_water
    return charts

def create_dashboard_pdf(data: Dict[str, Any], insights: Dict[str, Any], charts: Dict[str, Figure], out_path: str) -> None:
    """Create a PDF report of the dashboard.

    This function assembles a PDF document summarising the user's insights and
    embedding the provided chart figures.  The document uses ReportLab's
    platypus API to structure paragraphs and images.

    Parameters
    ----------
    data : dict
        Original user data dictionary.
    insights : dict
        Derived metrics from ``compute_insights``.
    charts : dict
        Chart figures generated by ``generate_dashboard_charts``.
    out_path : str
        File path to save the resulting PDF.
    """
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    styles = getSampleStyleSheet()
    flow: list = []
    # Title
    flow.append(Paragraph("RelatÃ³rio de Insights NutriSigno", styles["Title"]))
    flow.append(Spacer(1, 12))
    # User basic info
    name = data.get("nome", "UsuÃ¡rio")
    sign = data.get("signo", "")
    flow.append(Paragraph(f"Nome: {name}", styles["Normal"]))
    if sign:
        flow.append(Paragraph(f"Signo: {sign}", styles["Normal"]))
    flow.append(Spacer(1, 12))
    # Insights table
    table_data = [
        ["MÃ©trica", "Valor"],
        ["IMC", f"{insights.get('bmi'):.2f}" if insights.get("bmi") else "n/a"],
        ["Categoria IMC", insights.get("bmi_category", "")],
        ["Consumo de Ã¡gua recomendado", f"{insights.get('recommended_water'):.2f} L"],
        ["Status de HidrataÃ§Ã£o", insights.get("water_status", "")],
        ["Escala de Bristol", insights.get("bristol", "")],
        ["Cor da Urina", insights.get("urine", "")],
        ["Dica do signo", insights.get("sign_hint", "")],
        ["Nota psicolÃ³gica", insights.get("mental_notes", "")],
    ]
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#000000')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDBDBD')),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 12))
    # Charts
    for name, fig in charts.items():
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        flow.append(RLImage(buf, width=400, height=240))
        flow.append(Spacer(1, 12))
    # Build document
    doc.build(flow)

def create_share_image(insights: Dict[str, Any], charts: Dict[str, Figure], out_path: str) -> None:
    """Create a single image suitable for sharing on social media that summarises key insights."""
    # For brevity this function assembles a simple composite using matplotlib
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    # BMI gauge
    bmi = insights.get("bmi") or 0
    axes[0].barh([0], [bmi], height=0.5)
    axes[0].set_xlim(10, 40)
    axes[0].set_title("IMC")
    # Water bar
    recommended = insights.get("recommended_water", 0)
    consumption = insights.get("consumption", 0)
    axes[1].bar(["Rec.", "VocÃª"], [recommended, consumption])
    axes[1].set_title("Ãgua (L)")
    plt.tight_layout()
    fig.savefig(out_path, format='png')
    plt.close(fig)