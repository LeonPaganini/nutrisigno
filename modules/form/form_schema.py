"""Central form schema describing NutriSigno's six pillars questions."""

from __future__ import annotations

from typing import Dict, List


FREQUENCY_5 = [
    "Nunca",
    "Raramente",
    "Às vezes",
    "Frequentemente",
    "Quase sempre",
]

INTENSITY_5 = [
    "Muito baixa",
    "Baixa",
    "Moderada",
    "Alta",
    "Muito alta",
]

ACTIVITY_OPTIONS = [
    "Nunca",
    "1x por semana",
    "2-3x por semana",
    "4-5x por semana",
    "Diariamente",
]

BRISTOL_OPTIONS = [
    "Tipo 1 (Carocinhos duros)",
    "Tipo 2 (Salsicha grumosa)",
    "Tipo 3 (Salsicha com rachaduras)",
    "Tipo 4 (Salsicha lisa e macia)",
    "Tipo 5 (Pedaços macios)",
    "Tipo 6 (Pedaços fofos)",
    "Tipo 7 (Aquosa)",
]

URINE_COLOR_OPTIONS = [
    "Transparente",
    "Amarelo muito claro",
    "Amarelo claro",
    "Amarelo",
    "Âmbar",
    "Muito escura",
]

WEEKEND_CONSTANCY = [
    "Quase não muda",
    "Muda um pouco",
    "Muda bastante",
    "É totalmente diferente",
]


