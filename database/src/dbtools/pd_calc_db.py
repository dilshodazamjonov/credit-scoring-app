from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import joblib
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from dbtools.logging_utils import get_logger, log_step

logger = get_logger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = PACKAGE_DIR.parents[1]
REPO_ROOT = DATABASE_DIR.parent
DEFAULT_FEATURE_SPEC_PATH = REPO_ROOT / "gateway" / "schema" / "catboost_production_bundle.json"
DEFAULT_MODEL_BUNDLE_PATH = REPO_ROOT / "ml-service" / "models" / "catboost_production_bundle.joblib"
DEFAULT_MODEL_IMPORT_ROOT = REPO_ROOT / "ml-service"


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    dtype: str


@dataclass(frozen=True)
class FeatureSpec:
    model_name: str
    threshold: float
    required_features_count: int
    features: list[FeatureDefinition]

    @property
    def feature_names(self) -> list[str]:
        return [feature.name for feature in self.features]


@dataclass(frozen=True)
class ScoreResult:
    score_id: str
    application_id: int
    snapshot_id: str | None
    model_version: str
    pd_score: float
    score_band: str
    threshold: float
    null_feature_count: int


@dataclass(frozen=True)
class FeatureSnapshot:
    snapshot_id: str
    applicant_id: int
    feature_version: str
    features_json: dict[str, Any]
    feature_count: int
    source_application_rows: int
    source_bureau_rows: int


def score_applicant_from_db(
    engine: Engine,
    applicant_id: int,
    *,
    schema: str = "ml",
    raw_schema: str = "raw",
    table_name: str = "ml_applicant_features",
    feature_spec_path: str | Path = DEFAULT_FEATURE_SPEC_PATH,
    model_bundle_path: str | Path = DEFAULT_MODEL_BUNDLE_PATH,
    snapshot_id: str | None = None,
    persist_result: bool = True,
) -> ScoreResult:
    feature_spec = load_feature_spec(feature_spec_path)
    model_bundle = load_model_bundle(model_bundle_path)

    with log_step(
        logger,
        "score_applicant_from_db",
        applicant_id=applicant_id,
        schema=schema,
        table=table_name,
        persist_result=persist_result,
    ):
        with engine.begin() as conn:
            validate_feature_table_columns(
                conn,
                feature_spec,
                schema=schema,
                table_name=table_name,
            )
            applicant_features = fetch_applicant_features(
                conn,
                applicant_id,
                feature_spec,
                schema=schema,
                table_name=table_name,
            )
            source_row_counts = fetch_source_row_counts(
                conn,
                applicant_id,
                raw_schema=raw_schema,
            )
            feature_snapshot = build_feature_snapshot(
                applicant_id,
                applicant_features,
                feature_spec,
                snapshot_id=snapshot_id,
                source_application_rows=source_row_counts["source_application_rows"],
                source_bureau_rows=source_row_counts["source_bureau_rows"],
            )
            probability = float(model_bundle.predict_prob(applicant_features)[0])
            score_result = ScoreResult(
                score_id=str(uuid4()),
                application_id=applicant_id,
                snapshot_id=feature_snapshot.snapshot_id,
                model_version=feature_spec.model_name,
                pd_score=probability,
                score_band=derive_score_band(probability, feature_spec.threshold),
                threshold=feature_spec.threshold,
                null_feature_count=int(applicant_features.isna().sum(axis=1).iloc[0]),
            )
            logger.info(
                "applicant_scored applicant_id=%s pd_score=%.6f score_band=%s null_feature_count=%s",
                applicant_id,
                score_result.pd_score,
                score_result.score_band,
                score_result.null_feature_count,
            )
            if persist_result:
                ensure_feature_snapshot_table(conn, schema=schema)
                save_feature_snapshot(conn, feature_snapshot, schema=schema)
                ensure_score_result_table(conn, schema=schema)
                save_score_result(conn, score_result, schema=schema)
        return score_result


def load_feature_spec(path: str | Path) -> FeatureSpec:
    spec_path = Path(path)
    with log_step(logger, "load_feature_spec", path=spec_path):
        with spec_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        features = [
            FeatureDefinition(name=item["name"], dtype=item["type"])
            for item in data["features"]
        ]
        feature_names = [feature.name for feature in features]
        duplicates = sorted({name for name in feature_names if feature_names.count(name) > 1})
        if duplicates:
            raise ValueError(f"Duplicate feature names in feature spec: {', '.join(duplicates)}")

        required_features_count = int(data["required_features_count"])
        if required_features_count != len(features):
            raise ValueError(
                "Feature spec count mismatch: "
                f"required_features_count={required_features_count}, actual={len(features)}"
            )

        return FeatureSpec(
            model_name=data["model_name"],
            threshold=float(data["threshold"]),
            required_features_count=required_features_count,
            features=features,
        )


