"""Serviço de pós-pagamento para geração do plano completo NutriSigno."""

from __future__ import annotations

import io
import json
import logging
import os
import random
import time
import traceback
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:  # pragma: no cover - fallback de dependência opcional
    from pypdf import PdfReader, PdfWriter
except Exception:  # pragma: no cover
    try:
        from PyPDF2 import PdfReader, PdfWriter  # type: ignore
    except Exception:  # pragma: no cover
        PdfReader = None  # type: ignore
        PdfWriter = None  # type: ignore
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import email_utils, repo

log = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

PLAN_CATALOG_PATH = Path(
    os.getenv("PLAN_CATALOG_PATH", DATA_DIR / "dietas_index.json")
)
SUBSTITUTIONS_PATH = Path(
    os.getenv("SUBSTITUTIONS_PATH", DATA_DIR / "substituicoes.json")
)

SUGGESTION_VERSION = "v1"
SUPPORT_EMAIL = "equipe.nutripaganini@gmail.com"


@dataclass(frozen=True)
class PlanDefinition:
    """Representa um plano PDF disponível no catálogo."""

    kcal: int
    arquivo: str
    refeicoes_por_porcoes: Dict[str, Dict[str, str]]


class PlanProcessingError(RuntimeError):
    """Erro controlado para indicar falha em determinada etapa."""

    def __init__(self, stage: str, message: str, *, original: Exception | None = None) -> None:
        super().__init__(f"{stage}: {message}")
        self.stage = stage
        self.original = original


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text or "") if unicodedata.category(ch) != "Mn"
    ).lower()


def _normalize_key(text: str) -> str:
    cleaned = _strip_accents(text)
    cleaned = cleaned.replace("/", " ").replace("-", " ")
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return cleaned.strip()


def _to_float(value: Any) -> float | None:
    if value in (None, "", "—"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace(",", ".")
    digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in text)
    for part in digits.split():
        try:
            return float(part)
        except ValueError:
            continue
    return None


def load_plan_catalog(path: Path = PLAN_CATALOG_PATH) -> List[PlanDefinition]:
    """Carrega o catálogo de planos PDF disponíveis."""

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    catalog: List[PlanDefinition] = []
    for item in data.get("dietas", []):
        catalog.append(
            PlanDefinition(
                kcal=int(item["kcal"]),
                arquivo=str(item["arquivo"]),
                refeicoes_por_porcoes=dict(item.get("refeicoes_por_porcoes", {})),
            )
        )
    return catalog


def load_substitution_catalog(path: Path = SUBSTITUTIONS_PATH) -> Dict[str, Any]:
    """Carrega a lista de substituições em formato normalizado."""

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_name, payload in data.get("categorias", {}).items():
        items = payload.get("itens", [])
        normalized_items: List[Dict[str, str]] = []
        for item in items:
            if isinstance(item, dict):
                normalized_items.append(
                    {
                        "nome": item.get("nome") or "—",
                        "porcao": item.get("porcao") or "",
                    }
                )
            else:
                normalized_items.append({"nome": str(item), "porcao": ""})
        normalized[_normalize_key(raw_name)] = {
            "categoria": raw_name,
            "descricao": payload.get("descricao", ""),
            "itens": normalized_items,
        }

    return {
        "source": data.get("fonte") or "LISTA_DE_SUBSTITUICAO_FINAL.pdf",
        "observacao": data.get("observacao"),
        "normalized": normalized,
    }


CATEGORY_ALIAS = {
    "carboidrato": "carboidratos_e_derivados",
    "carboidratos": "carboidratos_e_derivados",
    "vegetais e hortalicas": "vegetais_livres",
    "proteina baixo teor de gordura": "proteina_animal_baixo_gordura",
    "proteina vegetal": "proteina_vegetal",
    "gordura": "gorduras",
    "fruta": "frutas_frescas",
    "laticinio magro": "laticinios_magros",
    "laticinio medio alto teor de gordura": "laticinios_medio_alto_gordura",
    "laticinio medio teor de gordura": "laticinios_medio_alto_gordura",
}


