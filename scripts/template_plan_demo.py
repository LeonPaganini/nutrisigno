from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from modules.nutrisigno_refeicoes import (
    SLOT_TO_CATEGORIES,
    carregar_substituicoes,
    carregar_templates,
    obter_template_por_id,
)

TEMPLATE_CHOICES: Dict[str, str] = {
    "Desjejum": "Desjejum5",
    "Almoço": "Almoco5",
    "Lanche": "Lanche3",
    "Jantar": "Jantar4",
    "Ceia": "Ceia5",
}


def _primeiro_item_da_categoria(categoria: str, substituicoes: Dict[str, Any]) -> Dict[str, str]:
    catalogo = substituicoes.get(categoria)
    if not isinstance(catalogo, dict):
        raise ValueError(f"Categoria de substituição não encontrada: {categoria}")

    itens = catalogo.get("itens")
    if not itens:
        raise ValueError(f"Categoria sem itens disponíveis: {categoria}")

    item_bruto = itens[0]
    if isinstance(item_bruto, dict):
        nome = str(item_bruto.get("nome", ""))
        porcao = str(item_bruto.get("porcao", "1 porção")) or "1 porção"
    else:
        nome = str(item_bruto)
        porcao = "1 porção"

    return {"nome": nome, "porcao": porcao}


def _montar_itens_exemplo(slots: Dict[str, Any], substituicoes: Dict[str, Any]) -> List[Dict[str, str]]:
    itens: List[Dict[str, str]] = []
    for slot in slots:
        categorias = SLOT_TO_CATEGORIES.get(slot)
        if not categorias:
            raise ValueError(f"Slot de template desconhecido: {slot}")
        categoria = categorias[0]
        item = _primeiro_item_da_categoria(categoria, substituicoes)
        itens.append({"slot": slot, "categoria": categoria, **item})
    return itens


def montar_plano(
    templates_path: str | Path = "data/templates_refeicoes.json",
    substituicoes_path: str | Path = "data/substituicoes.json",
) -> Dict[str, Any]:
    templates = carregar_templates(str(templates_path))
    substituicoes = carregar_substituicoes(str(substituicoes_path))

    plano_diario: List[Dict[str, Any]] = []
    descricoes: List[str] = []

    for tipo_refeicao, template_id in TEMPLATE_CHOICES.items():
        template = obter_template_por_id(templates, tipo_refeicao, template_id)
        if template is None:
            plano_diario.append({"tipo_refeicao": tipo_refeicao, "erro": "Não consegui acessar os templates de refeição"})
            continue

        slots = template.get("slots", {})
        itens_exemplo = _montar_itens_exemplo(slots, substituicoes)
        plano_diario.append(
            {
                "tipo_refeicao": tipo_refeicao,
                "template_id": template["id"],
                "descricao": template.get("descricao"),
                "slots": slots,
                "itens_exemplo": itens_exemplo,
            }
        )
        descricoes.append(f"{tipo_refeicao.lower()}: {template.get('descricao')}")

    resumo_textual = (
        "Dia alimentar montado apenas com templates do NutriSigno, "
        + "; ".join(descricoes)
        + "."
    )

    return {"plano_diario": plano_diario, "resumo_textual": resumo_textual}


def salvar_plano(
    destino: str | Path = "outputs/plano_teste_templates.json",
    templates_path: str | Path = "data/templates_refeicoes.json",
    substituicoes_path: str | Path = "data/substituicoes.json",
) -> Path:
    plano = montar_plano(templates_path, substituicoes_path)
    destino_path = Path(destino)
    destino_path.parent.mkdir(parents=True, exist_ok=True)
    destino_path.write_text(json.dumps(plano, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino_path


if __name__ == "__main__":
    caminho = salvar_plano()
    print(f"Plano salvo em {caminho}")
