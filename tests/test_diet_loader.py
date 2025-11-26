from agents import diet_loader


def test_select_kcal_alvo_respects_bounds():
    assert diet_loader.select_kcal_alvo(950) == 1000
    assert diet_loader.select_kcal_alvo(2050) == 2000


def test_select_kcal_alvo_picks_closest():
    assert diet_loader.select_kcal_alvo(1135) == 1100
    assert diet_loader.select_kcal_alvo(1875) == 1900


def test_get_diet_returns_entry_from_catalog():
    kcal_base, diet = diet_loader.get_diet(1420)
    assert kcal_base in diet_loader.SUPPORTED_KCALS
    assert diet.refeicoes_por_porcoes
    assert diet_loader.get_pdf_filename(1420)[1]
