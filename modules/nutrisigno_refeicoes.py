"""Funções utilitárias para gerar refeições e substituições do NutriSigno.

Este módulo carrega templates de refeições e o dicionário de substituições,
realizando o mapeamento entre slots genéricos dos modelos e as categorias
disponíveis no catálogo de alimentos. As funções expostas são pensadas para
serem simples de testar e reutilizar em outros componentes do aplicativo.
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
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


def _slugify(texto: str) -> str:
    """Normaliza um texto removendo acentos e espaços.

    Essa função é usada tanto para criar ``id_alimento`` quanto para permitir
    comparações consistentes por nome. Mantemos apenas caracteres
    alfanuméricos, convertendo sequências de separadores em ``_``.
    """

    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def _gerar_id_alimento(categoria: str, nome: str) -> str:
    """Gera ``id_alimento`` determinístico para cada item do catálogo."""

    categoria_slug = _slugify(categoria)
    nome_slug = _slugify(nome)
    return f"{categoria_slug}__{nome_slug}"


def _normalizar_nome_alimento(nome: str) -> str:
    """Normaliza nomes para busca em índices por nome."""

    return _slugify(nome)


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
    """Lê ``substituicoes.json`` e retorna categorias enriquecidas com ``id_alimento``.

    Além de garantir a estrutura esperada, esta função cria identificadores
    estáveis para todos os alimentos e constrói índices por nome e por ID para
    facilitar consultas durante a geração das refeições.
    """

    data = _load_json(caminho)
    categorias = data.get("categorias")
    if not isinstance(categorias, dict):
        raise ValueError("Estrutura de substituições inválida: chave 'categorias' ausente")

    categorias_enriquecidas: Dict[str, Dict[str, Any]] = {}
    indice_por_nome: Dict[str, List[Dict[str, Any]]] = {}
    indice_por_id: Dict[str, Dict[str, Any]] = {}

    for categoria, dados in categorias.items():
        itens_brutos = dados.get("itens") if isinstance(dados, Mapping) else None
        if not itens_brutos:
            continue

        itens_processados: List[Dict[str, Any]] = []
        for raw_item in itens_brutos:
            if isinstance(raw_item, Mapping):
                nome = str(raw_item.get("nome", ""))
                porcao = str(raw_item.get("porcao", "1 porção")) or "1 porção"
            else:
                nome = str(raw_item)
                porcao = "1 porção"

            # IDs determinísticos para cada alimento do catálogo.
            id_alimento = _gerar_id_alimento(categoria, nome)
            nome_normalizado = _normalizar_nome_alimento(nome)
            item_processado = {
                "id_alimento": id_alimento,
                "nome": nome,
                "porcao": porcao,
                "categoria": categoria,
                "nome_normalizado": nome_normalizado,
            }

            indice_por_id[id_alimento] = item_processado
            indice_por_nome.setdefault(nome_normalizado, []).append(item_processado)
            itens_processados.append(item_processado)

        categorias_enriquecidas[categoria] = {"itens": itens_processados}

    return {
        "categorias": categorias_enriquecidas,
        "indice_alimentos_por_nome": indice_por_nome,
        "indice_alimentos_por_id": indice_por_id,
    }


def listar_modelos_refeicao(templates: Mapping[str, Any], tipo_refeicao: str) -> List[Dict[str, Any]]:
    """Retorna todos os modelos de um tipo de refeição."""

    if tipo_refeicao not in templates:
        raise ValueError(f"Tipo de refeição não encontrado: {tipo_refeicao}")
    modelos = templates.get(tipo_refeicao, [])
    if not isinstance(modelos, Iterable):
        raise ValueError(f"Estrutura inválida para o tipo de refeição: {tipo_refeicao}")
    return list(modelos)


def _obter_categorias(substituicoes: Mapping[str, Any]) -> Mapping[str, Any]:
    """Obtém o dicionário de categorias, seja ele raiz ou dentro de ``categorias``."""

    if "categorias" in substituicoes:
        categorias = substituicoes.get("categorias")
        if isinstance(categorias, Mapping):
            return categorias
    return substituicoes


def _obter_indices(substituicoes: Mapping[str, Any]) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
    """Retorna os índices por nome e por ID se estiverem presentes."""

    indice_nome = substituicoes.get("indice_alimentos_por_nome", {}) if isinstance(substituicoes, Mapping) else {}
    indice_id = substituicoes.get("indice_alimentos_por_id", {}) if isinstance(substituicoes, Mapping) else {}
    return (
        indice_nome if isinstance(indice_nome, Mapping) else {},
        indice_id if isinstance(indice_id, Mapping) else {},
    )


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
    categorias = _obter_categorias(substituicoes)
    catalogo = categorias.get(categoria)
    if catalogo is None:
        raise ValueError(f"Categoria de substituição não encontrada: {categoria}")
    itens = catalogo.get("itens") if isinstance(catalogo, Mapping) else None
    if not itens:
        raise ValueError(f"Categoria sem itens disponíveis: {categoria}")

    item = rng.choice(list(itens))
    if isinstance(item, Mapping):
        nome = str(item.get("nome", ""))
        porcao = str(item.get("porcao", "1 porção")) or "1 porção"
        id_alimento = item.get("id_alimento")
    else:
        nome = str(item)
        porcao = "1 porção"
        id_alimento = _gerar_id_alimento(categoria, nome)

    return {
        "id_alimento": id_alimento,
        "nome": nome,
        "porcao": porcao,
        "categoria": categoria,
    }


def _priorizar_leguminosas(candidatos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reordena candidatos priorizando feijões e grão-de-bico."""

    prioridade: List[Dict[str, Any]] = []
    demais: List[Dict[str, Any]] = []
    for candidato in candidatos:
        nome_norm = candidato.get("nome_normalizado") or _normalizar_nome_alimento(
            candidato.get("nome", "")
        )
        if re.search(r"feij(ao|oes)|grao_de_bico", nome_norm):
            prioridade.append(candidato)
        else:
            demais.append(candidato)
    return prioridade + demais


