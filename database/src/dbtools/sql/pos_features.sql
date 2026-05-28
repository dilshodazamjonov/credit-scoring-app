DROP TABLE IF EXISTS "{ml_schema}"."stg_pos_features";

CREATE TABLE "{ml_schema}"."stg_pos_features" AS
SELECT
    "SK_ID_CURR",
    MIN("MONTHS_BALANCE") AS "POS_MONTHS_BALANCE_MIN",
    VAR_SAMP("MONTHS_BALANCE") AS "POS_MONTHS_BALANCE_VAR"
FROM "{raw_schema}"."raw_pos_cash_balance"
GROUP BY "SK_ID_CURR";

