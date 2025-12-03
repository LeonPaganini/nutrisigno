"""Ferramentas de publicação no Instagram.

O módulo mantém o fluxo legado via Selenium (guardado por `HAS_SELENIUM`) e
prioriza a publicação real via Instagram Content Publishing API.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

from .config import AppConfig, load_config
from .db import PostStatus, get_posts_due, update_post_status
from .instagram_api_client import InstagramAPIClient, InstagramAPIError

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - apenas para type checking
    from selenium import webdriver as selenium_webdriver  # noqa: F401

try:  # Lazy import para evitar quebra quando selenium não está instalado
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    HAS_SELENIUM = True
except ImportError:  # pragma: no cover - ambiente sem selenium
    webdriver = None  # type: ignore[assignment]
    Options = None  # type: ignore[assignment]
    By = None  # type: ignore[assignment]
    EC = None  # type: ignore[assignment]
    WebDriverWait = None  # type: ignore[assignment]
    HAS_SELENIUM = False


def _get_env(var: str) -> str:
    value = os.getenv(var)
    if not value:
        raise EnvironmentError(f"Missing environment variable: {var}")
    return value


# ---------------------------------------------------------------------------
# Fluxo Selenium (legado)
# ---------------------------------------------------------------------------

def _require_selenium() -> None:
    if not HAS_SELENIUM:
        raise ImportError(
            "Selenium não está instalado neste ambiente. O modo legado está desativado."
        )


def start_driver(headless: bool = True):  # type: ignore[override]
    _require_selenium()
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def login(driver, config: AppConfig) -> None:  # type: ignore[override]
    _require_selenium()
    driver.get(config.instagram.login_url)
    wait = WebDriverWait(driver, config.instagram.default_wait_seconds)

    username_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config.instagram.selectors["username"])))
    password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config.instagram.selectors["password"])))

    username = _get_env(config.instagram.username_env)
    password = _get_env(config.instagram.password_env)

    username_input.send_keys(username)
    password_input.send_keys(password)

    submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config.instagram.selectors["submit"])))
    submit_btn.click()
    LOGGER.info("Logged in to Instagram via Selenium (modo legado)")


def publish_post_selenium(post: dict[str, Any], driver, config: AppConfig) -> None:  # type: ignore[override]
    _require_selenium()
    wait = WebDriverWait(driver, config.instagram.default_wait_seconds)

    new_post_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, config.instagram.selectors["new_post"])))
    new_post_button.click()

    file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
    file_input.send_keys(post["imagem_path"])

    next_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Avançar')]")
    for btn in next_buttons:
        btn.click()

    caption_box = wait.until(EC.presence_of_element_located((By.XPATH, "//textarea")))
    caption_box.send_keys(f"{post.get('legenda', '')}\n\n{post.get('hashtags', '')}")

    share_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Compartilhar')]")
    for btn in share_buttons:
        btn.click()

    WebDriverWait(driver, config.instagram.default_wait_seconds).until(lambda d: "Compartilhado" in d.page_source or "Publicação" in d.page_source)

    update_post_status(
        post["id"],
        PostStatus.PUBLICADO,
        config=config,
        data_publicacao_real=datetime.now().isoformat(),
    )
    LOGGER.info("Published post %s via Selenium", post["id"])


def publish_due_posts_via_selenium(config: Optional[AppConfig] = None) -> None:
    """Mantém o fluxo legado via Selenium, protegido por import opcional."""

    cfg = config or load_config()
    due_posts = get_posts_due(datetime.now().isoformat(), config=cfg)

    if not due_posts:
        LOGGER.info("No posts due for publication (Selenium)")
        return

    driver = start_driver()
    try:
        login(driver, cfg)
        for post in due_posts:
            try:
                publish_post_selenium(post, driver, cfg)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to publish post %s via Selenium: %s", post.get("id"), exc)
                update_post_status(post["id"], PostStatus.ERRO, config=cfg)
    finally:
        driver.quit()


# ---------------------------------------------------------------------------
# Fluxo API Meta (preferencial)
# ---------------------------------------------------------------------------

def simulate_publish_due(config: Optional[AppConfig] = None) -> list[int]:
    """Retorna a lista de IDs que estariam prontos para publicação."""

    cfg = config or load_config()
    due = get_posts_due(datetime.now().isoformat(), config=cfg)
    return [p["id"] for p in due]


def publish_due_posts_via_api(config: Optional[AppConfig] = None) -> list[dict[str, Any]]:
    """Publica posts vencidos usando a Instagram Content Publishing API."""

    cfg = config or load_config()
    due_posts = get_posts_due(datetime.now().isoformat(), config=cfg)

    if not due_posts:
        LOGGER.info("No posts due for publication via API")
        return []

    client = InstagramAPIClient.from_env()
    results: list[dict[str, Any]] = []

    for post in due_posts:
        caption = f"{post.get('legenda', '')}\n\n{post.get('hashtags', '')}".strip()
        image_path = post.get("imagem_path")

        try:
            media_response = client.create_media(caption=caption, image_path=image_path)
            publish_response = client.publish_media(media_response["id"])

            update_post_status(
                post["id"],
                PostStatus.PUBLICADO,
                config=cfg,
                data_publicacao_real=datetime.now().isoformat(),
            )
            results.append(
                {
                    "post_id": post["id"],
                    "status": "success",
                    "creation_id": media_response.get("id"),
                    "publish_id": publish_response.get("id"),
                }
            )
            LOGGER.info("Post %s publicado via API", post["id"])
        except (InstagramAPIError, FileNotFoundError) as exc:
            LOGGER.error("Erro ao publicar post %s via API: %s", post.get("id"), exc)
            update_post_status(post["id"], PostStatus.ERRO, config=cfg)
            results.append({"post_id": post.get("id"), "status": "error", "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Falha inesperada ao publicar post %s via API", post.get("id"))
            update_post_status(post["id"], PostStatus.ERRO, config=cfg)
            results.append({"post_id": post.get("id"), "status": "error", "error": str(exc)})

    return results


def publish_due_posts(config: Optional[AppConfig] = None) -> list[dict[str, Any]]:
    """Wrapper compatível que prioriza a API oficial Meta."""

    return publish_due_posts_via_api(config=config)


if __name__ == "__main__":
    publish_due_posts()