GOAL_DEFAULTS = {
    "nao_treinado": {
        "emagrecer": (23, 27, 25),
        "manter": (28, 32, 30),
        "ganhar": (33, 37, 35),
    },
    "treinado": {
        "emagrecer": (26, 30, 28),
        "manter": (31, 35, 33),
        "ganhar": (36, 40, 38),
    },
}


GOAL_LABEL = {
    "emagrecer": "Emagrecimento",
    "manter": "Manutenção",
    "ganhar": "Ganho de massa",
}


SIGN_ELEMENTS: Dict[str, Tuple[str, ...]] = {
    "Terra": ("touro", "virgem", "capricornio", "capricórnio"),
    "Ar": ("gêmeos", "gemeos", "libra", "aquário", "aquario"),
    "Fogo": ("áries", "aries", "leão", "leao", "sagitário", "sagitario"),
    "Água": ("câncer", "cancer", "escorpião", "escorpiao", "peixes"),
}


SIGN_SYMBOLS = {
    "áries": "♈",
    "aries": "♈",
    "touro": "♉",
    "gêmeos": "♊",
    "gemeos": "♊",
    "câncer": "♋",
    "cancer": "♋",
    "leão": "♌",
    "leao": "♌",
    "virgem": "♍",
    "libra": "♎",
    "escorpião": "♏",
    "escorpiao": "♏",
    "sagitário": "♐",
    "sagitario": "♐",
    "capricórnio": "♑",
    "capricornio": "♑",
    "aquário": "♒",
    "aquario": "♒",
    "peixes": "♓",
}


def _goal_from_text(text: str) -> str:
    normalized = _strip_accents(text or "")
    if any(term in normalized for term in ("emag", "perd", "cut")):
        return "emagrecer"
    if any(term in normalized for term in ("ganh", "massa", "hiper", "bulk")):
        return "ganhar"
    return "manter"


def _is_treinado(activity: str) -> bool:
    normalized = _strip_accents(activity or "")
    return "treinado" in normalized or "5" in normalized


def compute_target_kcal(peso: float, objetivo: str, treinado: bool) -> Tuple[int, Tuple[int, int, int]]:
    """Calcula a meta de kcal (peso × fator)."""

    perfil = "treinado" if treinado else "nao_treinado"
    tabela = GOAL_DEFAULTS[perfil]
    faixa = tabela[objetivo]
    fator = faixa[2]
    target = int(round(peso * fator))
    return target, faixa


def select_plan(target_kcal: int, objetivo: str, catalog: Iterable[PlanDefinition]) -> PlanDefinition:
    """Seleciona o plano PDF mais próximo da kcal alvo."""

    plans = list(catalog)
    if not plans:
        raise ValueError("Catálogo de planos vazio.")

    def sort_key(plan: PlanDefinition) -> Tuple[int, int]:
        distance = abs(plan.kcal - target_kcal)
        return (distance, plan.kcal)

    plans.sort(key=sort_key)
    best_distance = abs(plans[0].kcal - target_kcal)
    tied = [plan for plan in plans if abs(plan.kcal - target_kcal) == best_distance]

    if len(tied) == 1:
        return tied[0]

    if objetivo == "emagrecer":
        return min(tied, key=lambda p: p.kcal)
    if objetivo == "ganhar":
        return max(tied, key=lambda p: p.kcal)
    # manutenção: menor kcal em caso de empate
    return min(tied, key=lambda p: p.kcal)