FORM_SCHEMA = [
    {
        "pilar": "Energia",
        "descricao": "Avalia como a pessoa sente e recupera energia diariamente.",
        "perguntas": [
            {
                "id": "nivel_energia_dia",
                "label": "Como você avalia seu nível de energia ao longo do dia?",
                "descricao": "Captura a percepção geral de energia. Pilar: Energia.",
                "tipo_campo": "select",
                "opcoes": INTENSITY_5,
                "valor_padrao": "Moderada",
                "pilares_relacionados": ["Energia"],
            },
            {
                "id": "cansaco_frequente",
                "label": "Com que frequência você se sente cansada ao longo do dia?",
                "descricao": "Mapeia episódios de fadiga recorrente. Pilar: Energia.",
                "tipo_campo": "select",
                "opcoes": FREQUENCY_5,
                "valor_padrao": "Às vezes",
                "pilares_relacionados": ["Energia"],
            },
            {
                "id": "acorda_cansada",
                "label": "Como você costuma se sentir ao acordar?",
                "descricao": "Indica recuperação durante a noite. Pilar: Energia.",
                "tipo_campo": "select",
                "opcoes": [
                    "Extremamente cansada",
                    "Cansada",
                    "Neutra",
                    "Disposta",
                    "Muito disposta",
                ],
                "valor_padrao": "Neutra",
                "pilares_relacionados": ["Energia", "Sono"],
            },
        ],
    },
    {
        "pilar": "Digestão",
        "descricao": "Investiga qualidade das fezes, gases e evacuação.",
        "perguntas": [
            {
                "id": "tipo_fezes_bristol",
                "label": "Qual tipo de fezes representa melhor seu padrão (Escala de Bristol)?",
                "descricao": "Consistência intestinal diretamente ligada à digestão.",
                "tipo_campo": "radio",
                "opcoes": BRISTOL_OPTIONS,
                "valor_padrao": BRISTOL_OPTIONS[3],
                "pilares_relacionados": ["Digestao"],
            },
            {
                "id": "freq_inchaco_abdominal",
                "label": "Com que frequência você sente inchaço abdominal?",
                "descricao": "Sintoma digestivo relevante. Pilar: Digestão.",
                "tipo_campo": "select",
                "opcoes": FREQUENCY_5,
                "valor_padrao": "Às vezes",
                "pilares_relacionados": ["Digestao"],
            },
            {
                "id": "freq_evacuacao",
                "label": "Com que frequência você evacua?",
                "descricao": "Ritmo intestinal completo. Pilar: Digestão.",
                "tipo_campo": "select",
                "opcoes": [
                    "Menos de 3x por semana",
                    "3-4x por semana",
                    "1x por dia",
                    "2x por dia",
                    "3 ou mais vezes por dia",
                ],
                "valor_padrao": "1x por dia",
                "pilares_relacionados": ["Digestao"],
            },
        ],
    },
    {
        "pilar": "Sono",
        "descricao": "Observa quantidade e qualidade do sono noturno.",
        "perguntas": [
            {
                "id": "horas_sono_noite",
                "label": "Quantas horas de sono você costuma ter por noite?",
                "descricao": "Duração média do sono. Pilar: Sono.",
                "tipo_campo": "slider",
                "config": {"min": 4.0, "max": 11.0, "step": 0.5},
                "valor_padrao": 7.0,
                "pilares_relacionados": ["Sono"],
            },
            {
                "id": "qualidade_sono",
                "label": "Como você avalia a qualidade do seu sono?",
                "descricao": "Percepção subjetiva de descanso. Pilar: Sono.",
                "tipo_campo": "select",
                "opcoes": INTENSITY_5,
                "valor_padrao": "Moderada",
                "pilares_relacionados": ["Sono"],
            },
            {
                "id": "despertares_noturnos",
                "label": "Quantas vezes você acorda durante a noite?",
                "descricao": "Fragmentação do sono. Pilar: Sono.",
                "tipo_campo": "slider",
                "config": {"min": 0, "max": 6, "step": 1},
                "valor_padrao": 1,
                "pilares_relacionados": ["Sono"],
            },
        ],
    },
    {
        "pilar": "Hidratação",
        "descricao": "Avalia ingestão hídrica e indicadores visuais.",
        "perguntas": [
            {
                "id": "copos_agua_dia",
                "label": "Quantos copos de 200 ml de água você bebe por dia?",
                "descricao": "Volume diário consumido. Pilar: Hidratação.",
                "tipo_campo": "slider",
                "config": {"min": 0, "max": 20, "step": 1},
                "valor_padrao": 8,
                "pilares_relacionados": ["Hidratacao"],
            },
            {
                "id": "cor_urina",
                "label": "Qual a cor predominante da sua urina?",
                "descricao": "Indicador indireto de hidratação. Pilar: Hidratação.",
                "tipo_campo": "select",
                "opcoes": URINE_COLOR_OPTIONS,
                "valor_padrao": URINE_COLOR_OPTIONS[1],
                "pilares_relacionados": ["Hidratacao"],
            },
            {
                "id": "retencao_inchaco",
                "label": "Com que frequência percebe retenção de líquidos ou inchaço?",
                "descricao": "Monitora edema associado à hidratação. Pilar: Hidratação.",
                "tipo_campo": "select",
                "opcoes": FREQUENCY_5,
                "valor_padrao": "Raramente",
                "pilares_relacionados": ["Hidratacao"],
            },
        ],
    },
    {
        "pilar": "Emoção",
        "descricao": "Foca em relação emocional com a alimentação.",
        "perguntas": [
            {
                "id": "fome_emocional",
                "label": "Com que frequência você come para aliviar emoções?",
                "descricao": "Indica gatilhos emocionais. Pilar: Emoção.",
                "tipo_campo": "select",
                "opcoes": FREQUENCY_5,
                "valor_padrao": "Às vezes",
                "pilares_relacionados": ["Emocao"],
            },
            {
                "id": "compulsao_alimentar",
                "label": "Com que frequência sente episódios de compulsão alimentar?",
                "descricao": "Avalia perda de controle alimentar. Pilar: Emoção.",
                "tipo_campo": "select",
                "opcoes": FREQUENCY_5,
                "valor_padrao": "Raramente",
                "pilares_relacionados": ["Emocao"],
            },
            {
                "id": "culpa_apos_comer",
                "label": "Com que frequência sente culpa após comer?",
                "descricao": "Registra impacto emocional pós-refeição. Pilar: Emoção.",
                "tipo_campo": "select",
                "opcoes": FREQUENCY_5,
                "valor_padrao": "Às vezes",
                "pilares_relacionados": ["Emocao"],
            },
        ],
    },
    {
        "pilar": "Rotina",
        "descricao": "Mapeia constância alimentar e atividade física.",
        "perguntas": [
            {
                "id": "refeicoes_por_dia",
                "label": "Quantas refeições completas você costuma fazer por dia?",
                "descricao": "Frequência alimentar diária. Pilar: Rotina.",
                "tipo_campo": "slider",
                "config": {"min": 1, "max": 7, "step": 1},
                "valor_padrao": 4,
                "pilares_relacionados": ["Rotina"],
            },
            {
                "id": "freq_pular_refeicoes",
                "label": "Com que frequência você pula refeições?",
                "descricao": "Estabilidade alimentar. Pilar: Rotina.",
                "tipo_campo": "select",
                "opcoes": FREQUENCY_5,
                "valor_padrao": "Raramente",
                "pilares_relacionados": ["Rotina"],
            },
            {
                "id": "constancia_fim_de_semana",
                "label": "Como sua rotina alimentar muda nos fins de semana?",
                "descricao": "Comparação semana vs. fim de semana. Pilar: Rotina.",
                "tipo_campo": "select",
                "opcoes": WEEKEND_CONSTANCY,
                "valor_padrao": WEEKEND_CONSTANCY[1],
                "pilares_relacionados": ["Rotina"],
            },
            {
                "id": "freq_atividade_fisica",
                "label": "Com que frequência pratica atividade física estruturada?",
                "descricao": "Revela constância de movimento. Pilar: Rotina.",
                "tipo_campo": "select",
                "opcoes": ACTIVITY_OPTIONS,
                "valor_padrao": ACTIVITY_OPTIONS[2],
                "pilares_relacionados": ["Rotina", "Energia"],
            },
        ],
    },
]

FORM_QUESTION_INDEX: Dict[str, Dict[str, object]] = {
    question["id"]: question
    for section in FORM_SCHEMA
    for question in section["perguntas"]
}

__all__ = [
    "ACTIVITY_OPTIONS",
    "BRISTOL_OPTIONS",
    "FORM_QUESTION_INDEX",
    "FORM_SCHEMA",
    "FREQUENCY_5",
    "INTENSITY_5",
    "URINE_COLOR_OPTIONS",
    "WEEKEND_CONSTANCY",
]
