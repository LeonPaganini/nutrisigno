from agents import orchestrator, diet_loader


def _sample_user():
    return {
        "sexo": "Feminino",
        "idade": 32,
        "altura_cm": 165,
        "peso_kg": 62,
        "nivel_atividade": "Moderado",
        "objetivo": "Manutenção",
        "restricoes": "",
    }


def test_calcular_meta_calorica_and_macros():
    user = _sample_user()
    meta = orchestrator.calcular_meta_calorica(user)
    macros = orchestrator.calcular_macros(user["peso_kg"], meta)

    assert meta > 0
    assert macros.kcal == meta
    assert macros.proteina_g > 0
    assert macros.carbo_g > 0


def test_gerar_plano_pre_pagamento_payload():
    plano = orchestrator.gerar_plano_pre_pagamento(_sample_user())

    assert plano["status"] == "aguardando_pagamento"
    assert "porcoes_por_refeicao" in plano and plano["porcoes_por_refeicao"]
    assert plano["dieta_pdf_kcal"] in diet_loader.SUPPORTED_KCALS
    assert plano["macros"]["kcal"] > 0
