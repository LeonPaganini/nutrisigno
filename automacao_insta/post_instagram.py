"""Automate Instagram posting via Selenium."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import AppConfig, load_config
from .db import PostStatus, get_posts_due, update_post_status

LOGGER = logging.getLogger(__name__)


def start_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def login(driver: webdriver.Chrome, config: AppConfig) -> None:
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
    LOGGER.info("Logged in to Instagram")


def _get_env(var: str) -> str:
    import os

    value = os.getenv(var)
    if not value:
        raise EnvironmentError(f"Missing environment variable: {var}")
    return value


def publish_post(post: dict, driver: webdriver.Chrome, config: AppConfig) -> None:
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

    update_post_status(post["id"], PostStatus.PUBLICADO, config=config, data_publicacao_real=datetime.now().isoformat())
    LOGGER.info("Published post %s", post["id"])


def publish_due_posts(config: Optional[AppConfig] = None) -> None:
    cfg = config or load_config()
    due_posts = get_posts_due(datetime.now().isoformat(), config=cfg)

    if not due_posts:
        LOGGER.info("No posts due for publication")
        return

    driver = start_driver()
    try:
        login(driver, cfg)
        for post in due_posts:
            try:
                publish_post(post, driver, cfg)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to publish post %s: %s", post.get("id"), exc)
                update_post_status(post["id"], PostStatus.ERRO, config=cfg)
    finally:
        driver.quit()


if __name__ == "__main__":
    publish_due_posts()
