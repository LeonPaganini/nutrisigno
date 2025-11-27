from modules import plan_post_payment


def test_build_template_menu_uses_templates_json():
    catalog = plan_post_payment.load_plan_catalog()
    assert catalog, "catálogo de planos não pode estar vazio"

    plan = catalog[0]
    menu = plan_post_payment.build_template_menu(plan, pac_id="teste-templates")

    assert menu.get("refeicoes"), "cardápio deve conter ao menos uma refeição"
    for refeicao in menu["refeicoes"]:
        assert refeicao.get("refeicao_padrao"), "cada refeição deve ter itens padrão"
        assert isinstance(refeicao.get("opcoes_substituicao"), dict)
