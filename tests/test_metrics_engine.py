"""Tests for the NutriSigno metrics engine."""

from modules.metrics_engine import calcular_pilares


def test_calcular_pilares_with_balanced_answers_returns_high_scores():
    respostas = {
        "nivel_energia": "Alta",
        "horas_sono": 8,
        "qualidade_sono": "Alta",
        "freq_atividade_fisica": "4-5x por semana",
        "nivel_estresse": "Baixa",
        "tipo_fezes": "Tipo 4 (Salsicha lisa e macia)",
        "freq_intestino": "2x por dia",
        "freq_inchaco": "Raramente",
        "freq_gases": "Raramente",
        "sensacao_peso_pos_refeicao": "Raramente",
        "despertares_noturnos": 0,
        "dificuldade_para_dormir": "Raramente",
        "sensacao_ao_acordar": "Disposta",
        "qtd_copos_agua": 10,
        "cor_urina": "Amarelo claro",
        "retencao_liquidos": "Raramente",
        "fome_emocional": "Raramente",
        "compulsao_alimentar": "Nunca",
        "culpa_apos_comer": "Raramente",
        "freq_pular_refeicoes": "Raramente",
        "refeicoes_no_dia": 4,
        "aderencia_plano_alimentar": "Sigo quase sempre",
        "variacao_rotina_fim_de_semana": "Muda um pouco",
    }

    scores = calcular_pilares(respostas)

    for pillar, score in scores.items():
        assert score >= 70, f"{pillar} deve refletir bom equilíbrio, recebeu {score}"


def test_calcular_pilares_penaliza_incoerencias_e_sintomas():
    respostas = {
        "nivel_energia": "Muito baixa",
        "horas_sono": 4.5,
        "qualidade_sono": "Muito baixa",
        "freq_atividade_fisica": "Nunca",
        "nivel_estresse": "Muito alta",
        "tipo_fezes": "Tipo 2 (Salsicha grumosa)",
        "freq_intestino": "Menos de 3x por semana",
        "freq_inchaco": "Quase sempre",
        "freq_gases": "Quase sempre",
        "sensacao_peso_pos_refeicao": "Quase sempre",
        "despertares_noturnos": 4,
        "dificuldade_para_dormir": "Quase sempre",
        "sensacao_ao_acordar": "Extremamente cansada",
        "qtd_copos_agua": 3,
        "cor_urina": "Âmbar",
        "retencao_liquidos": "Frequentemente",
        "fome_emocional": "Quase sempre",
        "compulsao_alimentar": "Frequentemente",
        "culpa_apos_comer": "Quase sempre",
        "freq_pular_refeicoes": "Frequentemente",
        "refeicoes_no_dia": 2,
        "aderencia_plano_alimentar": "Sigo quase sempre",
        "variacao_rotina_fim_de_semana": "É totalmente diferente",
    }

    scores = calcular_pilares(respostas)

    assert scores["Energia"] < 40
    assert scores["Sono"] < 45
    assert scores["Digestao"] < 50
    assert scores["Emocao"] < 35
    assert scores["Rotina"] < 50

