from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from dbtools.logging_utils import get_logger, log_step

SQL_DIR = Path(__file__).resolve().parent / "sql"
SQL_PIPELINE = [
    "application_base.sql",
    "bureau_features.sql",
    "installments_features.sql",
    "pos_features.sql",
    "previous_application_features.sql",
    "final_ml_applicant_features.sql",
]
logger = get_logger(__name__)


def build_ml_applicant_features(
    engine: Engine,
    *,
    raw_schema: str = "raw",
    ml_schema: str = "ml",
) -> None:
    with log_step(
        logger,
        "ml_features_build",
        raw_schema=raw_schema,
        ml_schema=ml_schema,
        steps=len(SQL_PIPELINE),
    ):
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{ml_schema}"'))
            for sql_file in SQL_PIPELINE:
                _run_sql_file(conn, sql_file, raw_schema=raw_schema, ml_schema=ml_schema)


def agg_application_base(
    conn: Connection,
    *,
    raw_schema: str = "raw",
    ml_schema: str = "ml",
) -> None:
    _run_sql_file(
        conn,
        "application_base.sql",
        raw_schema=raw_schema,
        ml_schema=ml_schema,
    )


def agg_bureau_features(
    conn: Connection,
    *,
    raw_schema: str = "raw",
    ml_schema: str = "ml",
) -> None:
    _run_sql_file(
        conn,
        "bureau_features.sql",
        raw_schema=raw_schema,
        ml_schema=ml_schema,
    )


def agg_installments_features(
    conn: Connection,
    *,
    raw_schema: str = "raw",
    ml_schema: str = "ml",
) -> None:
    _run_sql_file(
        conn,
        "installments_features.sql",
        raw_schema=raw_schema,
        ml_schema=ml_schema,
    )


def agg_pos_features(
    conn: Connection,
    *,
    raw_schema: str = "raw",
    ml_schema: str = "ml",
) -> None:
    _run_sql_file(
        conn,
        "pos_features.sql",
        raw_schema=raw_schema,
        ml_schema=ml_schema,
    )


def agg_previous_application_features(
    conn: Connection,
    *,
    raw_schema: str = "raw",
    ml_schema: str = "ml",
) -> None:
    _run_sql_file(
        conn,
        "previous_application_features.sql",
        raw_schema=raw_schema,
        ml_schema=ml_schema,
    )


def build_final_ml_applicant_features(
    conn: Connection,
    *,
    raw_schema: str = "raw",
    ml_schema: str = "ml",
) -> None:
    _run_sql_file(
        conn,
        "final_ml_applicant_features.sql",
        raw_schema=raw_schema,
        ml_schema=ml_schema,
    )


def _run_sql_file(
    conn: Connection,
    sql_file: str,
    *,
    raw_schema: str,
    ml_schema: str,
) -> None:
    sql_path = SQL_DIR / sql_file
    with log_step(
        logger,
        "sql_pipeline_step",
        file=sql_file,
        raw_schema=raw_schema,
        ml_schema=ml_schema,
    ):
        sql = sql_path.read_text(encoding="utf-8").format(
            raw_schema=_quote_identifier(raw_schema),
            ml_schema=_quote_identifier(ml_schema),
        )
        conn.exec_driver_sql(sql)


def _quote_identifier(value: str) -> str:
    return value.replace('"', '""')
