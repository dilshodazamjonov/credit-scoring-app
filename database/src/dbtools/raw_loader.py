from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from tqdm import tqdm

from dbtools.logging_utils import get_logger, log_step

PACKAGE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = PACKAGE_DIR.parents[1]
REPO_ROOT = DATABASE_DIR.parent
ENV_PATH = REPO_ROOT / ".env"
DEFAULT_SCHEMA = "raw"
DEFAULT_DB_NAME = "credit_scoring_db"
DEFAULT_PATHS = {
    "raw_application": DATABASE_DIR / "data" / "application_train.csv",
    "raw_bureau": DATABASE_DIR / "data" / "bureau.csv",
    "raw_previous_application": DATABASE_DIR / "data" / "previous_application.csv",
    "raw_installments_payments": DATABASE_DIR / "data" / "installments_payments.csv",
    "raw_credit_card_balance": DATABASE_DIR / "data" / "credit_card_balance.csv",
    "raw_pos_cash_balance": DATABASE_DIR / "data" / "POS_CASH_balance.csv",
}

load_dotenv(ENV_PATH)
logger = get_logger(__name__)


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str
    host: str
    port: int
    database: str


@dataclass(frozen=True)
class CheckReport:
    credentials: Credentials
    env_path: Path
    paths: dict[str, Path]
    schema_exists: bool


def get_credentials() -> Credentials:
    username = os.environ.get("db_username")
    password = os.environ.get("db_password")
    host = os.environ.get("db_host", "localhost")
    port = int(os.environ.get("db_port", "5432"))
    database = os.environ.get("db_name", DEFAULT_DB_NAME)

    missing = []
    if not username:
        missing.append("db_username")
    if not password:
        missing.append("db_password")

    if missing:
        raise ValueError(f"Missing required database env vars: {', '.join(missing)}")

    logger.info(
        "db_credentials_loaded database=%s host=%s port=%s user=%s",
        database,
        host,
        port,
        username,
    )
    return Credentials(
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )


def create_db_engine(credentials: Credentials) -> Engine:
    connection_url = URL.create(
        "postgresql+psycopg2",
        username=credentials.username,
        password=credentials.password,
        host=credentials.host,
        port=credentials.port,
        database=credentials.database,
    )
    logger.info(
        "db_engine_create database=%s host=%s port=%s",
        credentials.database,
        credentials.host,
        credentials.port,
    )
    return create_engine(connection_url, pool_pre_ping=True)


def check_credentials(
    paths: Mapping[str, str | Path] | None = None,
    *,
    schema: str = DEFAULT_SCHEMA,
) -> CheckReport:
    resolved_paths = resolve_paths(paths or DEFAULT_PATHS)
    missing_files = [str(path) for path in resolved_paths.values() if not path.exists()]
    if missing_files:
        raise FileNotFoundError(
            "Missing CSV files required for raw loading: " + ", ".join(missing_files)
        )

    credentials = get_credentials()
    engine = create_db_engine(credentials)
    with log_step(
        logger,
        "db_healthcheck",
        schema=schema,
        files=len(resolved_paths),
    ):
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            schema_exists = bool(
                connection.execute(
                    text(
                        """
                        SELECT EXISTS (
                            SELECT 1
                            FROM information_schema.schemata
                            WHERE schema_name = :schema_name
                        )
                        """
                    ),
                    {"schema_name": schema},
                ).scalar_one()
            )
    engine.dispose()

    return CheckReport(
        credentials=credentials,
        env_path=ENV_PATH,
        paths=resolved_paths,
        schema_exists=schema_exists,
    )


def load_raw_csvs_to_postgres(
    engine: Engine,
    paths: Mapping[str, str | Path],
    *,
    schema: str = DEFAULT_SCHEMA,
    sample_rows: int = 1000,
) -> None:
    resolved_paths = resolve_paths(paths)
    _ensure_schema(engine, schema)

    with log_step(
        logger,
        "raw_load_batch",
        schema=schema,
        tables=len(resolved_paths),
        sample_rows=sample_rows,
    ):
        for table_name, csv_path in tqdm(resolved_paths.items(), desc="Loading raw tables"):
            _load_single_table(
                engine,
                table_name,
                csv_path,
                schema=schema,
                sample_rows=sample_rows,
            )


