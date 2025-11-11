# modules/db.py
from __future__ import annotations

import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# DATABASE_URL + caminho absoluto do SQLite (evita múltiplos local.db por CWD)
# -----------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "local.db")
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

dialect = DATABASE_URL.split(":", 1)[0] if ":" in DATABASE_URL else "unknown"
if DATABASE_URL == DEFAULT_SQLITE_URL:
    log.warning("DATABASE_URL ausente; usando SQLite local (MVP). Configure no Render em produção.")

# Log seguro (sem expor credenciais)
log.info(
    "DB init: dialect_hint=%s url_hint=%s",
    dialect,
    "sqlite:///<projeto>/local.db" if dialect == "sqlite" else "postgresql://***",
)

# -----------------------------------------------------------------------------
# Engine por dialeto
# -----------------------------------------------------------------------------
if DATABASE_URL.startswith("sqlite:///"):
    # Dev/test local: estabilidade de thread e pool para apps single-process (ex.: Streamlit)
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Produção (Postgres ou outro): pre_ping evita conexões mortas no pool
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

log.info(
    "DB engine ready: dialect=%s pool=%s target=%s",
    engine.dialect.name,
    type(engine.pool).__name__,
    DEFAULT_SQLITE_PATH if engine.dialect.name == "sqlite" else "postgresql://***",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -----------------------------------------------------------------------------
# Helpers de dialeto (úteis para logs/condicionais)
# -----------------------------------------------------------------------------
def is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"

def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"

# -----------------------------------------------------------------------------
# Context manager de sessão
# -----------------------------------------------------------------------------
def session_scope():
    from contextlib import contextmanager

    @contextmanager
    def _scope():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return _scope()

# -----------------------------------------------------------------------------
# Init (create_all)
# -----------------------------------------------------------------------------
def init_models():
    import modules.repo  # garante que modelos sejam importados
    Base.metadata.create_all(bind=engine)
    log.info(
        "DB models initialized on %s",
        "SQLite" if is_sqlite() else engine.dialect.name,
    )
