"""Geração determinística de cardápios a partir do pré-plano.

O objetivo é transformar o ``pre_plano`` (porções por refeição) em um
cardápio de 1 dia com alimentos reais retirados exclusivamente da lista de
substituições validada por nutricionista. Nenhuma chamada de IA é necessária
e o resultado é totalmente replicável.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Tuple


# Mapeamento dos grupos de porções para as categorias do arquivo de
# substituições. Utilizamos apenas nomes normalizados (minúsculos e sem
# acentos) para facilitar a resolução.
CATEGORY_MAP: Mapping[str, str] = {
    "carboidratos": "Carboidratos_e_derivados",
    "carboidrato": "Carboidratos_e_derivados",
    "vegetais e hortaliças": "Vegetais_livres",
    "vegetais e hortalicas": "Vegetais_livres",
    "vegetais": "Vegetais_livres",
    "fruta": "Frutas_frescas",
    "fruta ou suco da fruta": "Frutas_frescas",
    "frutas": "Frutas_frescas",
    "suco": "Sucos",
    "laticínio magro": "Laticinios_magros",
    "laticinio magro": "Laticinios_magros",
    "laticínio médio/alto teor de gordura": "Laticinios_medio_alto_gordura",
    "laticinio medio/alto teor de gordura": "Laticinios_medio_alto_gordura",
    "laticínio médio teor de gordura": "Laticinios_medio_alto_gordura",
    "laticinio medio teor de gordura": "Laticinios_medio_alto_gordura",
    "proteína baixo teor de gordura": "Proteina_animal_baixo_gordura",
    "proteina baixo teor de gordura": "Proteina_animal_baixo_gordura",
    "proteína vegetal": "Proteina_vegetal",
    "proteina vegetal": "Proteina_vegetal",
    "gordura": "Gorduras",
}


def _normalize_key(text: str) -> str:
    """Remove acentos e converte para minúsculas para facilitar matching."""

    normalized = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore")
    return normalized.decode("ascii").lower().strip()


def _resolve_category(raw_name: str) -> str | None:
    """Resolve o nome de categoria do JSON de substituições.

    Caso não encontre correspondência direta em :data:`CATEGORY_MAP`, utiliza
    heurísticas simples baseadas em substrings para manter a robustez.
    """

    key = _normalize_key(raw_name)
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]

    if "carbo" in key:
        return "Carboidratos_e_derivados"
    if "frut" in key:
        return "Frutas_frescas"
    if "veget" in key or "hortal" in key:
        return "Vegetais_livres"
    if "latic" in key:
        # Preferimos versão magra por padrão
        if "medio" in key or "alto" in key:
            return "Laticinios_medio_alto_gordura"
        return "Laticinios_magros"
    if "gordur" in key:
        return "Gorduras"
    if "proteina vegetal" in key or "proteína vegetal" in raw_name.lower():
        return "Proteina_vegetal"
    if "proteina" in key or "proteína" in raw_name.lower():
        return "Proteina_animal_baixo_gordura"

    return None


def _parse_portion_count(raw_portion: Any) -> int:
    """Extrai a quantidade de porções de um texto ou número."""

    if isinstance(raw_portion, (int, float)):
        return int(raw_portion)

    match = re.search(r"([\d,.]+)", str(raw_portion))
    if match:
        value = match.group(1).replace(",", ".")
        try:
            return max(int(float(value)), 1)
        except ValueError:
            pass
    return 1


def _format_item(item: Any) -> str:
    """Formata o item de substituição para texto legível."""

    if isinstance(item, dict):
        nome = item.get("nome") or "Item"
        porcao = item.get("porcao") or ""
        return f"{nome} {porcao}".strip()
    return str(item)


def _build_catalog(substituicoes: Mapping[str, Any]) -> Mapping[str, List[str]]:
    """Normaliza o catálogo bruto em um mapa de categoria -> lista de itens."""

    categorias = substituicoes.get("categorias") or {}
    catalog: Dict[str, List[str]] = {}

    for nome, payload in categorias.items():
        itens = payload.get("itens") or []
        catalog[nome] = [_format_item(item) for item in itens]

    return catalog


def _select_default_items(items: List[str], portions: int) -> Tuple[List[str], Dict[str, int]]:
    """Seleciona itens padrão (determinísticos) e suas contagens."""

    if not items:
        return [], {}

    chosen: List[str] = []
    counts: Dict[str, int] = {}
    for idx in range(portions):
        item = items[idx % len(items)]
        chosen.append(item)
        counts[item] = counts.get(item, 0) + 1

    return chosen, counts


def _substitution_options(items: Iterable[str], chosen: Iterable[str]) -> List[str]:
    """Retorna opções alternativas (2 a 5) diferentes dos escolhidos."""

    chosen_set = set(chosen)
    options = [item for item in items if item not in chosen_set]
    if len(options) < 2:
        # Completa com escolhidos para atingir pelo menos 2 sugestões
        options.extend([item for item in chosen if item not in options])
    return options[:5]


def _build_comentario(signo: str | None, perfil: str | None) -> str:
    signo_txt = (signo or "").strip().title() or "seu signo"
    perfil_txt = (perfil or "" ).strip()
    base = f"Para {signo_txt}, priorizamos saciedade e equilíbrio energético."
    if perfil_txt:
        return f"{base} Perfil: {perfil_txt}."
    return base


def _build_refeicao(
    nome_refeicao: str,
    categorias_por_porcoes: Mapping[str, Any],
    catalog: Mapping[str, List[str]],
    signo: str | None,
    perfil: str | None,
) -> Dict[str, Any]:
    refeicao_padrao: List[Dict[str, Any]] = []
    opcoes_substituicao: Dict[str, List[str]] = {}

    for raw_cat, portion_text in categorias_por_porcoes.items():
        categoria_lookup = _resolve_category(raw_cat)
        if not categoria_lookup:
            continue
        itens_categoria = catalog.get(categoria_lookup)
        if not itens_categoria:
            continue

        portion_count = _parse_portion_count(portion_text)
        chosen_items, counts = _select_default_items(itens_categoria, portion_count)

        for item_name, qty in counts.items():
            refeicao_padrao.append(
                {
                    "categoria_porcoes": raw_cat,
                    "alimento": item_name,
                    "porcoes_equivalentes": qty,
                }
            )

        opcoes_substituicao[raw_cat] = _substitution_options(itens_categoria, chosen_items)

    return {
        "nome_refeicao": nome_refeicao,
        "refeicao_padrao": refeicao_padrao,
        "opcoes_substituicao": opcoes_substituicao,
        "comentario_astrologico": _build_comentario(signo, perfil),
    }


def build_cardapio(pre_plano: Mapping[str, Any], substituicoes: Mapping[str, Any]) -> Dict[str, Any]:
    """Gera o cardápio de 1 dia seguindo o contrato esperado pelo app."""

    try:
        catalog = _build_catalog(substituicoes)
        porcoes_por_refeicao: MutableMapping[str, Any] = pre_plano.get("porcoes_por_refeicao") or {}
        if not porcoes_por_refeicao:
            return {"erro": "porcoes_por_refeicao ausentes"}

        signo = pre_plano.get("signo")
        perfil = pre_plano.get("perfil_astrologico_resumido")

        refeicoes: List[Dict[str, Any]] = []
        for nome, categorias in porcoes_por_refeicao.items():
            refeicoes.append(
                _build_refeicao(
                    nome_refeicao=nome,
                    categorias_por_porcoes=categorias or {},
                    catalog=catalog,
                    signo=signo,
                    perfil=perfil,
                )
            )

        descricao_kcal = pre_plano.get("kcal_alvo") or pre_plano.get("dieta_pdf_kcal")
        descricao = None
        if descricao_kcal:
            descricao = f"Dia padrão de alimentação para {descricao_kcal} kcal."

        return {
            "cardapio_dia": {
                "descricao_dia": descricao,
                "refeicoes": refeicoes,
            }
        }
    except Exception as exc:  # pragma: no cover - fallback defensivo
        return {"erro": str(exc)}


__all__ = [
    "build_cardapio",
]