def _selecionar_por_exemplo(
    slot: str,
    exemplo_prato: Iterable[Mapping[str, Any]] | None,
    substituicoes: Mapping[str, Any],
) -> Dict[str, Any] | None:
    """Tenta encontrar um item do exemplo_prato no índice por nome."""

    categorias_aceitas = SLOT_TO_CATEGORIES.get(slot, [])
    indice_nome, _ = _obter_indices(substituicoes)
    for exemplo in exemplo_prato or []:
        nome_exemplo = str(exemplo.get("nome", ""))
        if not nome_exemplo:
            continue
        nome_norm = _normalizar_nome_alimento(nome_exemplo)
        candidatos = [
            c
            for c in indice_nome.get(nome_norm, [])
            if c.get("categoria") in categorias_aceitas
        ]
        if slot == "leguminosa":
            candidatos = _priorizar_leguminosas(candidatos)
        if candidatos:
            # Prioriza o alimento que casa diretamente com o exemplo_prato.
            return dict(candidatos[0])
    return None


def _selecionar_por_categoria(
    slot: str,
    substituicoes: Mapping[str, Any],
    rng: random.Random,
    priorizar_ordem: bool,
) -> Dict[str, Any]:
    """Fallback genérico: escolhe item dentro das categorias compatíveis."""

    categorias_aceitas = SLOT_TO_CATEGORIES.get(slot)
    if not categorias_aceitas:
        raise ValueError(f"Slot desconhecido: {slot}")

    categorias = _obter_categorias(substituicoes)
    candidatos: List[Dict[str, Any]] = []
    for categoria in categorias_aceitas:
        catalogo = categorias.get(categoria) or {}
        itens = catalogo.get("itens", []) if isinstance(catalogo, Mapping) else []
        for item in itens:
            if isinstance(item, Mapping):
                candidatos.append(dict(item))

    if not candidatos:
        raise ValueError(f"Nenhum item disponível para o slot {slot}")

    if slot == "leguminosa":
        candidatos = _priorizar_leguminosas(candidatos)

    if priorizar_ordem:
        return candidatos[0]
    return rng.choice(candidatos)


