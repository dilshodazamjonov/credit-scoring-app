from __future__ import annotations

import argparse
import sys

from dbtools.create_tables import (
    create_ml_feature_snapshot_table,
    create_raw_link_indexes,
)
from dbtools.features_aggregation import build_ml_applicant_features
from dbtools.logging_utils import configure_logging, get_logger, log_step
from dbtools.raw_loader import (
    DEFAULT_PATHS,
    check_credentials,
    create_db_engine,
    get_credentials,
    load_raw_csvs_to_postgres,
    load_single_raw_csv_to_postgres,
)

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="database",
        description="Database ETL and validation commands.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override DBTOOLS_LOG_LEVEL for this run.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser(
        "check_credentials",
        aliases=["check-credentials"],
        help="Validate DB credentials, connectivity, and CSV inputs.",
    )
    check_parser.add_argument(
        "--schema",
        default="raw",
        help="Schema to inspect for raw-table loading.",
    )

    load_parser = subparsers.add_parser(
        "load_raw_files",
        aliases=["load-raw-files"],
        help="Create raw tables and bulk-load CSV files into Postgres.",
    )
    load_parser.add_argument(
        "--schema",
        default="raw",
        help="Schema to load the raw tables into.",
    )
    load_parser.add_argument(
        "--sample-rows",
        type=int,
        default=1000,
        help="Rows to sample for type inference before COPY.",
    )

    load_one_parser = subparsers.add_parser(
        "load_raw_file",
        aliases=["load-raw-file"],
        help="Create and bulk-load one raw table into Postgres.",
    )
    load_one_parser.add_argument(
        "--table",
        required=True,
        choices=sorted(DEFAULT_PATHS),
        help="Raw table name to load.",
    )
    load_one_parser.add_argument(
        "--schema",
        default="raw",
        help="Schema to load the raw table into.",
    )
    load_one_parser.add_argument(
        "--sample-rows",
        type=int,
        default=1000,
        help="Rows to sample for type inference before COPY.",
    )

    create_parser = subparsers.add_parser(
        "create_feature_snapshot_table",
        aliases=["create-feature-snapshot-table"],
        help="Create the ml_feature_snapshot table.",
    )
    create_parser.add_argument(
        "--schema",
        default="ml",
        help="Schema to create the feature snapshot table in.",
    )

    indexes_parser = subparsers.add_parser(
        "create_raw_link_indexes",
        aliases=["create-raw-link-indexes"],
        help="Create join/link indexes for the raw tables.",
    )
    indexes_parser.add_argument(
        "--schema",
        default="raw",
        help="Schema containing the raw tables.",
    )

    ml_features_parser = subparsers.add_parser(
        "create_ml_features",
        aliases=["create-ml-features"],
        help="Build the 40-feature ml_applicant_features table from raw sources.",
    )
    ml_features_parser.add_argument(
        "--all",
        action="store_true",
        help="Run the full production feature build pipeline.",
    )
    ml_features_parser.add_argument(
        "--schema",
        default="ml",
        help="Schema to save ml_applicant_features into.",
    )
    ml_features_parser.add_argument(
        "--raw-schema",
        default="raw",
        help="Schema containing the raw source tables.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    try:
        return _dispatch_command(args, parser)
    except Exception as exc:
        logger.exception("command_failed command=%s", args.command)
        print(f"database command failed: {exc}", file=sys.stderr)
        return 1


def _dispatch_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    logger.info("command_start command=%s", args.command)

    if args.command in {"check_credentials", "check-credentials"}:
        with log_step(logger, "command_check_credentials", schema=args.schema):
            report = check_credentials(DEFAULT_PATHS, schema=args.schema)
        print(f"Environment file: {report.env_path}")
        print(
            "Database: "
            f"{report.credentials.database}@{report.credentials.host}:{report.credentials.port}"
        )
        print("Connection: OK")
        print(
            f"Schema '{args.schema}': "
            f"{'present' if report.schema_exists else 'missing'}"
        )
        print(f"CSV files: {len(report.paths)} found")
        for table_name, path in report.paths.items():
            print(f"  {table_name}: {path}")
        logger.info("command_success command=%s", args.command)
        return 0

    if args.command in {"load_raw_files", "load-raw-files"}:
        credentials = get_credentials()
        engine = create_db_engine(credentials)
        try:
            load_raw_csvs_to_postgres(
                engine,
                DEFAULT_PATHS,
                schema=args.schema,
                sample_rows=args.sample_rows,
            )
        finally:
            engine.dispose()
        print(f"Loaded {len(DEFAULT_PATHS)} raw tables into schema '{args.schema}'.")
        logger.info("command_success command=%s", args.command)
        return 0

    if args.command in {"load_raw_file", "load-raw-file"}:
        credentials = get_credentials()
        engine = create_db_engine(credentials)
        try:
            load_single_raw_csv_to_postgres(
                engine,
                args.table,
                schema=args.schema,
                sample_rows=args.sample_rows,
            )
        finally:
            engine.dispose()
        print(f"Loaded raw table '{args.table}' into schema '{args.schema}'.")
        logger.info("command_success command=%s table=%s", args.command, args.table)
        return 0

    if args.command in {
        "create_feature_snapshot_table",
        "create-feature-snapshot-table",
    }:
        credentials = get_credentials()
        engine = create_db_engine(credentials)
        try:
            create_ml_feature_snapshot_table(engine, schema=args.schema)
        finally:
            engine.dispose()
        print(
            f'Created table "{args.schema}"."ml_feature_snapshot" if it did not exist.'
        )
        logger.info("command_success command=%s", args.command)
        return 0

    if args.command in {"create_raw_link_indexes", "create-raw-link-indexes"}:
        credentials = get_credentials()
        engine = create_db_engine(credentials)
        try:
            create_raw_link_indexes(engine, schema=args.schema)
        finally:
            engine.dispose()
        print(f'Created raw-table link indexes in schema "{args.schema}".')
        logger.info("command_success command=%s", args.command)
        return 0

    if args.command in {"create_ml_features", "create-ml-features"}:
        credentials = get_credentials()
        engine = create_db_engine(credentials)
        try:
            build_ml_applicant_features(
                engine,
                raw_schema=args.raw_schema,
                ml_schema=args.schema,
            )
        finally:
            engine.dispose()
        print(
            f'Built "{args.schema}"."ml_applicant_features" from '
            f'"{args.raw_schema}" raw tables.'
        )
        logger.info("command_success command=%s", args.command)
        return 0

    parser.error("Unknown command.")
    return 2
