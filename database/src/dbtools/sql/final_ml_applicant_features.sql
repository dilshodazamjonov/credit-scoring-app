DROP TABLE IF EXISTS "{ml_schema}"."ml_applicant_features";

CREATE TABLE "{ml_schema}"."ml_applicant_features" AS
SELECT
    app."SK_ID_CURR",
    app."AMT_CREDIT",
    app."AMT_GOODS_PRICE",
    bureau."BURO_AMT_CREDIT_SUM_DEBT_MEAN",
    bureau."BURO_DAYS_CREDIT_ENDDATE_MAX",
    bureau."BURO_DAYS_CREDIT_ENDDATE_SUM",
    bureau."BURO_DAYS_CREDIT_MEAN",
    bureau."BURO_DAYS_CREDIT_SUM",
    bureau."BURO_DAYS_CREDIT_UPDATE_MAX",
    bureau."BURO_DAYS_CREDIT_UPDATE_VAR",
    bureau."BURO_DAYS_ENDDATE_FACT_MEAN",
    bureau."BURO_DAYS_ENDDATE_FACT_MIN",
    bureau."BURO_DEBT_CREDIT_DIFF_MAX",
    bureau."BURO_DEBT_CREDIT_DIFF_MIN",
    bureau."BURO_DEBT_RATIO_MAX",
    bureau."BURO_DEBT_RATIO_MEAN",
    bureau."BURO_DEBT_RATIO_SUM",
    bureau."BURO_DEBT_RATIO_VAR",
    app."DAYS_BIRTH",
    app."DAYS_EMPLOYED",
    app."EXT_SOURCE_1",
    app."EXT_SOURCE_2",
    app."EXT_SOURCE_3",
    instal."INSTAL_DAYS_DIFF_SUM",
    instal."INSTAL_IS_LATE_MEAN",
    instal."INSTAL_PAYMENT_RATIO_MEAN",
    instal."INSTAL_PAYMENT_RATIO_MIN",
    instal."INSTAL_PAYMENT_RATIO_VAR",
    app."OCCUPATION_TYPE",
    pos."POS_MONTHS_BALANCE_MIN",
    pos."POS_MONTHS_BALANCE_VAR",
    prev."PREV_DAYS_DECISION_VAR",
    prev."PREV_DAYS_FIRST_DRAWING_SUM",
    prev."PREV_DAYS_FIRST_DUE_MEAN",
    prev."PREV_DAYS_FIRST_DUE_VAR",
    prev."PREV_DAYS_LAST_DUE_1ST_VERSION_MEAN",
    prev."PREV_INTEREST_ESTIMATE_MAX",
    prev."PREV_INTEREST_ESTIMATE_MEAN",
    prev."PREV_INTEREST_ESTIMATE_MIN",
    prev."PREV_INTEREST_ESTIMATE_VAR",
    bureau."recent_decision_bureau"
FROM "{ml_schema}"."stg_application_base" AS app
LEFT JOIN "{ml_schema}"."stg_bureau_features" AS bureau
    ON app."SK_ID_CURR" = bureau."SK_ID_CURR"
LEFT JOIN "{ml_schema}"."stg_installments_features" AS instal
    ON app."SK_ID_CURR" = instal."SK_ID_CURR"
LEFT JOIN "{ml_schema}"."stg_pos_features" AS pos
    ON app."SK_ID_CURR" = pos."SK_ID_CURR"
LEFT JOIN "{ml_schema}"."stg_previous_application_features" AS prev
    ON app."SK_ID_CURR" = prev."SK_ID_CURR";

CREATE INDEX IF NOT EXISTS "ix_{ml_schema}_ml_applicant_features_sk_id_curr"
ON "{ml_schema}"."ml_applicant_features" ("SK_ID_CURR");