def _escolher_item_para_slot(
    slot: str,
    quantidade: int,
    exemplo_prato: Iterable[Mapping[str, Any]] | None,
    substituicoes: Mapping[str, Any],
    rng: random.Random,
    priorizar_exemplo_prato: bool,
) -> List[Dict[str, Any]]:
    """Seleciona os itens concretos para um slot.

    A função primeiro tenta casar com ``exemplo_prato`` quando solicitado e,
    se falhar, aplica o fallback genérico de categorias.
    """

    itens: List[Dict[str, Any]] = []
    for _ in range(quantidade):
        escolhido: Dict[str, Any] | None = None
        if priorizar_exemplo_prato:
            # Prioriza casar o slot com o exemplo_prato do template.
            escolhido = _selecionar_por_exemplo(slot, exemplo_prato, substituicoes)
        if escolhido is None and exemplo_prato and not priorizar_exemplo_prato:
            # Mesmo no modo menos restritivo, tentar casar pelo exemplo auxilia na coerência.
            escolhido = _selecionar_por_exemplo(slot, exemplo_prato, substituicoes)

        if escolhido is None:
            # Fallback genérico: sorteia dentro das categorias compatíveis.
            escolhido = _selecionar_por_categoria(
                slot, substituicoes, rng, priorizar_ordem=priorizar_exemplo_prato
            )

        escolhido["slot"] = str(slot)
        itens.append(escolhido)
    return itens


def gerar_refeicao_concreta(
    template: Mapping[str, Any],
    substituicoes: Mapping[str, Any],
    rng: random.Random | None = None,
    priorizar_exemplo_prato: bool = True,
) -> Dict[str, Any]:
    """Gera uma refeição concreta priorizando a coerência com o exemplo do template.

    Quando ``priorizar_exemplo_prato`` está habilitado, cada slot tenta casar
    com itens do ``exemplo_prato`` utilizando os índices por nome/ID. Caso não
    haja correspondência, ocorre um fallback para as categorias compatíveis.
    """

    rng = rng or random.Random()
    slots = template.get("slots")
    if not isinstance(slots, Mapping):
        raise ValueError("Template inválido: chave 'slots' ausente")

    itens_concretos: List[Dict[str, Any]] = []
    exemplo_prato = template.get("exemplo_prato", []) if isinstance(template, Mapping) else []

    for slot, quantidade in slots.items():
        if not isinstance(quantidade, int) or quantidade < 1:
            raise ValueError(f"Quantidade inválida para o slot {slot}: {quantidade}")
        itens_concretos.extend(
            _escolher_item_para_slot(
                str(slot),
                quantidade,
                exemplo_prato,
                substituicoes,
                rng,
                priorizar_exemplo_prato,
            )
        )

    return {
        "id": template.get("id"),
        "tipo_refeicao": template.get("tipo_refeicao"),
        "descricao": template.get("descricao"),
        "itens": itens_concretos,
        "exemplo_prato": template.get("exemplo_prato", []),
        "slots": dict(slots),
    }


def gerar_substituicoes_para_item(
    categoria: str, substituicoes: Mapping[str, Any], limite: int | None = 5
) -> List[Dict[str, str]]:
    """Retorna uma lista de opções de substituição para a categoria informada."""

    categorias = _obter_categorias(substituicoes)
    catalogo = categorias.get(categoria)
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
            id_alimento = raw_item.get("id_alimento") or _gerar_id_alimento(
                categoria, nome
            )
        else:
            nome = str(raw_item)
            porcao = "1 porção"
            id_alimento = _gerar_id_alimento(categoria, nome)
        resultados.append(
            {
                "id_alimento": id_alimento,
                "nome": nome,
                "porcao": porcao,
                "categoria": categoria,
            }
        )
    return resultados


def _selecionar_template_aleatorio(
    templates: Mapping[str, Any], tipo_refeicao: str, rng: random.Random
) -> Dict[str, Any]:
    """Seleciona um template existente para o tipo informado."""

    modelos = listar_modelos_refeicao(templates, tipo_refeicao)
    if not modelos:
        raise ValueError(f"Nenhum template disponível para o tipo {tipo_refeicao}")
    return dict(rng.choice(modelos))


