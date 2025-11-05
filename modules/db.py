# modules/db.py
from __future__ import annotations

import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

log = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///local.db"
    log.warning(
        "DATABASE_URL ausente; usando SQLite local (MVP). Configure no Render em produção."
    )

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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


def init_models():
    import modules.repo  # garante que modelos sejam importados

    Base.metadata.create_all(bind=engine)