def load_model_bundle(path: str | Path) -> Any:
    bundle_path = Path(path)
    with log_step(logger, "load_model_bundle", path=bundle_path):
        import_root = os.path.abspath(DEFAULT_MODEL_IMPORT_ROOT)
        if import_root not in sys.path:
            sys.path.insert(0, import_root)
        return joblib.load(bundle_path)


def validate_feature_table_columns(
    conn: Connection,
    feature_spec: FeatureSpec,
    *,
    schema: str,
    table_name: str,
) -> None:
    sql = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema_name
          AND table_name = :table_name
        """
    )
    result = conn.execute(
        sql,
        {"schema_name": schema, "table_name": table_name},
    )
    available_columns = {row[0] for row in result}
    missing_columns = [
        feature_name
        for feature_name in feature_spec.feature_names
        if feature_name not in available_columns
    ]
    if missing_columns:
        raise ValueError(
            "Applicant feature table is missing required model columns: "
            + ", ".join(missing_columns)
        )
    logger.info(
        "feature_table_validated schema=%s table=%s required_columns=%s",
        schema,
        table_name,
        len(feature_spec.feature_names),
    )


def fetch_applicant_features(
    conn: Connection,
    applicant_id: int,
    feature_spec: FeatureSpec,
    *,
    schema: str,
    table_name: str,
) -> pd.DataFrame:
    feature_columns = ", ".join(_quote_identifier(name) for name in feature_spec.feature_names)
    sql = text(
        f"""
        SELECT {feature_columns}
        FROM {_qualify_table(schema, table_name)}
        WHERE "SK_ID_CURR" = :applicant_id
        """
    )
    with log_step(
        logger,
        "fetch_applicant_features",
        applicant_id=applicant_id,
        schema=schema,
        table=table_name,
        features=len(feature_spec.feature_names),
    ):
        applicant_features = pd.read_sql_query(
            sql,
            conn,
            params={"applicant_id": applicant_id},
        )

    if applicant_features.empty:
        raise ValueError(
            f"No applicant features found for SK_ID_CURR={applicant_id} in {schema}.{table_name}"
        )
    if len(applicant_features) > 1:
        raise ValueError(
            f"Expected one applicant feature row for SK_ID_CURR={applicant_id}, "
            f"found {len(applicant_features)}"
        )

    missing_from_row = [
        feature_name
        for feature_name in feature_spec.feature_names
        if feature_name not in applicant_features.columns
    ]
    if missing_from_row:
        raise ValueError(
            "Fetched applicant row is missing required features: "
            + ", ".join(missing_from_row)
        )

    applicant_features = applicant_features.reindex(columns=feature_spec.feature_names)
    logger.info(
        "applicant_features_fetched applicant_id=%s null_feature_count=%s",
        applicant_id,
        int(applicant_features.isna().sum(axis=1).iloc[0]),
    )
    return applicant_features


def build_feature_snapshot(
    applicant_id: int,
    applicant_features: pd.DataFrame,
    feature_spec: FeatureSpec,
    *,
    snapshot_id: str | None,
    source_application_rows: int,
    source_bureau_rows: int,
) -> FeatureSnapshot:
    return FeatureSnapshot(
        snapshot_id=snapshot_id or str(uuid4()),
        applicant_id=applicant_id,
        feature_version=feature_spec.model_name,
        features_json=_dataframe_row_to_json_dict(applicant_features),
        feature_count=len(feature_spec.feature_names),
        source_application_rows=source_application_rows,
        source_bureau_rows=source_bureau_rows,
    )


def ensure_feature_snapshot_table(conn: Connection, *, schema: str = "ml") -> None:
    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    conn.execute(
        text(
            f'''
            CREATE TABLE IF NOT EXISTS "{schema}"."ml_feature_snapshot" (
                snapshot_id UUID PRIMARY KEY,
                applicant_id BIGINT NOT NULL,
                feature_version TEXT NOT NULL,
                features_json JSONB NOT NULL,
                feature_count INT NOT NULL,
                source_application_rows INT DEFAULT 0,
                source_bureau_rows INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            '''
        )
    )


def ensure_score_result_table(conn: Connection, *, schema: str = "ml") -> None:
    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    conn.execute(
        text(
            f'''
            CREATE TABLE IF NOT EXISTS "{schema}"."ml_score_result" (
                score_id UUID PRIMARY KEY,
                application_id BIGINT NOT NULL,
                snapshot_id UUID,
                model_version TEXT NOT NULL,
                pd_score DOUBLE PRECISION NOT NULL,
                score_band TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            '''
        )
    )


def save_feature_snapshot(
    conn: Connection,
    feature_snapshot: FeatureSnapshot,
    *,
    schema: str = "ml",
) -> None:
    sql = text(
        f"""
        INSERT INTO {_qualify_table(schema, "ml_feature_snapshot")} (
            snapshot_id,
            applicant_id,
            feature_version,
            features_json,
            feature_count,
            source_application_rows,
            source_bureau_rows
        ) VALUES (
            :snapshot_id,
            :applicant_id,
            :feature_version,
            CAST(:features_json AS JSONB),
            :feature_count,
            :source_application_rows,
            :source_bureau_rows
        )
        ON CONFLICT (snapshot_id) DO UPDATE
        SET applicant_id = EXCLUDED.applicant_id,
            feature_version = EXCLUDED.feature_version,
            features_json = EXCLUDED.features_json,
            feature_count = EXCLUDED.feature_count,
            source_application_rows = EXCLUDED.source_application_rows,
            source_bureau_rows = EXCLUDED.source_bureau_rows
        """
    )
    conn.execute(
        sql,
        {
            "snapshot_id": feature_snapshot.snapshot_id,
            "applicant_id": feature_snapshot.applicant_id,
            "feature_version": feature_snapshot.feature_version,
            "features_json": json.dumps(feature_snapshot.features_json),
            "feature_count": feature_snapshot.feature_count,
            "source_application_rows": feature_snapshot.source_application_rows,
            "source_bureau_rows": feature_snapshot.source_bureau_rows,
        },
    )
    logger.info(
        "feature_snapshot_saved application_id=%s snapshot_id=%s schema=%s",
        feature_snapshot.applicant_id,
        feature_snapshot.snapshot_id,
        schema,
    )


def fetch_source_row_counts(
    conn: Connection,
    applicant_id: int,
    *,
    raw_schema: str,
) -> dict[str, int]:
    application_rows = conn.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {_qualify_table(raw_schema, "raw_application")}
            WHERE "SK_ID_CURR" = :applicant_id
            """
        ),
        {"applicant_id": applicant_id},
    ).scalar_one()
    bureau_rows = conn.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {_qualify_table(raw_schema, "raw_bureau")}
            WHERE "SK_ID_CURR" = :applicant_id
            """
        ),
        {"applicant_id": applicant_id},
    ).scalar_one()
    return {
        "source_application_rows": int(application_rows),
        "source_bureau_rows": int(bureau_rows),
    }


def save_score_result(conn: Connection, score_result: ScoreResult, *, schema: str = "ml") -> None:
    sql = text(
        f"""
        INSERT INTO {_qualify_table(schema, "ml_score_result")} (
            score_id,
            application_id,
            snapshot_id,
            model_version,
            pd_score,
            score_band
        ) VALUES (
            :score_id,
            :application_id,
            :snapshot_id,
            :model_version,
            :pd_score,
            :score_band
        )
        """
    )
    conn.execute(
        sql,
        {
            "score_id": score_result.score_id,
            "application_id": score_result.application_id,
            "snapshot_id": score_result.snapshot_id,
            "model_version": score_result.model_version,
            "pd_score": score_result.pd_score,
            "score_band": score_result.score_band,
        },
    )
    logger.info(
        "score_result_saved application_id=%s score_id=%s schema=%s",
        score_result.application_id,
        score_result.score_id,
        schema,
    )


def derive_score_band(probability: float, threshold: float) -> str:
    if probability < threshold * 0.5:
        return "low_risk"
    if probability < threshold:
        return "medium_risk"
    return "high_risk"


def _qualify_table(schema: str, table_name: str) -> str:
    return f'{_quote_identifier(schema)}.{_quote_identifier(table_name)}'


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _dataframe_row_to_json_dict(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        raise ValueError("Cannot serialize an empty feature row into ml_feature_snapshot")
    row = df.iloc[0].to_dict()
    return {key: _normalize_json_value(value) for key, value in row.items()}


def _normalize_json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    return value
