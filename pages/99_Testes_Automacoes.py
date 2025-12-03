"""Painel de testes e QA das automações de Instagram (ambiente de teste).

Este módulo foi movido para ``pages/`` e mantém as mesmas funcionalidades
existentes na versão anterior, mas com caminhos e imports ajustados para o
novo layout do projeto.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

# --------------------------------------------------------------------------------------
# Ajuste de sys.path para permitir execução via `streamlit run pages/99_Testes_Automacoes.py`
# --------------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


# --------------------------------------------------------------------------------------
# Imports com fallback (scripts/ vs módulo raiz) sem try/except
# --------------------------------------------------------------------------------------

def _select_backend_prefix() -> str:
    """Retorna o prefixo de módulo correto (com ou sem ``scripts``)."""

    return "automacao_insta.scripts" if importlib.util.find_spec("automacao_insta.scripts") else "automacao_insta"


BACKEND_PREFIX = _select_backend_prefix()

config_module = importlib.import_module(f"{BACKEND_PREFIX}.config")
AppConfig = getattr(config_module, "AppConfig")
load_config = getattr(config_module, "load_config")

db_module = importlib.import_module(f"{BACKEND_PREFIX}.db")
PostStatus = getattr(db_module, "PostStatus")
get_connection = getattr(db_module, "get_connection")
init_db = getattr(db_module, "init_db")
update_post_status = getattr(db_module, "update_post_status")

calendar_module = importlib.import_module(f"{BACKEND_PREFIX}.generate_calendar")
generate_calendar = getattr(calendar_module, "generate_calendar")
persist_calendar = getattr(calendar_module, "persist_calendar")

generate_module = importlib.import_module(f"{BACKEND_PREFIX}.generate_posts")
generate_all_pending_posts = getattr(generate_module, "generate_all_pending_posts")

validate_module = importlib.import_module(f"{BACKEND_PREFIX}.validate_posts")
validate_all_pending_posts = getattr(validate_module, "validate_all_pending_posts")
validate_post = getattr(validate_module, "validate_post")

render_module = importlib.import_module(f"{BACKEND_PREFIX}.render_images")
render_all_validated_posts = getattr(render_module, "render_all_validated_posts")
render_post_image = getattr(render_module, "render_post_image")

schedule_module = importlib.import_module(f"{BACKEND_PREFIX}.schedule_queue")
get_posts_due = getattr(schedule_module, "get_posts_due")
schedule_posts_for_range = getattr(schedule_module, "schedule_posts_for_range")

instagram_module = importlib.import_module(f"{BACKEND_PREFIX}.post_instagram")
publish_due_posts_via_api = getattr(instagram_module, "publish_due_posts_via_api")
simulate_publish_due = getattr(instagram_module, "simulate_publish_due", None)
selenium_available = getattr(instagram_module, "HAS_SELENIUM", False)
if simulate_publish_due is None:
    def simulate_publish_due(config: AppConfig | None = None) -> list[int]:
        due = get_posts_due(config=config)
        return [p["id"] for p in due]


TEST_DB_NAME = "posts_test.db"
TEST_RENDERS_DIRNAME = "renders_test"


# --------------------------------------------------------------------------------------
# Helpers de caminhos
# --------------------------------------------------------------------------------------

def get_project_root() -> Path:
    """Retorna a raiz do projeto (um nível acima de ``pages/``)."""

    return PROJECT_ROOT


def resolve_path(*parts: str) -> Path:
    """Constrói um caminho absoluto a partir da raiz do projeto."""

    return get_project_root().joinpath(*parts)


def get_test_db_path() -> Path:
    """Caminho absoluto para o banco de teste, garantindo existência da pasta."""

    path = resolve_path("automacao_insta", "data", TEST_DB_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_test_renders_path() -> Path:
    """Caminho absoluto para a pasta de renders de teste, garantindo criação."""

    path = resolve_path("automacao_insta", "data", TEST_RENDERS_DIRNAME)
    path.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------------------
# Helpers de configuração e estado
# --------------------------------------------------------------------------------------

def get_test_config() -> AppConfig:
    """Carrega a configuração padrão e redireciona para recursos de teste."""

    base_cfg = load_config()
    test_db_path = get_test_db_path()
    test_renders_dir = get_test_renders_path()

    cfg = replace(base_cfg)
    cfg.paths = replace(base_cfg.paths)
    cfg.db = replace(base_cfg.db)
    cfg.paths.data_dir = test_db_path.parent
    cfg.paths.renders_dir = test_renders_dir
    cfg.db.db_path = test_db_path
    return cfg


def init_test_env() -> AppConfig:
    """Inicializa o ambiente de teste e retorna a config especializada."""

    cfg = get_test_config()
    init_db(cfg)
    if "qa_logs" not in st.session_state:
        st.session_state.qa_logs = []
    return cfg


def log_event(message: str) -> None:
    """Registra eventos simples na sessão."""

    logs = st.session_state.get("qa_logs", [])
    logs.insert(0, f"{datetime.now().strftime('%H:%M:%S')} - {message}")
    st.session_state.qa_logs = logs[:100]


# --------------------------------------------------------------------------------------
# Consultas ao banco de teste
# --------------------------------------------------------------------------------------

def fetch_posts(cfg: AppConfig, status: str | None = None) -> list[dict[str, Any]]:
    """Busca posts com ou sem filtro de status."""

    conn = get_connection(cfg.db.db_path)
    try:
        if status and status != "todos":
            cursor = conn.execute("SELECT * FROM posts WHERE status = ? ORDER BY id DESC", (status,))
        else:
            cursor = conn.execute("SELECT * FROM posts ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def fetch_counts(cfg: AppConfig) -> dict[str, int]:
    """Retorna contagem de posts por status."""

    counts = {status: 0 for status in vars(PostStatus).values() if isinstance(status, str)}
    conn = get_connection(cfg.db.db_path)
    try:
        cursor = conn.execute("SELECT status, COUNT(*) as total FROM posts GROUP BY status")
        for row in cursor.fetchall():
            counts[row["status"]] = row["total"]
    finally:
        conn.close()
    return counts


def fetch_post_by_id(cfg: AppConfig, post_id: int) -> dict[str, Any] | None:
    conn = get_connection(cfg.db.db_path)
    try:
        cursor = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_test_environment(cfg: AppConfig) -> None:
    """Remove banco de teste e renders gerados."""

    db_path = cfg.db.db_path
    renders_dir = cfg.paths.renders_dir

    if db_path.exists():
        db_path.unlink()
    if renders_dir.exists():
        for img in renders_dir.glob("*"):
            if img.is_file():
                img.unlink()
    init_db(cfg)


# --------------------------------------------------------------------------------------
# Ações de pipeline
# --------------------------------------------------------------------------------------

def run_end_to_end(cfg: AppConfig, quantidade: int) -> None:
    """Executa do calendário até o agendamento, sem publicar."""

    entries = generate_calendar(quantidade)
    persist_calendar(entries, config=cfg)
    generate_all_pending_posts(limit=quantidade, config=cfg)
    validate_all_pending_posts(config=cfg)
    render_all_validated_posts(limit=quantidade, config=cfg)

    start = date.today()
    end = start + timedelta(days=quantidade - 1)
    schedule_posts_for_range(start, end, publish_time=time(hour=9), config=cfg)
    log_event(f"Fluxo end-to-end concluído para {quantidade} post(s).")


def force_validate_post(cfg: AppConfig, post: dict[str, Any]) -> None:
    result = validate_post(post)
    status = result.get("status")

    update_post_status(
        post["id"],
        status or PostStatus.ERRO,
        config=cfg,
        texto_imagem=result.get("texto_imagem", post.get("texto_imagem")),
        legenda=result.get("legenda", post.get("legenda")),
        hashtags=result.get("hashtags", post.get("hashtags")),
    )
    log_event(f"Validação forçada aplicada ao post {post['id']}")


def force_render_post(cfg: AppConfig, post: dict[str, Any]) -> str:
    path = render_post_image(post, config=cfg)
    log_event(f"Renderização forçada gerou {path}")
    return path


# --------------------------------------------------------------------------------------
# Componentes de UI
# --------------------------------------------------------------------------------------

def render_overview_tab(cfg: AppConfig) -> None:
    counts = fetch_counts(cfg)
    st.subheader("Visão geral do banco de teste")

    cols = st.columns(4)
    status_order = [
        PostStatus.RASCUNHO,
        PostStatus.PARA_VALIDAR,
        PostStatus.VALIDADO,
        PostStatus.RENDERIZADO,
        PostStatus.AGENDADO,
        PostStatus.PUBLICADO,
        PostStatus.ERRO,
    ]
    for idx, status in enumerate(status_order):
        with cols[idx % len(cols)]:
            st.metric(status.replace("_", " ").title(), counts.get(status, 0))

    st.divider()
    st.markdown("### Teste rápido end-to-end")
    qtd = st.slider("Quantos posts gerar?", 1, 5, 2)
    if st.button("Rodar fluxo completo", type="primary"):
        with st.spinner("Executando pipeline de teste..."):
            run_end_to_end(cfg, qtd)
        st.success("Fluxo completo executado. Confira a fila e as métricas.")



def render_pipeline_tab(cfg: AppConfig) -> None:
    st.subheader("Etapas do pipeline")
    with st.expander("Geração de calendário", expanded=True):
        dias = st.number_input("Dias a gerar", min_value=1, max_value=30, value=7)
        if st.button("Gerar calendário", key="btn_calendar"):
            with st.spinner("Gerando calendário de teste..."):
                entries = generate_calendar(dias)
                persist_calendar(entries, config=cfg)
            st.success(f"{len(entries)} entradas adicionadas como rascunho.")
            log_event(f"Calendário de {dias} dia(s) gerado para testes")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Gerar textos IA", key="btn_generate"):
            with st.spinner("Gerando conteúdo para rascunhos..."):
                generate_all_pending_posts(config=cfg)
            st.success("Geração concluída.")
            log_event("Textos gerados para rascunhos")
    with col2:
        if st.button("Validar pendentes", key="btn_validate"):
            with st.spinner("Validando posts..."):
                validate_all_pending_posts(config=cfg)
            st.success("Validação concluída.")
            log_event("Validação executada")
    with col3:
        if st.button("Renderizar validados", key="btn_render"):
            with st.spinner("Renderizando imagens..."):
                render_all_validated_posts(config=cfg)
            st.success("Renderização finalizada.")
            log_event("Renderização executada")

    st.divider()
    st.markdown("#### Agendamento")
    start = st.date_input("Início", value=date.today())
    end = st.date_input("Fim", value=date.today() + timedelta(days=6))
    hora = st.slider("Hora de publicação", 0, 23, 9)
    if st.button("Agendar renderizados"):
        with st.spinner("Aplicando datas na fila..."):
            schedule_posts_for_range(start, end, publish_time=time(hour=hora), config=cfg)
        st.success("Agendamentos aplicados.")
        log_event("Agendamentos aplicados via painel")

    st.divider()
    st.markdown("#### Ações avançadas / Forçar fluxo")
    posts = fetch_posts(cfg)
    if not posts:
        st.info("Nenhum post disponível para ações avançadas.")
        return

    selected_id = st.selectbox("Selecione o ID do post", [p["id"] for p in posts])
    post = fetch_post_by_id(cfg, selected_id)
    if not post:
        st.warning("Post não encontrado.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Forçar validação"):
            with st.spinner("Aplicando validação..."):
                force_validate_post(cfg, post)
            st.success("Validação forçada concluída.")
    with col_b:
        if st.button("Forçar renderização"):
            with st.spinner("Gerando imagem..."):
                img_path = force_render_post(cfg, post)
            st.success(f"Imagem salva em {img_path}")
            if Path(img_path).exists():
                st.image(img_path, caption=f"Preview post {post['id']}")



def _render_post_timeline(post: dict[str, Any]) -> None:
    statuses = [
        PostStatus.RASCUNHO,
        PostStatus.PARA_VALIDAR,
        PostStatus.VALIDADO,
        PostStatus.RENDERIZADO,
        PostStatus.AGENDADO,
        PostStatus.PUBLICADO,
        PostStatus.ERRO,
    ]
    st.markdown(
        " > ".join(
            [f"**{s}**" if post.get("status") == s else s for s in statuses]
        )
    )



def render_database_tab(cfg: AppConfig) -> None:
    st.subheader("Banco de posts e fila")
    status_filter = st.selectbox(
        "Filtrar por status",
        options=[
            "todos",
            PostStatus.RASCUNHO,
            PostStatus.PARA_VALIDAR,
            PostStatus.VALIDADO,
            PostStatus.RENDERIZADO,
            PostStatus.AGENDADO,
            PostStatus.PUBLICADO,
            PostStatus.ERRO,
        ],
    )
    posts = fetch_posts(cfg, status=status_filter)
    st.dataframe(posts, use_container_width=True, hide_index=True)

    if not posts:
        st.info("Nenhum post encontrado no filtro atual.")
        return

    post_ids = [p["id"] for p in posts]
    selected_id = st.selectbox("Selecionar post para detalhes", post_ids)
    post = fetch_post_by_id(cfg, selected_id)
    if not post:
        st.warning("Post não encontrado.")
        return

    st.markdown("### Detalhes do post")
    st.write({k: v for k, v in post.items() if k not in {"texto_imagem", "legenda", "hashtags", "imagem_path"}})

    cols = st.columns(3)
    with cols[0]:
        st.markdown("**Texto da imagem**")
        st.write(post.get("texto_imagem") or "—")
    with cols[1]:
        st.markdown("**Legenda**")
        st.write(post.get("legenda") or "—")
    with cols[2]:
        st.markdown("**Hashtags**")
        st.write(post.get("hashtags") or "—")

    st.markdown("**Timeline de status**")
    _render_post_timeline(post)

    img_path = post.get("imagem_path")
    if img_path and Path(img_path).exists():
        st.image(img_path, caption=f"Preview da renderização ({img_path})", use_column_width=True)



def render_publish_tab(cfg: AppConfig) -> None:
    st.subheader("Publicação e simulação")
    due_posts = get_posts_due(config=cfg)

    st.markdown("### Simulação")
    if st.button("Simular publicação dos posts vencidos"):
        if not due_posts:
            st.info("Nenhum post vencido para publicar.")
        else:
            st.success("Simulação concluída. Posts que seriam publicados:")
            st.json([p["id"] for p in due_posts])
            log_event(f"Simulação de publicação para {len(due_posts)} post(s)")

    st.divider()
    st.markdown("### Publicação REAL (API Meta)")
    st.warning(
        "Esta ação usará a conta real configurada via API oficial da Meta. Utilize somente se tiver certeza e com credenciais válidas.",
        icon="⚠️",
    )
    st.info(
        "Automação via Selenium está desativada neste ambiente; a publicação real ocorrerá apenas via API.",
        icon="ℹ️",
    )
    if not selenium_available:
        st.caption("Modo legado Selenium indisponível (pacote não instalado ou desativado).")

    confirm = st.checkbox("Eu entendo que isso vai postar na conta real")
    if st.button("Publicar posts vencidos (MODO REAL)", type="primary"):
        if not confirm:
            st.error("Confirme a caixa de seleção antes de publicar.")
        elif not due_posts:
            st.info("Nenhum post vencido no momento.")
        else:
            with st.spinner("Publicando via API Meta..."):
                result = publish_due_posts_via_api(config=cfg)
            st.success("Processo de publicação real finalizado.")
            if result:
                st.json(result)
            log_event("Publicação real disparada via API Meta")



def render_environment_tab(cfg: AppConfig) -> None:
    st.subheader("Ambiente de teste")
    st.write(
        {
            "Banco de teste": str(cfg.db.db_path),
            "Renders de teste": str(cfg.paths.renders_dir),
            "Logo": str(cfg.paths.logo_path),
            "Fonts": str(cfg.paths.fonts_dir),
        }
    )

    st.markdown("### Resetar ambiente de teste")
    confirm = st.checkbox("Apagar banco e renders de teste", key="reset_confirm")
    if st.button("Resetar Ambiente de Teste", type="primary"):
        if not confirm:
            st.error("Confirme a intenção antes de resetar.")
        else:
            with st.spinner("Limpando base e renders de teste..."):
                delete_test_environment(cfg)
            st.success("Ambiente de teste resetado.")
            log_event("Reset completo do ambiente de teste")

    st.divider()
    st.markdown("### Logs recentes")
    for entry in st.session_state.get("qa_logs", [])[:30]:
        st.write(entry)


# --------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Painel QA Automações Instagram", page_icon="🧪", layout="wide")
    st.title("Painel de Testes – Automações Instagram (NutriSigno)")
    st.write(
        "Ferramenta interna para validar o pipeline de automações do Instagram sem afetar o banco de produção."
    )

    cfg = init_test_env()

    st.info(
        f"Usando banco de TESTE em: {cfg.db.db_path}\nRenders de teste: {cfg.paths.renders_dir}",
        icon="🧪",
    )

    tabs = st.tabs(["Visão geral", "Pipeline", "Banco & Fila", "Publicação", "Ambiente de Teste"])
    with tabs[0]:
        render_overview_tab(cfg)
    with tabs[1]:
        render_pipeline_tab(cfg)
    with tabs[2]:
        render_database_tab(cfg)
    with tabs[3]:
        render_publish_tab(cfg)
    with tabs[4]:
        render_environment_tab(cfg)


if __name__ == "__main__":
    main()
