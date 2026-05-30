CREATE TABLE IF NOT EXISTS ml.ml_score_result (
    score_id UUID PRIMARY KEY, 
    application_id BIGINT NOT NULL,
    snapshot_id UUID,
    model_version TEXT NOT NULL,
    pd_score FLOAT NOT NULL,
    score_band TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


