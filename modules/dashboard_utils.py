"""Utilities for generating health insights and dashboards.

This module contains helper functions to compute derived insights from the
user's raw input data, generate charts with matplotlib for interactive
display in Streamlit, and produce exportable artefacts such as PDF reports
and shareable images. The focus is on presenting health and nutrition
information in an engaging way while respecting evidence‑based guidance.

Guidelines implemented here are informed by the project's ethos: use
astrology solely as an inspirational lens and never as a replacement for
professional medical or nutritional advice【816008315108607†L388-L390】.  All
health recommendations are anchored in nutritional science; zodiac
annotations act only as behavioural nudges.

Functions
---------
compute_insights(data: dict) -> dict
    Calculate derived metrics such as BMI, hydration status and interpret
    the Bristol stool scale and urine colour selections. Also attach
    astrological hints when available.

generate_dashboard_charts(insights: dict) -> dict
    Build matplotlib figures representing the insights (BMI and water
    consumption) and return them in a dictionary for easy rendering in
    Streamlit.

create_dashboard_pdf(data: dict, insights: dict, charts: dict, out_path: str) -> None
    Generate a PDF summarising the insights and embedding chart images.

create_share_image(insights: dict, charts: dict, out_path: str) -> None
    Create a single image suitable for sharing on social media that
    summarises key insights.
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
from reportlab.platypus import (Image as RLImage, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

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
        return "Excelente, você está bem hidratado(a)!"
    if 0.8 <= ratio < 1.0:
        return "Bom, porém você pode aumentar um pouco a ingestão de água."
    return "Atenção: aumente o consumo de água para evitar desidratação."


def _interpret_bristol(selection: str) -> str:
    """Interpret the Bristol stool scale selection into a concise description."""
    # Mapping based on common clinical interpretations
    mapping = {
        1: "Fezes muito duras, indicar possível constipação e baixa ingestão de fibras.",
        2: "Fezes duras, sinal de constipação e necessidade de mais fibras e água.",
        3: "Fezes com fissuras, indicam tendência à constipação; aumentar fibras e líquidos.",
        4: "Fezes normais, consistência saudável.",
        5: "Fezes moles, podem indicar alimentação leve ou possível intolerância alimentar.",
        6: "Fezes pastosas, sugerem possível diarreia ou intolerância; consulte um profissional se persistir.",
        7: "Fezes líquidas, sinal de diarreia; hidrate‑se e procure atendimento se necessário."
    }
    # Extract leading number from selection string
    try:
        num = int(selection.split(" ")[1]) if selection.startswith("Tipo") else int(selection.split("-")[0])
    except Exception:
        return "Não foi possível interpretar o tipo de fezes."
    return mapping.get(num, "Tipo de fezes desconhecido.")


def _interpret_urine(selection: str) -> str:
    """Interpret urine colour selection into hydration advice."""
    if "Transparente" in selection or "Amarelo muito claro" in selection:
        return "Excelente hidratação! Mantenha o consumo de água."
    if "Amarelo claro" in selection or "Amarelo" in selection:
        return "Hidratação moderada; aumente sua ingestão de água."
    if "Amarelo escuro" in selection:
        return "Atenção! Possível desidratação; beba mais água." 
    return "Perigo extremo! Procure atendimento médico; você está muito desidratado(a)."


def _sign_hints() -> Dict[str, str]:
    """Return behavioural hints by zodiac sign for nutrition adherence."""
    return {
        "Áries": "Evite decisões impulsivas: planeje suas refeições e escolha opções saciantes.",
        "Touro": "Valorize a qualidade, evitando excessos; comidas prazerosas podem ser saudáveis.",
        "Gêmeos": "Varie os alimentos para evitar tédio e mantenha refeições regulares.",
        "Câncer": "Prefira refeições leves e frequentes para evitar desconfortos gástricos.",
        "Leão": "Evite exagerar para impressionar; busque equilíbrio e moderação.",
        "Virgem": "Mantenha uma rotina organizada, preparando refeições caseiras sempre que possível.",
        "Libra": "Planeje seu cardápio semanal para reduzir indecisão e escolhas de última hora.",
        "Escorpião": "Evite extremos alimentares; consuma porções controladas e variadas.",
        "Sagitário": "Cuidado com o entusiasmo excessivo: busque equilíbrio entre prazer e nutrição.",
        "Capricórnio": "Estabeleça pausas alimentares e evite rigidez excessiva; permita pequenas indulgências.",
        "Aquário": "Experimente novos ingredientes, mas mantenha constância e variedade.",
        "Peixes": "Escute seu corpo e hidrate‑se; refeições intuitivas podem ajudar na saciedade."
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

    bmi = None
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
            mental_notes = "Você está motivado(a) e com baixo estresse, ótimo cenário para mudanças!"
        elif motivacao >= 4 and estresse > 2:
            mental_notes = "Alta motivação, mas com estresse; tente técnicas de relaxamento para manter o foco."
        elif motivacao < 4 and estresse <= 2:
            mental_notes = "Você tem baixa motivação, mas baixo estresse; busque fontes de inspiração para engajar."
        else:
            mental_notes = "Motivação e estresse merecem atenção; considere apoio psicológico para mudanças sustentáveis."

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
        # Define ranges for normal categories
        categories = ["Abaixo", "Normal", "Sobrepeso", "Obesidade"]
        bounds = [18.5, 25, 30]
        # Plot user BMI as a bar on a continuum
        ax_bmi.barh([0], [bmi], height=0.5)
        ax_bmi.set_xlabel("IMC")
        ax_bmi.set_yticks([])
        ax_bmi.set_title("Índice de Massa Corporal (IMC)")
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
    ax_water.bar(["Recomendado", "Você"], [recommended, consumption])
    ax_water.set_title("Consumo de água (litros)")
    ax_water.set_ylabel("Litros")
    charts["water"] = fig_water
    return charts


def create_dashboard_pdf(data: Dict[str, Any], insights: Dict[str, Any], charts: Dict[str, Figure], out_path: str) -> None:
    """Create a PDF report of the dashboard.

    This function assembles a PDF document summarising the user's insights and
    embedding the provided chart figures. The document uses ReportLab's
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
    flow.append(Paragraph("Relatório de Insights NutriSigno", styles["Title"]))
    flow.append(Spacer(1, 12))
    # User basic info
    name = data.get("nome", "Usuário")
    sign = data.get("signo", "")
    flow.append(Paragraph(f"Nome: {name}", styles["Normal"]))
    if sign:
        flow.append(Paragraph(f"Signo: {sign}", styles["Normal"]))
    flow.append(Spacer(1, 12))
    # Insights table
    table_data = [
        ["Métrica", "Valor"],
        ["IMC", f"{insights.get('bmi'):.2f}" if insights.get("bmi") else "n/a"],
        ["Categoria IMC", insights.get("bmi_category", "")],
        ["Consumo de água recomendado", f"{insights.get('recommended_water'):.2f} L"],
        ["Status de Hidratação", insights.get("water_status", "")],
        ["Escala de Bristol", insights.get("bristol", "")],
        ["Cor da Urina", insights.get("urine", "")],
        ["Nota mental", insights.get("mental_notes", "")],
    ]
    table = Table(table_data, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 12))
    # Astrological hint
    if insights.get("sign_hint"):
        flow.append(Paragraph(f"Dica do signo: {insights['sign_hint']}", styles["Italic"]))
        flow.append(Spacer(1, 12))
    # Insert charts as images
    for name, fig in charts.items():
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        rl_img = RLImage(buf, width=400, height=250)
        flow.append(rl_img)
        flow.append(Spacer(1, 12))
    doc.build(flow)


