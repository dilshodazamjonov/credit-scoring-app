from sqlalchemy import text
from sqlalchemy.engine import Engine

def create_ml_feature_snapshot_table(engine: Engine, schema: str = "ml") -> None:
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


def create_raw_link_indexes(engine: Engine, schema: str = "raw") -> None:
    statements = [
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_application_sk_id_curr"
        ON "{schema}"."raw_application" ("SK_ID_CURR");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_bureau_sk_id_curr"
        ON "{schema}"."raw_bureau" ("SK_ID_CURR");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_bureau_sk_id_bureau"
        ON "{schema}"."raw_bureau" ("SK_ID_BUREAU");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_previous_application_sk_id_curr"
        ON "{schema}"."raw_previous_application" ("SK_ID_CURR");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_previous_application_sk_id_prev"
        ON "{schema}"."raw_previous_application" ("SK_ID_PREV");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_installments_payments_sk_id_curr"
        ON "{schema}"."raw_installments_payments" ("SK_ID_CURR");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_installments_payments_sk_id_prev"
        ON "{schema}"."raw_installments_payments" ("SK_ID_PREV");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_credit_card_balance_sk_id_curr"
        ON "{schema}"."raw_credit_card_balance" ("SK_ID_CURR");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_credit_card_balance_sk_id_prev"
        ON "{schema}"."raw_credit_card_balance" ("SK_ID_PREV");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_pos_cash_balance_sk_id_curr"
        ON "{schema}"."raw_pos_cash_balance" ("SK_ID_CURR");
        ''',
        f'''
        CREATE INDEX IF NOT EXISTS "ix_{schema}_raw_pos_cash_balance_sk_id_prev"
        ON "{schema}"."raw_pos_cash_balance" ("SK_ID_PREV");
        ''',
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
