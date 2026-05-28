DROP TABLE IF EXISTS "{ml_schema}"."stg_installments_features";

CREATE TABLE "{ml_schema}"."stg_installments_features" AS
WITH installments_enriched AS (
    SELECT
        "SK_ID_CURR",
        "DAYS_ENTRY_PAYMENT",
        "DAYS_INSTALMENT",
        "AMT_PAYMENT",
        "AMT_INSTALMENT",
        "DAYS_ENTRY_PAYMENT" - "DAYS_INSTALMENT" AS days_diff,
        CASE
            WHEN "DAYS_ENTRY_PAYMENT" IS NULL OR "DAYS_INSTALMENT" IS NULL THEN NULL
            WHEN "DAYS_ENTRY_PAYMENT" - "DAYS_INSTALMENT" > 0 THEN 1.0
            ELSE 0.0
        END AS is_late,
        CASE
            WHEN "AMT_INSTALMENT" IS NULL OR "AMT_INSTALMENT" = 0 THEN NULL
            ELSE "AMT_PAYMENT" / "AMT_INSTALMENT"
        END AS payment_ratio
    FROM "{raw_schema}"."raw_installments_payments"
)
SELECT
    "SK_ID_CURR",
    SUM(days_diff) AS "INSTAL_DAYS_DIFF_SUM",
    AVG(is_late) AS "INSTAL_IS_LATE_MEAN",
    AVG(payment_ratio) AS "INSTAL_PAYMENT_RATIO_MEAN",
    MIN(payment_ratio) AS "INSTAL_PAYMENT_RATIO_MIN",
    VAR_SAMP(payment_ratio) AS "INSTAL_PAYMENT_RATIO_VAR"
FROM installments_enriched
GROUP BY "SK_ID_CURR";

