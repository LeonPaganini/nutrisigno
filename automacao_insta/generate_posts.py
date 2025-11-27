"""Generate post texts for NutriSigno."""
from __future__ import annotations

import logging
from typing import Optional

from .config import AppConfig, load_config
from .db import PostStatus, get_posts_by_status, update_post_status

LOGGER = logging.getLogger(__name__)


def _compose_hashtags(entry: dict) -> str:
    base_tags = ["#NutriSigno", "#AstroNutri", "#BemEstar", "#Astrologia"]
    tipo = entry.get("tipo_post", "")
    signo = entry.get("signo")
    tema = entry.get("tema")

    if signo:
        base_tags.append(f"#{signo.replace(' ', '')}")
    if tema:
        base_tags.append(f"#{tema.title()}")

    if tipo:
        base_tags.append(f"#{tipo}")

    return " ".join(base_tags)


def _generate_frase_unica(entry: dict) -> tuple[str, str]:
    signo = entry.get("signo") or "seu signo"
    texto_imagem = (
        f"{signo} merece uma nutrição que respeita ciclos e sensações."
    )
    legenda = (
        "Nutrição místico-racional: acolhe emoções, observa padrões e cria pequenas ações diárias. "
        "Sem promessas rápidas, só constância com carinho."
    )
    return texto_imagem, legenda


def _generate_carrossel_signo(entry: dict) -> tuple[str, str]:
    signo = entry.get("signo", "signo")
    texto_imagem = f"{signo}: 3 micro-hábitos alimentares para nutrir corpo e mente"
    legenda = (
        f"{signo} vibra melhor quando nutrição e rotina conversam. "
        "Teste um hábito por vez e observe como seu corpo responde, sem pressa e sem culpa."
    )
    return texto_imagem, legenda


def _generate_carrossel_tema(entry: dict) -> tuple[str, str]:
    tema = entry.get("tema", "bem-estar")
    texto_imagem = f"Carrossel: como cuidar da {tema} com nutrição gentil"
    legenda = (
        f"{tema.title()} pede escuta do corpo: hidratação, fibras e pausas conscientes. "
        "Sem radicalismos, apenas escolhas constantes que respeitam limites."
    )
    return texto_imagem, legenda


def _generate_educativo(entry: dict) -> tuple[str, str]:
    tema = entry.get("tema", "equilíbrio")
    texto_imagem = f"Nutrição descomplicada: {tema} sem dietas extremas"
    legenda = (
        "Explicação simples e prática, baseada em ciência, para cuidar de você sem prometer milagres. "
        "Acompanhe sinais do corpo e ajuste o prato com gentileza."
    )
    return texto_imagem, legenda


def _generate_previsao_semanal(entry: dict) -> tuple[str, str]:
    signo = entry.get("signo", "signo")
    texto_imagem = f"{signo}: foco nutricional da semana"
    legenda = (
        "Semana pede equilíbrio: água, cores no prato e rotina de sono alinhada. "
        "Use cada refeição como ponto de apoio, sem exageros nem promessas mágicas."
    )
    return texto_imagem, legenda


def _generate_motivacional(entry: dict) -> tuple[str, str]:
    tema = entry.get("tema", "cuidado")
    texto_imagem = f"Real talk: {tema} sem romantizar dieta"
    legenda = (
        "Motivação pé no chão: celebre pequenos avanços, acolha recaídas e siga no ritmo possível. "
        "Nutrição é vínculo com você, não corrida por perfeição."
    )
    return texto_imagem, legenda


type_generators = {
    "frase_unica": _generate_frase_unica,
    "carrossel_signo": _generate_carrossel_signo,
    "carrossel_tema": _generate_carrossel_tema,
    "educativo": _generate_educativo,
    "previsao_semanal": _generate_previsao_semanal,
    "motivacional": _generate_motivacional,
}


def generate_text_for_post(entry: dict, config: Optional[AppConfig] = None) -> dict:
    """Generate texto_imagem, legenda and hashtags for an entry."""

    cfg = config or load_config()
    _ = cfg.ai  # placeholder for future AI integration

    generator = type_generators.get(entry.get("tipo_post"), _generate_frase_unica)
    texto_imagem, legenda = generator(entry)
    hashtags = _compose_hashtags(entry)

    return {"texto_imagem": texto_imagem, "legenda": legenda, "hashtags": hashtags}


def process_post(entry: dict, config: Optional[AppConfig] = None) -> None:
    """Generate text for a single draft and update its status."""

    post_content = generate_text_for_post(entry, config=config)
    update_post_status(
        entry["id"],
        PostStatus.PARA_VALIDAR,
        config=config,
        texto_imagem=post_content["texto_imagem"],
        legenda=post_content["legenda"],
        hashtags=post_content["hashtags"],
    )
    LOGGER.info("Generated content for post %s", entry["id"])


def generate_all_pending_posts(limit: Optional[int] = None, config: Optional[AppConfig] = None) -> None:
    """Process drafts and prepare them for validation."""

    cfg = config or load_config()
    drafts = get_posts_by_status(PostStatus.RASCUNHO, limit=limit or 50, config=cfg)
    if not drafts:
        LOGGER.info("No drafts found for generation")
        return

    for draft in drafts:
        try:
            process_post(draft, config=cfg)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Failed to generate content for post %s: %s", draft.get("id"), exc)
            update_post_status(draft["id"], PostStatus.ERRO, config=cfg)


if __name__ == "__main__":
    generate_all_pending_posts()