def _montar_itens_para_template(
    template: Mapping[str, Any],
    substituicoes: Mapping[str, Any],
    rng: random.Random,
) -> List[Dict[str, str]]:
    """Gera a lista de itens concretos respeitando os slots do template."""

    slots = template.get("slots")
    if not isinstance(slots, Mapping):
        raise ValueError("Template inválido: chave 'slots' ausente")

    itens: List[Dict[str, Any]] = []
    exemplo_prato = template.get("exemplo_prato", []) if isinstance(template, Mapping) else []
    for slot, quantidade in slots.items():
        if not isinstance(quantidade, int) or quantidade < 1:
            raise ValueError(f"Quantidade inválida para o slot {slot}: {quantidade}")
        itens.extend(
            _escolher_item_para_slot(
                str(slot),
                quantidade,
                exemplo_prato,
                substituicoes,
                rng,
                priorizar_exemplo_prato=True,
            )
        )
    return itens


def _gerar_resumo_textual(paciente: Mapping[str, Any], plano_diario: List[Dict[str, Any]]) -> str:
    """Cria um texto simples descrevendo o plano alimentar."""

    partes: List[str] = []
    nome_paciente = paciente.get("nome", "Paciente")
    partes.append(
        f"Plano alimentar de 1 dia para {nome_paciente}, pensado para {paciente.get('objetivo', 'o objetivo informado')}"
    )
    for refeicao in plano_diario:
        itens = refeicao.get("itens_escolhidos", [])
        itens_descritos = ", ".join(
            f"{item.get('nome')} ({item.get('porcao')})" for item in itens if item.get("nome")
        )
        partes.append(
            f"{refeicao.get('tipo_refeicao')}: {refeicao.get('descricao')} — {itens_descritos}"
        )
    return " . ".join(partes)


def gerar_plano_diario_simulado(
    paciente: Mapping[str, Any],
    templates_path: str,
    substituicoes_path: str,
    rng_seed: int | None = None,
) -> Dict[str, Any]:
    """Gera um plano alimentar de 1 dia seguindo estritamente os templates."""

    rng = random.Random(rng_seed)
    try:
        templates = carregar_templates(templates_path)
        substituicoes = carregar_substituicoes(substituicoes_path)
    except Exception as exc:  # pragma: no cover - proteção simples
        return {
            "erro": "Falha ao carregar templates_refeicoes.json ou substituicoes.json",
            "detalhes": str(exc),
        }

    plano_diario: List[Dict[str, Any]] = []
    tipos_refeicao = [
        {"tipo": "Desjejum", "chave": "Desjejum"},
        {"tipo": "Almoço", "chave": "Almoço"},
        {"tipo": "Lanche da tarde", "chave": "Lanche"},
        {"tipo": "Jantar", "chave": "Jantar"},
        {"tipo": "Ceia", "chave": "Ceia"},
    ]

    for bloco in tipos_refeicao:
        try:
            template = _selecionar_template_aleatorio(templates, bloco["chave"], rng)
            itens_escolhidos = _montar_itens_para_template(template, substituicoes, rng)
        except Exception as exc:  # pragma: no cover - fluxo de proteção
            return {"erro": "Falha ao gerar refeição", "detalhes": str(exc)}

        slots = template.get("slots") if isinstance(template.get("slots"), Mapping) else {}
        plano_diario.append(
            {
                "tipo_refeicao": bloco["tipo"],
                "template_id": template.get("id"),
                "descricao": template.get("descricao"),
                "slots": dict(slots),
                "itens_escolhidos": itens_escolhidos,
                "exemplo_prato": template.get("exemplo_prato", []),
                "template_tipo_refeicao": bloco["chave"],
            }
        )

    resumo_textual = _gerar_resumo_textual(paciente, plano_diario)
    return {"paciente": dict(paciente), "plano_diario": plano_diario, "resumo_textual": resumo_textual}


def teste_end_to_end_simulado() -> Dict[str, Any]:
    """Executa o fluxo completo solicitado para o cenário fictício."""

    paciente_teste = {
        "nome": "Paciente Teste",
        "sexo": "feminino",
        "idade": 32,
        "altura_m": 1.63,
        "peso_kg": 72,
        "objetivo": "emagrecimento leve",
        "signo": "Leão",
    }

    templates_path = str(Path("data") / "templates_refeicoes.json")
    substituicoes_path = str(Path("data") / "substituicoes.json")

    return gerar_plano_diario_simulado(
        paciente=paciente_teste,
        templates_path=templates_path,
        substituicoes_path=substituicoes_path,
    )


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
