from __future__ import annotations

import argparse

from dbtools.create_tables import create_ml_feature_snapshot_table
from dbtools.raw_loader import (
    DEFAULT_PATHS,
    check_credentials,
    create_db_engine,
    get_credentials,
    load_raw_csvs_to_postgres,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="database",
        description="Database ETL and validation commands.",
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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command in {"check_credentials", "check-credentials"}:
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
        return 0

    if args.command in {"load_raw_files", "load-raw-files"}:
        credentials = get_credentials()
        engine = create_db_engine(credentials)
        load_raw_csvs_to_postgres(
            engine,
            DEFAULT_PATHS,
            schema=args.schema,
            sample_rows=args.sample_rows,
        )
        print(f"Loaded {len(DEFAULT_PATHS)} raw tables into schema '{args.schema}'.")
        return 0

    if args.command in {
        "create_feature_snapshot_table",
        "create-feature-snapshot-table",
    }:
        credentials = get_credentials()
        engine = create_db_engine(credentials)
        create_ml_feature_snapshot_table(engine, schema=args.schema)
        print(
            f'Created table "{args.schema}"."ml_feature_snapshot" if it did not exist.'
        )
        return 0

    parser.error("Unknown command.")
    return 2
