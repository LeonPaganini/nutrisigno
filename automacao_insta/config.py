"""Configuration module for NutriSigno Instagram automation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging
import os


@dataclass
class AppPaths:
    """File system paths used across the application."""

    base_dir: Path
    fonts_dir: Path
    renders_dir: Path
    logs_dir: Path
    data_dir: Path
    logo_path: Path


@dataclass
class DbConfig:
    """SQLite database configuration."""

    db_path: Path


@dataclass
class InstagramConfig:
    """Instagram automation related configuration."""

    login_url: str
    username_env: str = "INSTAGRAM_USERNAME"
    password_env: str = "INSTAGRAM_PASSWORD"
    upload_delay_seconds: int = 3
    default_wait_seconds: int = 20
    selectors: dict[str, str] | None = None


@dataclass
class AIConfig:
    """External AI provider configuration (keys provided via env)."""

    provider: str
    api_base: str
    model: str
    api_key_env: str = "OPENAI_API_KEY"


@dataclass
class ImageConfig:
    """Default image generation parameters."""

    width: int = 1080
    height: int = 1350
    margin: int = 120
    palette_background: str = "#F9F6FF"
    palette_primary: str = "#4B2F68"
    palette_gold: str = "#F5C76B"
    palette_accent_light: str = "#C2A7FF"
    palette_accent_dark: str = "#1C102B"
    font_primary: str = "Poppins-Regular.ttf"


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: int = logging.INFO
    fmt: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"
    log_file: Optional[Path] = None


@dataclass
class AppConfig:
    """Consolidated application configuration."""

    paths: AppPaths
    db: DbConfig
    instagram: InstagramConfig
    ai: AIConfig
    images: ImageConfig
    logging: LoggingConfig


def _resolve_path(env_var: str, default: Path) -> Path:
    """Resolve a path from environment variable with a fallback default."""

    env_value = os.getenv(env_var)
    return Path(env_value).expanduser() if env_value else default


def _build_paths(base_dir: Path) -> AppPaths:
    """Construct application paths ensuring directories exist."""

    fonts_dir = _resolve_path("NUTRISIGNO_FONTS_DIR", base_dir / "assets" / "fonts")
    renders_dir = _resolve_path("NUTRISIGNO_RENDERS_DIR", base_dir / "renders")
    logs_dir = _resolve_path("NUTRISIGNO_LOGS_DIR", base_dir / "logs")
    data_dir = _resolve_path("NUTRISIGNO_DATA_DIR", base_dir / "data")

    for path in (fonts_dir, renders_dir, logs_dir, data_dir):
        path.mkdir(parents=True, exist_ok=True)

    logo_path = _resolve_path("NUTRISIGNO_LOGO_PATH", base_dir / "assets" / "logo.png")

    return AppPaths(
        base_dir=base_dir,
        fonts_dir=fonts_dir,
        renders_dir=renders_dir,
        logs_dir=logs_dir,
        data_dir=data_dir,
        logo_path=logo_path,
    )


def _build_logging_config(paths: AppPaths) -> LoggingConfig:
    """Build logging configuration writing to file by default."""

    log_file = paths.logs_dir / "nutrisigno.log"
    return LoggingConfig(log_file=log_file)


def configure_logging(logging_config: LoggingConfig) -> None:
    """Configure global logging for the application."""

    handlers = [logging.StreamHandler()]
    if logging_config.log_file:
        file_handler = logging.FileHandler(logging_config.log_file)
        handlers.append(file_handler)

    logging.basicConfig(
        level=logging_config.level,
        format=logging_config.fmt,
        datefmt=logging_config.datefmt,
        handlers=handlers,
    )


def load_config() -> AppConfig:
    """Load application configuration from environment variables and defaults."""

    base_dir = Path(os.getenv("NUTRISIGNO_BASE_DIR", Path(__file__).resolve().parent))
    paths = _build_paths(base_dir)

    db_path = _resolve_path("NUTRISIGNO_DB_PATH", paths.data_dir / "nutrisigno.db")

    instagram_config = InstagramConfig(
        login_url=os.getenv("NUTRISIGNO_INSTAGRAM_LOGIN_URL", "https://www.instagram.com/accounts/login"),
        selectors={
            "username": "input[name='username']",
            "password": "input[name='password']",
            "submit": "button[type='submit']",
            "new_post": "svg[aria-label='Nova publicação']",
        },
    )

    ai_config = AIConfig(
        provider=os.getenv("NUTRISIGNO_AI_PROVIDER", "openai"),
        api_base=os.getenv("NUTRISIGNO_AI_BASE", "https://api.openai.com/v1"),
        model=os.getenv("NUTRISIGNO_AI_MODEL", "gpt-4o-mini"),
    )

    images_config = ImageConfig(
        width=int(os.getenv("NUTRISIGNO_IMG_WIDTH", 1080)),
        height=int(os.getenv("NUTRISIGNO_IMG_HEIGHT", 1350)),
        margin=int(os.getenv("NUTRISIGNO_IMG_MARGIN", 120)),
    )

    logging_config = _build_logging_config(paths)

    config = AppConfig(
        paths=paths,
        db=DbConfig(db_path=db_path),
        instagram=instagram_config,
        ai=ai_config,
        images=images_config,
        logging=logging_config,
    )

    configure_logging(logging_config)
    return config


__all__ = [
    "AppConfig",
    "AppPaths",
    "DbConfig",
    "InstagramConfig",
    "AIConfig",
    "ImageConfig",
    "LoggingConfig",
    "configure_logging",
    "load_config",
]