def create_share_image(insights: Dict[str, Any], charts: Dict[str, Figure], out_path: str) -> None:
    """Create a shareable image summarising key insights for social media.

    The image combines a short summary of the main metrics with one of the
    charts (BMI bar chart) to create an aesthetically pleasing visual for
    platforms like Instagram. The resulting PNG is saved to `out_path`.
    """
    # Choose the BMI chart if available
    fig = charts.get("bmi")
    if fig is None:
        # Fallback: create a blank figure with summary only
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.axis('off')
    # Create a new figure onto which we draw summary text and the chosen chart
    share_fig = plt.figure(figsize=(8, 8))
    gs = share_fig.add_gridspec(2, 1, height_ratios=[1, 1.5])
    # Top cell: summary text
    ax_top = share_fig.add_subplot(gs[0, 0])
    ax_top.axis('off')
    lines = []
    bmi = insights.get("bmi")
    if bmi is not None:
        lines.append(f"IMC: {bmi:.1f} ({insights.get('bmi_category')})")
    lines.append(f"Água recomendada: {insights.get('recommended_water'):.1f} L")
    lines.append(f"Hidratação: {insights.get('water_status')}")
    lines.append(f"Bristol: {insights.get('bristol')}")
    lines.append(f"Urina: {insights.get('urine')}")
    if insights.get("sign_hint"):
        lines.append(f"Dica astrológica: {insights.get('sign_hint')}")
    text = "\n".join(lines)
    ax_top.text(0.5, 0.5, text, fontsize=10, ha='center', va='center', wrap=True)
    # Bottom cell: embed BMI chart
    ax_bottom = share_fig.add_subplot(gs[1, 0])
    if fig is not None:
        # Draw the existing BMI figure onto the bottom axis by redrawing its artists
        for artist in fig.get_axes()[0].get_children():
            try:
                artist_fig = artist.figure
            except Exception:
                continue
            # We'll skip original figure's axes backgrounds; draw replicates using original artists' properties
        # Instead of trying to replicate artists, simply re‑plot the bar for share image
        bmi_value = insights.get("bmi") or 0
        ax_bottom.barh([0], [bmi_value], height=0.5)
        ax_bottom.set_yticks([])
        ax_bottom.set_xlabel("IMC")
        ax_bottom.set_title("Seu IMC")
        ax_bottom.axvline(18.5, color="gray", linestyle="--", linewidth=1)
        ax_bottom.axvline(25, color="gray", linestyle="--", linewidth=1)
        ax_bottom.axvline(30, color="gray", linestyle="--", linewidth=1)
        ax_bottom.set_xlim(10, 40)
    ax_bottom.text(17, 0.3, "Abaixo", fontsize=8)
    ax_bottom.text(20.5, 0.3, "Normal", fontsize=8)
    ax_bottom.text(27.5, 0.3, "Sobrepeso", fontsize=8)
    ax_bottom.text(33, 0.3, "Obesidade", fontsize=8)
    share_fig.tight_layout()
    share_fig.savefig(out_path, format='png')