def load_single_raw_csv_to_postgres(
    engine: Engine,
    table_name: str,
    *,
    schema: str = DEFAULT_SCHEMA,
    sample_rows: int = 1000,
) -> None:
    if table_name not in DEFAULT_PATHS:
        valid_tables = ", ".join(sorted(DEFAULT_PATHS))
        raise ValueError(
            f"Unknown raw table '{table_name}'. Valid options: {valid_tables}"
        )

    resolved_paths = resolve_paths({table_name: DEFAULT_PATHS[table_name]})
    csv_path = resolved_paths[table_name]
    _ensure_schema(engine, schema)
    _load_single_table(
        engine,
        table_name,
        csv_path,
        schema=schema,
        sample_rows=sample_rows,
    )


def resolve_paths(paths: Mapping[str, str | Path]) -> dict[str, Path]:
    resolved: dict[str, Path] = {}

    for table_name, raw_path in paths.items():
        path = Path(raw_path)
        if path.is_absolute():
            resolved[table_name] = path
            continue

        database_relative = (DATABASE_DIR / path).resolve()
        repo_relative = (REPO_ROOT / path).resolve()
        resolved[table_name] = database_relative if database_relative.exists() else repo_relative
        logger.debug("path_resolved table=%s path=%s", table_name, resolved[table_name])

    return resolved


def _ensure_schema(engine: Engine, schema: str) -> None:
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema)}"))
    logger.info("schema_ensured schema=%s", schema)


def _load_single_table(
    engine: Engine,
    table_name: str,
    csv_path: Path,
    *,
    schema: str,
    sample_rows: int,
) -> None:
    with log_step(
        logger,
        "raw_table_load",
        schema=schema,
        table=table_name,
        path=csv_path,
    ):
        columns = _create_table_from_sample(
            engine,
            table_name,
            csv_path,
            schema=schema,
            sample_rows=sample_rows,
        )
        row_count = _copy_csv_to_table(
            engine,
            table_name,
            csv_path,
            columns,
            schema=schema,
        )
        logger.info(
            "raw_table_loaded schema=%s table=%s columns=%s rows=%s",
            schema,
            table_name,
            len(columns),
            row_count,
        )


def _create_table_from_sample(
    engine: Engine,
    table_name: str,
    csv_path: Path,
    *,
    schema: str,
    sample_rows: int,
) -> list[str]:
    logger.info(
        "raw_table_sample schema=%s table=%s sample_rows=%s path=%s",
        schema,
        table_name,
        sample_rows,
        csv_path,
    )
    sample = pd.read_csv(csv_path, nrows=sample_rows, low_memory=False)
    headers = sample.columns.tolist()
    sample.head(0).to_sql(
        table_name,
        engine,
        schema=schema,
        if_exists="replace",
        index=False,
    )
    return headers


def _copy_csv_to_table(
    engine: Engine,
    table_name: str,
    csv_path: Path,
    columns: list[str],
    *,
    schema: str,
) -> int:
    quoted_columns = ", ".join(_quote_identifier(column) for column in columns)
    quoted_table = f"{_quote_identifier(schema)}.{_quote_identifier(table_name)}"
    copy_sql = (
        f"COPY {quoted_table} ({quoted_columns}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    )

    raw_connection = engine.raw_connection()
    try:
        with raw_connection.cursor() as cursor:
            with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
                cursor.copy_expert(copy_sql, csv_file)
        raw_connection.commit()
        row_count = _fetch_row_count(engine, table_name, schema=schema)
        return row_count
    except Exception:
        raw_connection.rollback()
        raise
    finally:
        raw_connection.close()


def _fetch_row_count(engine: Engine, table_name: str, *, schema: str) -> int:
    sql = text(
        f'SELECT COUNT(*) FROM {_quote_identifier(schema)}.{_quote_identifier(table_name)}'
    )
    with engine.connect() as connection:
        return int(connection.execute(sql).scalar_one())


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


