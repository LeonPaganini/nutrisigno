# modules/app_bootstrap.py
from __future__ import annotations

import logging

from sqlalchemy import text

from .db import engine, Base

log = logging.getLogger(__name__)


def init_models_and_migrate() -> None:
    """
    Inicializa os modelos (create_all) e aplica migrações mínimas
    necessárias para alinhar a tabela patients ao modelo atual.
    Deve ser chamada no boot da aplicação (ex.: app.py).
    """
    # Cria tabelas que ainda não existem
    Base.metadata.create_all(bind=engine)

    # Ajusta colunas da tabela patients conforme o modelo Patient
    migrate_patients_table()


def migrate_patients_table() -> None:
    """
    Migração idempotente da tabela patients.
    - Adiciona colunas de status_pagamento, status_plano, plano_ia,
      substituicoes, cardapio_ia, pdf_completo_url se não existirem.
    - Funciona tanto em PostgreSQL quanto em SQLite local.
    """
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