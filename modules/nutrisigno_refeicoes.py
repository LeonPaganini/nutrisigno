"""Funções utilitárias para gerar refeições e substituições do NutriSigno.

Este módulo carrega templates de refeições e o dicionário de substituições,
realizando o mapeamento entre slots genéricos dos modelos e as categorias
disponíveis no catálogo de alimentos. As funções expostas são pensadas para
serem simples de testar e reutilizar em outros componentes do aplicativo.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

SLOT_TO_CATEGORIES: Dict[str, List[str]] = {
    "carboidrato": ["Carboidratos_e_derivados", "Vegetais_ricos_em_carboidratos"],
    "leguminosa": ["Proteina_vegetal"],
    "proteina_animal": [
        "Proteina_animal_baixo_gordura",
        "Proteina_animal_medio_gordura",
        "Proteina_animal_alto_gordura",
    ],
    "proteina_vegetal": ["Proteina_vegetal"],
    "vegetais": ["Vegetais_livres"],
    "fruta": ["Frutas_frescas", "Frutas_secas", "Sucos"],
    "laticinio": ["Laticinios_magros", "Laticinios_medio_alto_gordura"],
    "gordura": ["Gorduras"],
}


def _load_json(path: str | Path) -> Mapping[str, Any]:
    """Carrega um arquivo JSON retornando o conteúdo como dicionário."""

    filepath = Path(path)
    with filepath.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def carregar_templates(caminho: str) -> Dict[str, List[Dict[str, Any]]]:
    """Lê ``templates_refeicoes.json`` e retorna ``modelos_refeicao``.

    Args:
        caminho: Caminho para o arquivo de templates de refeições.

    Returns:
        Dicionário contendo as listas de modelos por tipo de refeição.

    Raises:
        FileNotFoundError: Caso o arquivo não exista.
        json.JSONDecodeError: Caso o arquivo não seja um JSON válido.
    """

    data = _load_json(caminho)
    modelos = data.get("modelos_refeicao")
    if not isinstance(modelos, dict):
        raise ValueError("Estrutura de templates inválida: chave 'modelos_refeicao' ausente")
    return modelos


def carregar_substituicoes(caminho: str) -> Dict[str, Any]:
    """Lê ``substituicoes.json`` e retorna o dicionário de categorias.

    Args:
        caminho: Caminho para o arquivo de substituições.

    Returns:
        Dicionário contendo as categorias e respectivos itens.

    Raises:
        FileNotFoundError: Caso o arquivo não exista.
        json.JSONDecodeError: Caso o arquivo não seja um JSON válido.
    """

    data = _load_json(caminho)
    categorias = data.get("categorias")
    if not isinstance(categorias, dict):
        raise ValueError("Estrutura de substituições inválida: chave 'categorias' ausente")
    return categorias


def listar_modelos_refeicao(templates: Mapping[str, Any], tipo_refeicao: str) -> List[Dict[str, Any]]:
    """Retorna todos os modelos de um tipo de refeição."""

    if tipo_refeicao not in templates:
        raise ValueError(f"Tipo de refeição não encontrado: {tipo_refeicao}")
    modelos = templates.get(tipo_refeicao, [])
    if not isinstance(modelos, Iterable):
        raise ValueError(f"Estrutura inválida para o tipo de refeição: {tipo_refeicao}")
    return list(modelos)


def obter_template_por_id(
    templates: Mapping[str, Any], tipo_refeicao: str, template_id: str
) -> Dict[str, Any] | None:
    """Busca um modelo específico pelo ``id`` dentro de um tipo de refeição."""

    modelos = listar_modelos_refeicao(templates, tipo_refeicao)
    for modelo in modelos:
        if isinstance(modelo, Mapping) and modelo.get("id") == template_id:
            return dict(modelo)
    return None


def _escolher_categoria(slot: str, rng: random.Random | None = None) -> str:
    categorias = SLOT_TO_CATEGORIES.get(slot)
    if not categorias:
        raise ValueError(f"Slot desconhecido: {slot}")
    if rng is None:
        return categorias[0]
    return rng.choice(categorias)


def _sortear_item(categoria: str, substituicoes: Mapping[str, Any], rng: random.Random) -> Dict[str, str]:
    catalogo = substituicoes.get(categoria)
    if catalogo is None:
        raise ValueError(f"Categoria de substituição não encontrada: {categoria}")
    itens = catalogo.get("itens") if isinstance(catalogo, Mapping) else None
    if not itens:
        raise ValueError(f"Categoria sem itens disponíveis: {categoria}")
    item = rng.choice(list(itens))
    if isinstance(item, Mapping):
        nome = str(item.get("nome", ""))
        porcao = str(item.get("porcao", "1 porção")) or "1 porção"
    else:
        nome = str(item)
        porcao = "1 porção"
    return {"nome": nome, "porcao": porcao, "categoria": categoria}


def gerar_refeicao_concreta(
    template: Mapping[str, Any],
    substituicoes: Mapping[str, Any],
    rng: random.Random | None = None,
) -> Dict[str, Any]:
    """Gera uma refeição concreta a partir de um modelo e do catálogo de substituições."""

    rng = rng or random.Random()
    slots = template.get("slots")
    if not isinstance(slots, Mapping):
        raise ValueError("Template inválido: chave 'slots' ausente")

    itens_concretos: List[Dict[str, str]] = []
    for slot, quantidade in slots.items():
        if not isinstance(quantidade, int) or quantidade < 1:
            raise ValueError(f"Quantidade inválida para o slot {slot}: {quantidade}")
        for _ in range(quantidade):
            categoria = _escolher_categoria(str(slot), rng)
            item = _sortear_item(categoria, substituicoes, rng)
            item["slot"] = str(slot)
            itens_concretos.append(item)

    return {
        "id": template.get("id"),
        "tipo_refeicao": template.get("tipo_refeicao"),
        "descricao": template.get("descricao"),
        "itens": itens_concretos,
        "exemplo_prato": template.get("exemplo_prato", []),
    }


def gerar_substituicoes_para_item(
    categoria: str, substituicoes: Mapping[str, Any], limite: int | None = 5
) -> List[Dict[str, str]]:
    """Retorna uma lista de opções de substituição para a categoria informada."""

    catalogo = substituicoes.get(categoria)
    if catalogo is None:
        raise ValueError(f"Categoria de substituição não encontrada: {categoria}")

    itens = catalogo.get("itens") if isinstance(catalogo, Mapping) else None
    if not itens:
        raise ValueError(f"Categoria sem itens disponíveis: {categoria}")

    resultados: List[Dict[str, str]] = []
    for raw_item in itens[: limite or len(itens)]:
        if isinstance(raw_item, Mapping):
            nome = str(raw_item.get("nome", ""))
            porcao = str(raw_item.get("porcao", "1 porção")) or "1 porção"
        else:
            nome = str(raw_item)
            porcao = "1 porção"
        resultados.append({"nome": nome, "porcao": porcao, "categoria": categoria})
    return resultados


def montar_refeicao_e_substituicoes(
    templates_path: str,
    substituicoes_path: str,
    tipo_refeicao: str,
    template_id: str,
    rng: random.Random | None = None,
) -> Dict[str, Any]:
    """Função de alto nível que entrega refeição concreta e substituições sugeridas."""

    templates = carregar_templates(templates_path)
    substituicoes = carregar_substituicoes(substituicoes_path)

    template = obter_template_por_id(templates, tipo_refeicao, template_id)
    if template is None:
        raise ValueError(
            f"Template não encontrado para o tipo '{tipo_refeicao}' com id '{template_id}'"
        )

    template = dict(template)
    template["tipo_refeicao"] = tipo_refeicao

    refeicao = gerar_refeicao_concreta(template, substituicoes, rng)

    substituicoes_por_slot: Dict[str, List[Dict[str, str]]] = {}
    for item in refeicao.get("itens", []):
        categoria = item.get("categoria")
        slot = item.get("slot") or ""
        if categoria:
            substituicoes_por_slot[slot] = gerar_substituicoes_para_item(
                str(categoria), substituicoes
            )

    return {"refeicao": refeicao, "substituicoes": substituicoes_por_slot}
