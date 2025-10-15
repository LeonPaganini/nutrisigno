"""Geração de relatórios em PDF utilizando ReportLab e Matplotlib.

Este módulo fornece funções para transformar os resultados do modelo
nutricional em um relatório PDF profissional. Utiliza o ReportLab para
montar páginas com textos, tabelas e imagens, e Matplotlib para
plotagem de gráficos de distribuição de macronutrientes.  O conteúdo
foi copiado da versão original do repositório, mantendo compatibilidade
com as alterações realizadas nesta implementação.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import matplotlib.pyplot as plt

def _generate_macros_chart(macros: Dict[str, Any]) -> io.BytesIO:
    """Cria um gráfico de pizza ou barras para a distribuição de macros.

    Args:
        macros: dicionário com chaves 'carboidratos', 'proteinas', 'gorduras'
            e valores em porcentagem.

    Returns:
        BytesIO contendo a imagem PNG do gráfico.
    """
    labels = list(macros.keys())
    sizes = [float(macros.get(k, 0)) for k in labels]
    colors_list = ["#81C784", "#4FC3F7", "#FFD54F"]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors_list)
    ax.axis('equal')  # Assegura que o círculo permaneça circular
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer

def create_pdf_report(user_data: Dict[str, Any], plan_dict: Dict[str, Any], output_path: str) -> None:
    """Gera um relatório em PDF a partir dos dados e salva no caminho fornecido.

    Args:
        user_data: dicionário com informações do usuário.
        plan_dict: dicionário retornado pela OpenAI contendo 'plano',
            'macros', 'insights' e 'perfil_astrologico'.
        output_path: caminho de saída do arquivo PDF.
    """
    # Configuração do documento
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story: List[Any] = []

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"].clone('title')
    title_style.fontSize = 20
    title_style.leading = 24
    title_style.spaceAfter = 12

    normal_style = styles["Normal"].clone('normal')
    normal_style.fontSize = 11
    normal_style.leading = 14

    small_style = ParagraphStyle(
        'small',
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    )

    # Página de título
    story.append(Paragraph("Plano Alimentar Personalizado", title_style))
    story.append(Paragraph(f"Nome: {user_data.get('nome', 'Usuário')} ", normal_style))
    story.append(Paragraph(f"E-mail: {user_data.get('email', '')}", normal_style))
    story.append(Paragraph(f"Signo: {plan_dict.get('perfil_astrologico', {}).get('signo', user_data.get('signo', ''))}", normal_style))
    story.append(Spacer(1, 12))
    perfil = plan_dict.get('perfil_astrologico')
    if perfil:
        story.append(Paragraph("<b>Resumo do Perfil Astrológico:</b>", normal_style))
        if isinstance(perfil, dict):
            # Converte dict para texto amigável
            linhas = [f"<i>{k.title()}</i>: {v}" for k, v in perfil.items()]
            story.append(Paragraph("<br/>".join(linhas), small_style))
        elif isinstance(perfil, str):
            story.append(Paragraph(perfil, small_style))
        story.append(Spacer(1, 12))

    # Tabela do plano alimentar
    plano = plan_dict.get('plano', [])
    if plano:
        story.append(Paragraph("<b>Plano Alimentar:</b>", normal_style))
        # Cabeçalhos
        data_table = [["Refeição", "Descrição", "Alimentos", "Quantidades", "Calorias"]]
        for item in plano:
            refeicao = item.get('refeicao', '')
            descricao = item.get('descricao', '')
            alimentos = ', '.join(item.get('alimentos', []))
            quantidades = ', '.join(item.get('quantidades', []))
            calorias = str(item.get('calorias', ''))
            data_table.append([refeicao, descricao, alimentos, quantidades, calorias])
        table = Table(data_table, repeatRows=1, colWidths=[3 * cm, 4 * cm, 4 * cm, 3 * cm, 2.5 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#000000')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDBDBD')),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    # Gráfico de macros
    macros = plan_dict.get('macros')
    if macros:
        story.append(Paragraph("<b>Distribuição de Macronutrientes:</b>", normal_style))
        chart_buffer = _generate_macros_chart(macros)
        img = Image(chart_buffer, width=8 * cm, height=8 * cm)
        story.append(img)
        story.append(Spacer(1, 12))

    # Insights
    insights = plan_dict.get('insights')
    if insights:
        story.append(Paragraph("<b>Insights Personalizados:</b>", normal_style))
        story.append(Paragraph(insights.replace('\n', '<br/>'), small_style))

    # Constrói o documento
    doc.build(story)