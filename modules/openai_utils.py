"""Utilitários para interação com a API da OpenAI.

Este módulo oferece funções para construir prompts e chamar o endpoint
``chat.completions`` da OpenAI, retornando resultados em formato
estruturado (JSON). Além disso, este módulo integra algumas directrizes
adicionais para incorporar elementos astrológicos de maneira ética e
baseada em evidências.

*Os insights astrológicos devem ser embasados em fontes oficiais e
reconhecidas (por exemplo, associações de astrologia, literatura
acadêmica). O modelo é instruído a respeitar princípios científicos de
nutrição e a evitar promessas milagrosas ou sugestões sem evidências.*

A chave de API deve ser definida na variável de ambiente
``OPENAI_API_KEY``.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from openai import OpenAI


def _build_prompt(user_data: Dict[str, Any]) -> str:
    """Constrói o prompt enviado à OpenAI a partir dos dados do usuário.

    O prompt orienta o modelo a responder em formato JSON, contendo um
    plano alimentar detalhado, distribuição de macronutrientes e
    insights comportamentais baseados no perfil astrológico e no
    histórico nutricional. Ele também injeta sugestões específicas
    baseadas no signo do usuário (quando presente), sem perder a
    fundamentação científica. As instruções enfatizam a necessidade
    de utilizar fontes oficiais e confiáveis para os insights
    astrológicos e desencorajam promessas milagrosas.

    Args:
        user_data: dicionário com informações coletadas no formulário.

    Returns:
        Texto do prompt que será passado ao modelo.
    """
    # Dicionário de sugestões baseadas em cada signo.  Estas sugestões
    # fornecem orientações comportamentais e nutricionais gerais.  Você
    # pode expandir ou ajustar conforme julgar necessário, mas evite
    # basear conselhos apenas na astrologia.  Sempre priorize evidências
    # nutricionais.
    sign_hints: Dict[str, str] = {
        "Áries": (
            "Evite estimular impulsividade; prefira refeições práticas e saciantes. "
            "Inclua lanches estratégicos para evitar longos jejuns."
        ),
        "Touro": (
            "Valorize a qualidade sem excessos calóricos.  Crie rituais que aumentem a "
            "adesão, focando em alimentos densos em nutrientes."
        ),
        "Gêmeos": (
            "Varie sabores e texturas para evitar tédio.  Refeições pequenas e frequentes "
            "podem ajudar a manter a energia."
        ),
        "Câncer": (
            "Inclua alimentos reconfortantes e nutritivos.  Horários consistentes podem "
            "trazer estabilidade emocional."
        ),
        "Leão": (
            "Capriche na apresentação dos pratos e incorpore desafios culinários saudáveis. "
            "Alimentos ricos em beta-caroteno são bem-vindos."
        ),
        "Virgem": (
            "Detalhe quantidades com cuidado e prefira alimentos integrais.  Rotinas "
            "estruturadas favorecem disciplina."
        ),
        "Libra": (
            "Busque equilíbrio entre saúde e prazer.  Refeições em companhia podem ser "
            "estimulantes, mas mantenha moderação."
        ),
        "Escorpião": (
            "Valorize intensamente sabores e evite extremos na dieta.  Pratique autocuidado "
            "e mindfulness nas refeições."
        ),
        "Sagitário": (
            "Inclua variedade e opções portáteis para acompanhar um estilo de vida ativo. "
            "Evite excessos e mantenha refeições regulares."
        ),
        "Capricórnio": (
            "Estruture metas claras e progressivas.  Prefira alimentos que sustentem "
            "energia por longos períodos de trabalho."
        ),
        "Aquário": (
            "Introduza tendências alimentares inovadoras de forma equilibrada.  Inclua "
            "superalimentos ricos em antioxidantes."
        ),
        "Peixes": (
            "Priorize refeições leves e ricas em ômega‑3.  Combine a alimentação com "
            "práticas de atenção plena."
        ),
    }
    sign = str(user_data.get("signo") or "").strip()
    hint = sign_hints.get(sign, "")
    instructions = (
        "Você é um nutricionista profissional com conhecimento em astrologia. "
        "Crie um plano alimentar personalizado considerando os dados do usuário abaixo. "
        "Considere o signo solar do usuário para ajustar o tom e o comportamento do plano, "
        "mas a base deve ser a ciência da nutrição.  Utiliza insights astrológicos apenas "
        "quando houver respaldo de fontes oficiais e reconhecidas (Astrological Association, "
        "estudos acadêmicos), e deixe claro que eles não substituem evidências científicas. "
        "Não faça promessas milagrosas e não recomende dietas extremas.  O resultado deve ser "
        "um JSON válido e exclusivo, sem texto acompanhando, contendo os campos:\n"
        "- plano: lista de objetos com 'refeicao', 'descricao', 'alimentos' (array de nomes), "
        "  'quantidades' (array de gramas ou unidades) e 'calorias'.\n"
        "- macros: objeto com 'carboidratos', 'proteinas', 'gorduras' em porcentagem.\n"
        "- insights: texto motivacional e prático com base no signo e no histórico fornecidos.\n"
        "- perfil_astrologico: resumo de traços comportamentais do signo e como eles impactam a alimentação.\n"
        "Não inclua nenhum texto fora do JSON."
    )
    # Inclui o JSON dos dados no prompt para que o modelo tenha contexto.
    user_json = json.dumps(user_data, ensure_ascii=False, indent=2)
    # Adiciona a dica astrológica quando disponível
    if hint:
        instructions += f"\n\nPara este signo ({sign}), considere o seguinte ao elaborar o plano: {hint}"
    prompt = f"{instructions}\n\nDados do usuário:\n{user_json}"
    return prompt


def generate_plan(user_data: Dict[str, Any], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Envia o prompt à OpenAI e retorna um dicionário com o plano gerado.

    Esta função utiliza o SDK mais recente da OpenAI.  Lê a chave da
    API na variável de ambiente ``OPENAI_API_KEY`` e instrui o modelo a
    responder obrigatoriamente em JSON usando o parâmetro
    ``response_format``.  Por padrão, usa-se o modelo ``gpt-4o-mini``
    pela sua eficiência e custo reduzido; altere o argumento ``model``
    conforme necessário.

    Args:
        user_data: dicionário com os dados do usuário.
        model: identificador do modelo da OpenAI a ser utilizado.

    Returns:
        Dicionário contendo plano alimentar, macros, insights e perfil astrológico.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "A variável de ambiente OPENAI_API_KEY não foi definida."
        )
    client = OpenAI(api_key=api_key)
    prompt = _build_prompt(user_data)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um assistente. Responda em JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            response_format={"type": "json_object"},
            max_tokens=1600,
        )
        content = response.choices[0].message.content.strip()
        # Tenta converter a resposta em JSON
        return json.loads(content)
    except Exception as exc:
        raise RuntimeError(f"Falha ao gerar plano com a OpenAI: {exc}") from exc
