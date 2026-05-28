DROP TABLE IF EXISTS "{ml_schema}"."stg_application_base";

CREATE TABLE "{ml_schema}"."stg_application_base" AS
SELECT
    "SK_ID_CURR",
    "AMT_CREDIT",
    "AMT_GOODS_PRICE",
    "DAYS_BIRTH",
    "DAYS_EMPLOYED",
    "EXT_SOURCE_1",
    "EXT_SOURCE_2",
    "EXT_SOURCE_3",
    "OCCUPATION_TYPE"
FROM "{raw_schema}"."raw_application";

