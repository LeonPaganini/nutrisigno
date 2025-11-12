from modules.plan_post_payment import (
    PlanDefinition,
    compute_target_kcal,
    generate_combos,
    prepare_substitutions,
    select_plan,
)


def _sample_catalog():
    return {
        "source": "LISTA_DE_SUBSTITUICAO_FINAL.pdf",
        "observacao": "Todas as porções equivalentes.",
        "normalized": {
            "carboidratos_e_derivados": {
                "categoria": "Carboidratos e derivados",
                "descricao": "Grupo de pães, massas e cereais.",
                "itens": [
                    {"nome": "Arroz integral", "porcao": "3 colheres"},
                    {"nome": "Quinoa", "porcao": "3 colheres"},
                ],
            },
            "proteina_animal_baixo_gordura": {
                "categoria": "Proteína animal — baixo teor de gordura",
                "descricao": "Carnes magras e aves sem pele.",
                "itens": [
                    {"nome": "Frango grelhado", "porcao": "120 g"},
                    {"nome": "Tilápia", "porcao": "120 g"},
                ],
            },
            "vegetais_livres": {
                "categoria": "Vegetais livres",
                "descricao": "Verduras e legumes crus ou cozidos.",
                "itens": [
                    {"nome": "Brócolis", "porcao": "à vontade"},
                    {"nome": "Couve", "porcao": "à vontade"},
                ],
            },
            "frutas_frescas": {
                "categoria": "Frutas frescas",
                "descricao": "Frutas in natura ou picadas.",
                "itens": [
                    {"nome": "Maçã", "porcao": "1 unidade"},
                    {"nome": "Mamão", "porcao": "1 fatia"},
                ],
            },
            "gorduras": {
                "categoria": "Gorduras boas",
                "descricao": "Óleos, sementes e castanhas.",
                "itens": [
                    {"nome": "Azeite de oliva", "porcao": "1 colher"},
                    {"nome": "Castanhas", "porcao": "1 punhado"},
                ],
            },
            "laticinios_magros": {
                "categoria": "Laticínios magros",
                "descricao": "Iogurtes e queijos com baixo teor de gordura.",
                "itens": [
                    {"nome": "Iogurte natural", "porcao": "1 copo"},
                    {"nome": "Queijo minas", "porcao": "1 fatia"},
                ],
            },
        },
    }


def test_compute_target_kcal_treinado_ganho():
    target, faixa = compute_target_kcal(70, "ganhar", True)
    assert target == 2660
    assert faixa == (36, 40, 38)


def test_select_plan_tiebreak_by_goal():
    catalog = [
        PlanDefinition(kcal=1600, arquivo="a.pdf", refeicoes_por_porcoes={}),
        PlanDefinition(kcal=1700, arquivo="b.pdf", refeicoes_por_porcoes={}),
    ]
    plan_cut = select_plan(1650, "emagrecer", catalog)
    assert plan_cut.kcal == 1600
    plan_bulk = select_plan(1650, "ganhar", catalog)
    assert plan_bulk.kcal == 1700


def test_prepare_substitutions_and_combos():
    plan = PlanDefinition(
        kcal=1700,
        arquivo="plan1700.pdf",
        refeicoes_por_porcoes={
            "Desjejum": {
                "Carboidratos": "2 porções",
                "Laticínio magro": "1 porção",
                "Fruta": "1 porção",
            },
            "Almoço": {
                "Carboidrato": "2 porções",
                "Proteína Baixo Teor de Gordura": "1 porção",
                "Vegetais e Hortaliças": "2 porções",
                "Gordura": "1 porção",
            },
            "Jantar": {
                "Carboidrato": "1 porção",
                "Proteína Baixo Teor de Gordura": "1 porção",
                "Vegetais e Hortaliças": "2 porções",
            },
        },
    )
    catalog = _sample_catalog()
    public_data, lookup = prepare_substitutions(plan, catalog)

    assert public_data["categorias"]
    categorias = {c["categoria"] for c in public_data["categorias"]}
    assert "Carboidratos e derivados" in categorias
    assert "Laticínios magros" in categorias

    combos = generate_combos(plan, lookup, "abc123")
    refeicoes = [c.get("refeicao") for c in combos["combos"]]
    assert refeicoes.count("desjejum") == 2
    assert refeicoes.count("almoço") == 2
    assert refeicoes.count("jantar") == 2
