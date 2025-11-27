from __future__ import annotations

from agents.cardapio_builder import build_cardapio
from agents.subs_loader import load_substitutions


def _dummy_pre_plano() -> dict:
    return {
        "dados_usuario": {"nome": "Ana"},
        "signo": "Libra",
        "perfil_astrologico_resumido": "equilíbrio e foco",  # noqa: RUF001
        "kcal_alvo": 2000,
        "porcoes_por_refeicao": {
            "Desjejum": {
                "Carboidratos": "2 porções",
                "Fruta": "1 porção",
                "Laticínio magro": "1 porção",
                "Gordura": "1 porção",
            },
            "Almoço": {
                "Proteína Baixo Teor de Gordura": "1 porção",
                "Carboidrato": "1 porção",
                "Vegetais e Hortaliças": "2 porções",
                "Fruta": "1 porção",
            },
        },
    }


def test_cardapio_builds_all_meals_and_portions():
    substituicoes = load_substitutions()
    cardapio = build_cardapio(_dummy_pre_plano(), substituicoes)

    assert "cardapio_dia" in cardapio
    refeicoes = cardapio["cardapio_dia"]["refeicoes"]
    assert len(refeicoes) == 2

    desjejum = next(r for r in refeicoes if r["nome_refeicao"] == "Desjejum")
    grupos = {}
    for item in desjejum["refeicao_padrao"]:
        grupos.setdefault(item["categoria_porcoes"], 0)
        grupos[item["categoria_porcoes"]] += item["porcoes_equivalentes"]

    assert grupos["Carboidratos"] == 2
    assert grupos["Fruta"] == 1
    assert "comentario_astrologico" in desjejum
    assert desjejum["opcoes_substituicao"]["Carboidratos"]


def test_cardapio_handles_fallback_when_missing_categories():
    substituicoes = load_substitutions()
    plano = _dummy_pre_plano()
    plano["porcoes_por_refeicao"]["Ceia"] = {"Proteina": "1 porção", "Vegetais": "1 porção"}

    cardapio = build_cardapio(plano, substituicoes)
    refeicoes = cardapio["cardapio_dia"]["refeicoes"]
    ceia = next(r for r in refeicoes if r["nome_refeicao"] == "Ceia")

    categorias = {item["categoria_porcoes"] for item in ceia["refeicao_padrao"]}
    assert "Proteina" in categorias
    assert "Vegetais" in categorias
    assert ceia["opcoes_substituicao"]["Proteina"]
