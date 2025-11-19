"""Tests for the NutriSigno metrics engine."""

from modules.metrics_engine import calcular_pilares


def test_calcular_pilares_with_balanced_answers_returns_high_scores():
    respostas = {
        "nivel_energia_dia": "Alta",
        "cansaco_frequente": "Raramente",
        "acorda_cansada": "Disposta",
        "horas_sono_noite": 8,
        "qualidade_sono": "Alta",
        "despertares_noturnos": 0,
        "freq_atividade_fisica": "4-5x por semana",
        "tipo_fezes_bristol": "Tipo 4 (Salsicha lisa e macia)",
        "freq_evacuacao": "2x por dia",
        "freq_inchaco_abdominal": "Raramente",
        "copos_agua_dia": 10,
        "cor_urina": "Amarelo muito claro",
        "retencao_inchaco": "Raramente",
        "fome_emocional": "Raramente",
        "compulsao_alimentar": "Nunca",
        "culpa_apos_comer": "Raramente",
        "freq_pular_refeicoes": "Raramente",
        "refeicoes_por_dia": 4,
        "constancia_fim_de_semana": "Quase não muda",
    }

    scores = calcular_pilares(respostas)

    for pillar, score in scores.items():
        assert score is not None
        assert score >= 70, f"{pillar} deve refletir bom equilíbrio, recebeu {score}"


def test_calcular_pilares_penaliza_incoerencias_e_sintomas():
    respostas = {
        "nivel_energia_dia": "Muito baixa",
        "cansaco_frequente": "Quase sempre",
        "acorda_cansada": "Extremamente cansada",
        "horas_sono_noite": 4.5,
        "qualidade_sono": "Muito baixa",
        "freq_atividade_fisica": "Nunca",
        "tipo_fezes_bristol": "Tipo 2 (Salsicha grumosa)",
        "freq_evacuacao": "Menos de 3x por semana",
        "freq_inchaco_abdominal": "Quase sempre",
        "despertares_noturnos": 4,
        "copos_agua_dia": 3,
        "cor_urina": "Âmbar",
        "retencao_inchaco": "Frequentemente",
        "fome_emocional": "Quase sempre",
        "compulsao_alimentar": "Frequentemente",
        "culpa_apos_comer": "Quase sempre",
        "freq_pular_refeicoes": "Frequentemente",
        "refeicoes_por_dia": 2,
        "constancia_fim_de_semana": "É totalmente diferente",
    }

    scores = calcular_pilares(respostas)

    assert scores["Energia"] is not None and scores["Energia"] < 40
    assert scores["Sono"] is not None and scores["Sono"] < 45
    assert scores["Digestao"] is not None and scores["Digestao"] < 50
    assert scores["Emocao"] is not None and scores["Emocao"] < 35
    assert scores["Rotina"] is not None and scores["Rotina"] < 50


def test_calcular_pilares_retorna_none_sem_respostas():
    scores = calcular_pilares({})
    assert all(value is None for value in scores.values())


def test_calcular_pilares_aceita_chaves_antigas():
    respostas = {
        "nivel_energia": "Moderada",
        "sensacao_ao_acordar": "Neutra",
        "tipo_fezes": "Tipo 4 (Salsicha lisa e macia)",
        "freq_intestino": "1x por dia",
        "freq_inchaco": "Raramente",
        "horas_sono": 7.5,
        "qtd_copos_agua": 9,
        "retencao_liquidos": "Raramente",
        "refeicoes_no_dia": 3,
        "variacao_rotina_fim_de_semana": "Muda um pouco",
    }

    scores = calcular_pilares(respostas)
    assert any(value is not None for value in scores.values())

