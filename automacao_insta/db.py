"""SQLite helpers for NutriSigno automation."""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

from .config import AppConfig, load_config

LOGGER = logging.getLogger(__name__)


class PostStatus:
    RASCUNHO = "rascunho"
    GERADO = "gerado"
    PARA_VALIDAR = "para_validar"
    VALIDADO = "validado"
    RENDERIZADO = "renderizado"
    AGENDADO = "agendado"
    PUBLICADO = "publicado"
    ERRO = "erro"


@dataclass
class PostRecord:
    id: int
    tipo_post: str
    signo: Optional[str]
    tema: Optional[str]
    texto_imagem: str
    legenda: str
    hashtags: str
    status: str
    imagem_path: Optional[str]
    data_publicacao_planejada: Optional[str]
    data_publicacao_real: Optional[str]
    likes: int
    comentarios: int
    saves: int
    shares: int


SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_post TEXT NOT NULL,
    signo TEXT,
    tema TEXT,
    texto_imagem TEXT NOT NULL,
    legenda TEXT NOT NULL,
    hashtags TEXT NOT NULL,
    status TEXT NOT NULL,
    imagem_path TEXT,
    data_publicacao_planejada TEXT,
    data_publicacao_real TEXT,
    likes INTEGER DEFAULT 0,
    comentarios INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS logs_execucao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento TEXT NOT NULL,
    detalhes TEXT,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Create a SQLite connection with row factory set."""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(config: Optional[AppConfig] = None) -> None:
    """Initialize database tables."""

    cfg = config or load_config()
    LOGGER.info("Initializing database at %s", cfg.db.db_path)
    conn = get_connection(cfg.db.db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_post(
    tipo_post: str,
    signo: Optional[str],
    tema: Optional[str],
    texto_imagem: str,
    legenda: str,
    hashtags: str,
    status: str = PostStatus.RASCUNHO,
    imagem_path: Optional[str] = None,
    data_publicacao_planejada: Optional[str] = None,
    config: Optional[AppConfig] = None,
) -> int:
    """Insert a post record and return its ID."""

    cfg = config or load_config()
    conn = get_connection(cfg.db.db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO posts (
                tipo_post, signo, tema, texto_imagem, legenda, hashtags,
                status, imagem_path, data_publicacao_planejada
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tipo_post,
                signo,
                tema,
                texto_imagem,
                legenda,
                hashtags,
                status,
                imagem_path,
                data_publicacao_planejada,
            ),
        )
        conn.commit()
        post_id = int(cursor.lastrowid)
        LOGGER.debug("Inserted post %s with status %s", post_id, status)
        return post_id
    finally:
        conn.close()


def update_post_status(post_id: int, novo_status: str, config: Optional[AppConfig] = None, **extra_fields: Any) -> None:
    """Update the status and optional extra fields for a post."""

    cfg = config or load_config()
    set_clauses = ["status = ?"]
    values: List[Any] = [novo_status]

    for key, value in extra_fields.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)

    values.append(post_id)
    query = f"UPDATE posts SET {', '.join(set_clauses)} WHERE id = ?"

    conn = get_connection(cfg.db.db_path)
    try:
        conn.execute(query, values)
        conn.commit()
        LOGGER.debug("Updated post %s to status %s", post_id, novo_status)
    finally:
        conn.close()


def get_posts_by_status(status: str, limit: int = 10, config: Optional[AppConfig] = None) -> list[dict[str, Any]]:
    """Fetch posts filtered by status."""

    cfg = config or load_config()
    conn = get_connection(cfg.db.db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM posts WHERE status = ? ORDER BY id ASC LIMIT ?",
            (status, limit),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_posts_without_schedule(config: Optional[AppConfig] = None) -> list[dict[str, Any]]:
    """Fetch renderized posts without planned publication date."""

    cfg = config or load_config()
    conn = get_connection(cfg.db.db_path)
    try:
        cursor = conn.execute(
            """
            SELECT * FROM posts
            WHERE status = ? AND (data_publicacao_planejada IS NULL OR data_publicacao_planejada = '')
            ORDER BY id ASC
            """,
            (PostStatus.RENDERIZADO,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_posts_due(now_iso: str, config: Optional[AppConfig] = None) -> list[dict[str, Any]]:
    """Return agendado posts due for publication."""

    cfg = config or load_config()
    conn = get_connection(cfg.db.db_path)
    try:
        cursor = conn.execute(
            """
            SELECT * FROM posts
            WHERE status = ? AND data_publicacao_planejada <= ?
            ORDER BY data_publicacao_planejada ASC
            """,
            (PostStatus.AGENDADO, now_iso),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def save_metrics(post_id: int, likes: int, comentarios: int, saves: int, shares: int, config: Optional[AppConfig] = None) -> None:
    """Persist engagement metrics for a post."""

    cfg = config or load_config()
    conn = get_connection(cfg.db.db_path)
    try:
        conn.execute(
            """
            UPDATE posts
            SET likes = ?, comentarios = ?, saves = ?, shares = ?
            WHERE id = ?
            """,
            (likes, comentarios, saves, shares, post_id),
        )
        conn.commit()
        LOGGER.info("Saved metrics for post %s", post_id)
    finally:
        conn.close()


def bulk_insert_posts(entries: Iterable[dict[str, Any]], config: Optional[AppConfig] = None) -> list[int]:
    """Insert multiple post drafts and return their IDs."""

    ids: list[int] = []
    for entry in entries:
        ids.append(
            insert_post(
                tipo_post=entry.get("tipo_post", ""),
                signo=entry.get("signo"),
                tema=entry.get("tema"),
                texto_imagem=entry.get("texto_imagem", ""),
                legenda=entry.get("legenda", ""),
                hashtags=entry.get("hashtags", ""),
                status=entry.get("status", PostStatus.RASCUNHO),
                imagem_path=entry.get("imagem_path"),
                data_publicacao_planejada=entry.get("data_publicacao_planejada"),
                config=config,
            )
        )
    return ids


__all__ = [
    "PostStatus",
    "PostRecord",
    "init_db",
    "insert_post",
    "bulk_insert_posts",
    "update_post_status",
    "get_posts_by_status",
    "get_posts_without_schedule",
    "get_posts_due",
    "save_metrics",
]