def prepare_substitutions(
    plan: PlanDefinition,
    catalog: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Retorna dados públicos e mapa interno de substituições para o plano."""

    normalized_map = catalog["normalized"]
    categories_public: List[Dict[str, Any]] = []
    lookup: Dict[str, Dict[str, Any]] = {}

    for meal, categories in plan.refeicoes_por_porcoes.items():
        for cat_name, portion in categories.items():
            key = CATEGORY_ALIAS.get(_normalize_key(cat_name))
            if not key:
                continue
            entry = normalized_map.get(key)
            if not entry:
                continue
            lookup[key] = entry
            existing = next((c for c in categories_public if c["categoria"] == entry["categoria"]), None)
            refeicao_info = {"refeicao": meal, "porcao": portion}
            if existing:
                existing.setdefault("refeicoes", []).append(refeicao_info)
            else:
                categories_public.append(
                    {
                        "categoria": entry["categoria"],
                        "descricao": entry.get("descricao", ""),
                        "refeicoes": [refeicao_info],
                        "itens": entry["itens"],
                    }
                )

    categories_public.sort(key=lambda c: c["categoria"].lower())

    public_payload = {
        "fonte": catalog.get("source"),
        "observacao": catalog.get("observacao"),
        "categorias": categories_public,
    }
    return public_payload, lookup


def generate_combos(
    plan: PlanDefinition,
    lookup: Dict[str, Dict[str, Any]],
    pac_id: str,
) -> Dict[str, Any]:
    """Gera seis combinações (2 por refeição principal)."""

    rng = random.Random(pac_id)
    combos: List[Dict[str, str]] = []
    target_meals = ["Desjejum", "Almoço", "Jantar"]

    for meal in target_meals:
        categories = plan.refeicoes_por_porcoes.get(meal)
        if not categories:
            continue
        normalized_requirements = []
        for raw_cat, portion in categories.items():
            key = CATEGORY_ALIAS.get(_normalize_key(raw_cat))
            if not key:
                continue
            entry = lookup.get(key)
            if not entry or not entry.get("itens"):
                continue
            normalized_requirements.append((entry, portion))
        if not normalized_requirements:
            continue

        meal_id = _strip_accents(meal).replace(" ", "_")
        for variant in range(2):
            parts = []
            for entry, portion in normalized_requirements:
                items = entry["itens"]
                idx = (variant + rng.randint(0, len(items) - 1)) % len(items)
                item = items[idx]
                nome = item.get("nome", "Item")
                parts.append(f"{nome} {portion}".strip())
            if parts:
                combos.append(
                    {
                        "refeicao": meal.lower(),
                        "combo": " + ".join(parts),
                        "id": f"{meal_id}_{variant+1}",
                    }
                )

    timestamp = datetime.utcnow().isoformat()
    return {"versao": SUGGESTION_VERSION, "timestamp": timestamp, "combos": combos}


def _watermark_canvas(canv: canvas.Canvas) -> None:
    width, height = A4
    canv.saveState()
    canv.setFillColorRGB(0.7, 0.68, 0.87)
    canv.setFont("Helvetica-Bold", 48)
    canv.translate(width / 2, height / 2)
    canv.rotate(45)
    canv.drawCentredString(0, 0, "NutriSigno")
    canv.restoreState()

    canv.saveState()
    canv.setFillColorRGB(0.42, 0.36, 0.82)
    canv.setFont("Helvetica", 9)
    canv.drawCentredString(width / 2, 1.2 * cm, "NutriSigno · Plano consolidado")
    canv.restoreState()


def _build_story_pages(story: List[Any]) -> List[Any]:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    def decorate(canv: canvas.Canvas, _doc: SimpleDocTemplate) -> None:
        _watermark_canvas(canv)

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    buffer.seek(0)
    return PdfReader(buffer).pages


def _plan_pages_with_watermark(plan_path: str) -> List[Any]:
    file_path = Path(plan_path)
    if not file_path.exists():
        log.warning("Plano base não encontrado: path=%s", plan_path)
        placeholder = io.BytesIO()
        canv = canvas.Canvas(placeholder, pagesize=A4)
        canv.setFont("Helvetica-Bold", 16)
        canv.drawString(2 * cm, 26 * cm, "Plano base não localizado")
        canv.setFont("Helvetica", 11)
        canv.drawString(2 * cm, 24.5 * cm, f"Arquivo esperado: {file_path.name}")
        canv.drawString(2 * cm, 23.7 * cm, "Entre em contato com o suporte NutriSigno.")
        canv.save()
        placeholder.seek(0)
        page = PdfReader(placeholder).pages[0]
        _watermark_canvas(canvas.Canvas(io.BytesIO(), pagesize=A4))
        return [page]

    if PdfReader is None:
        raise PlanProcessingError("pdf", "biblioteca pypdf ausente")

    reader = PdfReader(str(file_path))
    watermark_buffer = io.BytesIO()
    wm_canvas = canvas.Canvas(watermark_buffer, pagesize=A4)
    _watermark_canvas(wm_canvas)
    wm_canvas.save()
    watermark_buffer.seek(0)
    watermark_page = PdfReader(watermark_buffer).pages[0]

    pages = []
    for page in reader.pages:
        page.merge_page(watermark_page)
        pages.append(page)
    return pages


def _build_cover_story(
    *,
    first_name: str,
    objetivo_label: str,
    target_kcal: int,
    faixa: Tuple[int, int, int],
    plan: PlanDefinition,
    signo: str,
    elemento: str,
    symbol: str,
    respostas: Dict[str, Any],
) -> List[Any]:
    styles = getSampleStyleSheet()
    title_style = styles["Title"].clone("ns_title")
    title_style.textColor = colors.HexColor("#6C5DD3")
    subtitle = ParagraphStyle(
        "subtitle",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#6C5DD3"),
        spaceAfter=12,
    )
    info_style = styles["Normal"].clone("info")
    info_style.leading = 14

    today = datetime.now().strftime("%d/%m/%Y")
    faixa_txt = f"{faixa[0]}–{faixa[1]} kcal/kg (base {faixa[2]} kcal/kg)"

    story: List[Any] = []
    story.append(Paragraph("NutriSigno · Plano Consolidado", title_style))
    story.append(Paragraph("Plano alimentar pós-pagamento", subtitle))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            f"<b>Cliente:</b> {first_name}<br/>"
            f"<b>Objetivo:</b> {objetivo_label}<br/>"
            f"<b>Kcal alvo:</b> {target_kcal} kcal/dia · {faixa_txt}<br/>"
            f"<b>Plano selecionado:</b> {plan.kcal} kcal<br/>"
            f"<b>Signo:</b> {signo or '—'} ({symbol}) · <b>Elemento:</b> {elemento or '—'}<br/>"
            f"<b>Data:</b> {today}",
            info_style,
        )
    )

    story.append(Spacer(1, 18))
    story.append(Paragraph("Indicadores de bem-estar", styles["Heading3"]))
    story.append(Spacer(1, 8))

    fezes_img = ASSETS_DIR / "escala_bistrol.jpeg"
    urina_img = ASSETS_DIR / "escala_urina.jpeg"
    if fezes_img.exists() or urina_img.exists():
        table_data = []
        if urina_img.exists():
            table_data.append(["Urina", f"Seleção: {respostas.get('cor_urina', '—')}"])
        if fezes_img.exists():
            table_data.append(["Fezes", f"Seleção: {respostas.get('tipo_fezes', '—')}"])
        if table_data:
            table = Table(table_data, colWidths=[4 * cm, 11 * cm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F1FF")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#433878")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B9A2FF")),
                    ]
                )
            )
            story.append(table)

    story.append(Spacer(1, 24))
    story.append(Paragraph("Sumário", styles["Heading3"]))
    items = [
        "Capa",
        "Plano base",
        "Tabela de substituições",
        "Sugestões IA (combinações)",
    ]
    rows = [["Seção", "Descrição"]] + [[item, "Inclui marca d'água NutriSigno"] for item in items]
    table = Table(rows, colWidths=[6 * cm, 9 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4D9FF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9A2FF")),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9A2FF")),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 16))

    story.append(
        Paragraph(
            "<i>Privacidade:</i> exibimos apenas o primeiro nome do paciente em todos os artefatos.",
            styles["Italic"],
        )
    )
    return story


def _build_substitution_story(substitutions: Dict[str, Any]) -> List[Any]:
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = styles["Heading3"]
    small = ParagraphStyle("small", parent=normal, fontSize=9, leading=11)

    story: List[Any] = []
    story.append(Paragraph("Tabela de substituições", heading))
    if substitutions.get("observacao"):
        story.append(Paragraph(substitutions["observacao"], small))
    story.append(Spacer(1, 12))

    for categoria in substitutions.get("categorias", []):
        story.append(
            Paragraph(
                f"<b>{categoria['categoria']}</b> — {categoria.get('descricao', '')}",
                normal,
            )
        )
        refeicoes = categoria.get("refeicoes", [])
        if refeicoes:
            refeicao_text = ", ".join(
                f"{item['refeicao']}: {item['porcao']}" for item in refeicoes
            )
            story.append(Paragraph(f"Porções no plano: {refeicao_text}", small))

        for item in categoria.get("itens", []):
            detalhe = f" ({item['porcao']})" if item.get("porcao") else ""
            story.append(Paragraph(f"- {item['nome']}{detalhe}", normal))
        story.append(Spacer(1, 8))
    return story


def _build_combos_story(combos: Dict[str, Any]) -> List[Any]:
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = styles["Heading3"]
    small = ParagraphStyle("small", parent=normal, fontSize=9, leading=11)

    story: List[Any] = []
    story.append(Paragraph("Sugestões IA — Combinações", heading))
    story.append(
        Paragraph(
            f"Versão {combos.get('versao', '—')} · {combos.get('timestamp', '—')}",
            small,
        )
    )
    story.append(Spacer(1, 10))

    grouped: Dict[str, List[str]] = {}
    for combo in combos.get("combos", []):
        grouped.setdefault(combo.get("refeicao", ""), []).append(combo.get("combo", ""))

    for refeicao in ("desjejum", "almoço", "jantar"):
        entries = grouped.get(refeicao)
        if not entries:
            continue
        titulo = refeicao.capitalize()
        story.append(Paragraph(f"<b>{titulo}</b>", normal))
        for texto in entries:
            story.append(Paragraph(f"- {texto}", normal))
        story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "As combinações utilizam apenas itens presentes na lista oficial de substituições e respeitam as porções do plano base.",
            small,
        )
    )
    return story


def build_consolidated_pdf(
    *,
    pac_id: str,
    respostas: Dict[str, Any],
    objetivo_label: str,
    target_kcal: int,
    faixa: Tuple[int, int, int],
    plan: PlanDefinition,
    substitutions_public: Dict[str, Any],
    combos: Dict[str, Any],
) -> str:
    """Gera o PDF consolidado (capa → plano base → substituições → combos)."""

    first_name = ((respostas.get("nome") or "Paciente").strip() or "Paciente").split()[0]
    signo = respostas.get("signo") or "—"
    elemento = "—"
    symbol = "✦"
    sign_norm = _strip_accents(signo)
    for element_name, group in SIGN_ELEMENTS.items():
        if sign_norm in group:
            elemento = element_name
            break
    symbol = SIGN_SYMBOLS.get(sign_norm, symbol)

    cover_story = _build_cover_story(
        first_name=first_name,
        objetivo_label=objetivo_label,
        target_kcal=target_kcal,
        faixa=faixa,
        plan=plan,
        signo=signo,
        elemento=elemento,
        symbol=symbol,
        respostas=respostas,
    )
    substitution_story = _build_substitution_story(substitutions_public)
    combos_story = _build_combos_story(combos)

    pages = []
    pages.extend(_build_story_pages(cover_story))
    pages.extend(_plan_pages_with_watermark(plan.arquivo))
    pages.extend(_build_story_pages(substitution_story))
    pages.extend(_build_story_pages(combos_story))

    output_dir = Path(os.getenv("OUTPUT_DIR", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"nutrisigno_{pac_id[:8]}_{int(time.time())}_plano.pdf"
    file_path = output_dir / filename

    if PdfWriter is None:
        raise PlanProcessingError("pdf", "biblioteca pypdf ausente")

    writer = PdfWriter()
    for page in pages:
        writer.add_page(page)

    with file_path.open("wb") as fh:
        writer.write(fh)

    return str(file_path)


def _execute_with_retries(stage: str, func, *, max_attempts: int = 2, base_delay: float = 0.5):
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        start = time.perf_counter()
        try:
            result = func()
            log.info(
                "post_payment.stage_success",
                extra={"stage": stage, "attempt": attempt, "elapsed": time.perf_counter() - start},
            )
            return result
        except Exception as exc:  # pragma: no cover - logging
            last_exc = exc
            log.exception(
                "post_payment.stage_error",
                extra={"stage": stage, "attempt": attempt, "elapsed": time.perf_counter() - start},
            )
            if attempt == max_attempts:
                raise PlanProcessingError(stage, "falha após retries", original=exc) from exc
            delay = base_delay * (2 ** (attempt - 1))
            time.sleep(delay)
    raise PlanProcessingError(stage, "falha desconhecida", original=last_exc)


def process_post_payment(pac_id: str) -> Dict[str, Any]:
    """Fluxo principal disparado pelo webhook de pagamento."""

    log.info("post_payment.start", extra={"pac_id": pac_id})
    payload = repo.get_by_pac_id(pac_id)
    if not payload:
        raise PlanProcessingError("carregamento", "paciente não localizado")

    respostas = payload.get("respostas") or {}
    peso = _to_float(respostas.get("peso") or respostas.get("peso_kg"))
    if not peso:
        raise PlanProcessingError("validacao", "peso ausente ou inválido")

    objetivo_raw = (
        respostas.get("objetivo")
        or respostas.get("objetivo_principal")
        or respostas.get("meta")
        or "manter"
    )
    objetivo = _goal_from_text(objetivo_raw)
    atividade = respostas.get("nivel_atividade") or ""
    treinado = _is_treinado(atividade)

    catalog = load_plan_catalog()
    substitutions_catalog = load_substitution_catalog()

    target_kcal, faixa = compute_target_kcal(peso, objetivo, treinado)

    plan = _execute_with_retries(
        "selecionar_plano",
        lambda: select_plan(target_kcal, objetivo, catalog),
    )

    substitutions_public, lookup = _execute_with_retries(
        "substituicoes",
        lambda: prepare_substitutions(plan, substitutions_catalog),
    )

    combos = _execute_with_retries(
        "combos",
        lambda: generate_combos(plan, lookup, pac_id),
    )

    pdf_url = _execute_with_retries(
        "pdf",
        lambda: build_consolidated_pdf(
            pac_id=pac_id,
            respostas=respostas,
            objetivo_label=GOAL_LABEL[objetivo],
            target_kcal=target_kcal,
            faixa=faixa,
            plan=plan,
            substitutions_public=substitutions_public,
            combos=combos,
        ),
    )

    repo.save_plan_generation_result(
        pac_id,
        plano_ia={"kcal": plan.kcal, "arquivo": plan.arquivo, "kcal_alvo": target_kcal},
        substituicoes=substitutions_public,
        cardapio_ia=combos,
        pdf_completo_url=pdf_url,
        status_plano="disponivel",
    )

    result = {
        "plano_ia": {"kcal": plan.kcal, "arquivo": plan.arquivo, "kcal_alvo": target_kcal},
        "substituicoes": substitutions_public,
        "cardapio_ia": combos,
        "pdf_completo_url": pdf_url,
        "status_plano": "disponivel",
    }
    log.info("post_payment.success", extra={"pac_id": pac_id, "plan_kcal": plan.kcal})
    return result


def process_post_payment_with_failover(pac_id: str) -> Dict[str, Any]:
    """Wrapper com fallback de erro e notificação ao suporte."""

    try:
        return process_post_payment(pac_id)
    except PlanProcessingError as exc:
        log.error("post_payment.failed", extra={"pac_id": pac_id, "stage": exc.stage})
        repo.mark_plan_error(pac_id)
        trace = traceback.format_exc()
        subject = f"[NutriSigno] Falha na geração do plano · pac_id={pac_id}"
        body = (
            f"Falha na etapa: {exc.stage}\n"
            f"Erro: {exc}\n\n"
            f"Traceback:\n{trace}\n"
        )
        try:
            email_utils.send_email(SUPPORT_EMAIL, subject, body, attachments=None)
        except Exception:  # pragma: no cover - envio de email opcional
            log.exception("post_payment.email_fail", extra={"pac_id": pac_id})
        raise

