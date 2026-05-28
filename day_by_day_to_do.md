## Day 1

Keep tomorrow small. Create the tables in this order.

### 1. Create the raw source tables

These hold the original dataset.

```text
raw_application
raw_bureau
raw_previous_application
raw_installments_payments
raw_credit_card_balance
raw_pos_cash_balance
```

### 2. Create `ml_feature_snapshot`

Meaning:

Stores the exact generated feature row for one scoring attempt.

For tomorrow, keep it simple with JSONB.

```sql
CREATE TABLE IF NOT EXISTS ml_feature_snapshot (
    snapshot_id UUID PRIMARY KEY,
    applicant_id BIGINT NOT NULL,
    feature_version TEXT NOT NULL,
    features_json JSONB NOT NULL,
    feature_count INT NOT NULL,
    source_application_rows INT DEFAULT 0,
    source_bureau_rows INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Keep the goal in mind

This table is important because later you can say:

For applicant 100001, these exact features were used at this time.

That is the beginning of real auditability.


### 4. In short 
1. Create raw and ml schemas.
2. Load all CSVs into raw tables.
3. Create ml_applicant_features using Python.
4. Save the feature table into PostgreSQL.
5. Add index on SK_ID_CURR.
6. Test one query:
   SELECT * FROM ml.ml_applicant_features WHERE "SK_ID_CURR" = 100001;


# Day 2 

Tomorrow target

Build one new executable:so

database create_ml_features --schema ml

Its job:

raw tables
* → aggregate features
* → one row per SK_ID_CURR
* → save as ml.ml_applicant_features

# Day 3 

Add the logs 


