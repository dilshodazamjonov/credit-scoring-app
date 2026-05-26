from sqlalchemy import text


def create_ml_feature_snapshot_table(engine, schema: str = "ml") -> None:
    with engine.begin() as conn:
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

    
