# modules/app_bootstrap.py
from __future__ import annotations

import logging
from typing import Tuple

from sqlalchemy import text

from .db import Base, engine

log = logging.getLogger(__name__)

_BOOTSTRAP_DONE: bool = False
_BOOTSTRAP_MSG: str | None = None


def init_models_and_migrate() -> None:
    """Inicializa os modelos e aplica migrações idempotentes."""

    # Cria tabelas que ainda não existem
    Base.metadata.create_all(bind=engine)

    # Ajusta colunas da tabela patients conforme o modelo Patient
    migrate_patients_table()


def migrate_patients_table() -> None:
    """Aplica migrações mínimas à tabela ``patients`` de forma idempotente."""

    with engine.begin() as conn:
        dialect = engine.dialect.name

        if dialect == "postgresql":
            # Cada ALTER é idempotente via IF NOT EXISTS
            conn.execute(
                text(
                    """
                    ALTER TABLE patients
                    ADD COLUMN IF NOT EXISTS status_pagamento TEXT NOT NULL DEFAULT 'pendente';
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE patients
                    ADD COLUMN IF NOT EXISTS status_plano TEXT NOT NULL DEFAULT 'nao_gerado';
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE patients
                    ADD COLUMN IF NOT EXISTS plano_ia JSONB NOT NULL DEFAULT '{}'::jsonb;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE patients
                    ADD COLUMN IF NOT EXISTS substituicoes JSONB NOT NULL DEFAULT '{}'::jsonb;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE patients
                    ADD COLUMN IF NOT EXISTS cardapio_ia JSONB NOT NULL DEFAULT '{}'::jsonb;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE patients
                    ADD COLUMN IF NOT EXISTS pdf_completo_url TEXT NULL;
                    """
                )
            )

            log.info("Migração patients (PostgreSQL) aplicada com sucesso.")

        else:
            # SQLite / ambiente local: checa colunas existentes via PRAGMA
            rows = conn.execute(text("PRAGMA table_info(patients)")).all()
            existing_cols = {r[1] for r in rows}

            def add_if_missing(colname: str, ddl: str) -> None:
                if colname not in existing_cols:
                    conn.execute(text(f"ALTER TABLE patients ADD COLUMN {ddl}"))

            add_if_missing(
                "status_pagamento",
                "status_pagamento TEXT NOT NULL DEFAULT 'pendente'",
            )
            add_if_missing(
                "status_plano",
                "status_plano TEXT NOT NULL DEFAULT 'nao_gerado'",
            )
            add_if_missing(
                "plano_ia",
                "plano_ia JSON NOT NULL DEFAULT '{}'",
            )
            add_if_missing(
                "substituicoes",
                "substituicoes JSON NOT NULL DEFAULT '{}'",
            )
            add_if_missing(
                "cardapio_ia",
                "cardapio_ia JSON NOT NULL DEFAULT '{}'",
            )
            add_if_missing(
                "pdf_completo_url",
                "pdf_completo_url TEXT NULL",
            )

            log.info("Migração patients (SQLite) aplicada com sucesso.")


def ensure_bootstrap() -> Tuple[bool, str | None]:
    """Garante que o banco esteja pronto antes de usar a aplicação."""

    global _BOOTSTRAP_DONE, _BOOTSTRAP_MSG

    if _BOOTSTRAP_DONE:
        return True, _BOOTSTRAP_MSG

    try:
        # Importa o módulo de modelos para registrar metadata no SQLAlchemy.
        import modules.repo  # noqa: F401  # pylint: disable=unused-import

        init_models_and_migrate()
    except Exception as exc:  # pragma: no cover - diagnóstico em produção
        log.exception("Falha ao executar bootstrap da aplicação")
        _BOOTSTRAP_DONE = False
        _BOOTSTRAP_MSG = str(exc)
        return False, _BOOTSTRAP_MSG

    _BOOTSTRAP_DONE = True
    _BOOTSTRAP_MSG = "Bootstrap executado com sucesso."
    log.info(_BOOTSTRAP_MSG)
    return True, _BOOTSTRAP_MSG
