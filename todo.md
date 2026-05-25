# 1. Target architecture

Build it like this:

Frontend
   в†“
Go Backend
   в†“
Python FastAPI ML Service
   в†“
PostgreSQL
   в†“
Saved model bundle / artifacts

But the responsibility split matters.

### Go backend should own
* Authentication
* User sessions
* Applicant ownership
* Frontend-facing APIs
* Score request creation
* Permission checks

### Python FastAPI should own
* Data loading for scoring
* Feature engineering
* Feature validation
* Model loading
* Prediction
* Calibration
* Explanation
* ML audit logging


### PostgreSQL should own
* Raw imported source tables
* Applicant identity mapping
* Feature snapshots
* Score requests
* Score results
* Model registry
* Prediction logs

### Frontend should own
* Login/register
* Applicant dashboard
* "Get my score" button
* Score result display
* Reason/explanation display
* History of previous scores

## 2. First thing to build: database schema

Create schemas like this:
* raw.application_train
* raw.bureau
* raw.bureau_balance
* raw.previous_application
* raw.installments_payments
* raw.credit_card_balance
* raw.pos_cash_balance
---
* core.applicants
* core.users
* core.user_applicant_map
---
* ml.model_registry
* ml.feature_snapshot
* ml.score_request
* ml.score_result
* ml.prediction_log

raw tables should mirror the original CSV columns as much as possible

## 3. Build a DB ingestion module

Create a separate backend utility, not inside the FastAPI route.

Suggested location:
```
credit_scoring_backend/
  ingestion/
    load_csv_to_postgres.py
    validate_raw_tables.py
    source_table_config.yaml
```
This module should:

* Read CSV
* Clean column names only if needed
* Insert into matching raw table
* Check primary IDs
* Check row counts
* Check missing required columns
* Write ingestion log

For now, do not build a fancy ETL framework. Just build a reliable script.

Example:
```
python ingestion/load_csv_to_postgres.py --source application_train --path data/application_train.csv
python ingestion/load_csv_to_postgres.py --source bureau --path data/bureau.csv
```
Add an ingestion log table:
```
ml.ingestion_log (
    ingestion_id,
    source_name,
    file_name,
    row_count,
    column_count,
    status,
    error_message,
    created_at
)
```

## 4. Refactor your training code into reusable feature code

Build a real model bundle, not just model.joblib

Your current joblib model is not enough.

Create this artifact structure:

artifacts/
  model_bundle_v001/
    model.joblib
    preprocessor.joblib
    calibrator.joblib
    feature_schema.json
    training_manifest.json
    selected_features.json
    score_mapping.json
    metrics_report.json

Where:

model.joblib
    Trained classifier.

preprocessor.joblib
    Imputation, encoding, scaling, column ordering.

calibrator.joblib
    Platt/isotonic/beta calibration if used.

feature_schema.json
    Exact expected feature names, dtypes, order.

training_manifest.json
    Dataset version, split dates, DEV/OOT sizes, target rate, model params.

selected_features.json
    Features used by the model.

score_mapping.json
    PD в†’ score band / decision recommendation.

Your previous result brief already tracks DEV/OOT splits, target rates, AUC/Gini/KS, PSI, stability metrics, and model score PSI. That information should become part of the model manifest, not just a report.

Also, because feature-selection stability is a core part of your research, keep the selected-feature metadata. Nogueira et al. define feature-selection stability as robustness of selected features under data sampling/stochastic changes, which is directly relevant to your LLM/mRMR/CatBoost feature-selection pipeline.

## 6. Build the Python FastAPI scoring service

Suggested structure:

```text
scoring_service/
  app/
    main.py
    api/
      score_routes.py
      health_routes.py
    services/
      scoring_service.py
      feature_service.py
      explanation_service.py
      model_loader.py
    db/
      session.py
      repositories.py
    schemas/
      requests.py
      responses.py
    config.py
```

Main endpoint:

```text
POST /internal/score/{applicant_id}
```

Input:

```json
{
  "request_id": "uuid-from-go-backend",
  "requested_by": "user_id"
}
```

Output:

```json
{
  "applicant_id": 100001,
  "request_id": "abc-123",
  "model_version": "model_bundle_v001",
  "pd_raw": 0.183,
  "pd_calibrated": 0.157,
  "score_band": "medium_risk",
  "decision_recommendation": "review",
  "top_risk_factors": [
    "High credit amount relative to income",
    "Short employment history",
    "Previous late payment pattern"
  ],
  "created_at": "2026-05-25T..."
}
```

The scoring flow inside Python should be:

```text
Receive applicant_id
в†’ fetch raw rows from PostgreSQL
в†’ build feature vector
в†’ validate feature schema
в†’ save feature_snapshot
в†’ load active model bundle
в†’ predict raw PD
в†’ apply calibration
в†’ map PD to score band
в†’ generate explanation
в†’ save score_result
в†’ return response to Go
```

Do not load the model on every request. Load it once during service startup and cache it.

## 7. Build Go as the API gateway, not the ML brain

Your Go backend should expose something like:

```text
POST /api/score/me
GET /api/score/history
GET /api/score/{score_id}
```

Flow:

```text
User clicks "Get my score"
в†’ frontend calls Go
в†’ Go checks auth
в†’ Go finds applicant_id for user
в†’ Go creates ml.score_request row
в†’ Go calls Python /internal/score/{applicant_id}
в†’ Python returns result
в†’ Go returns clean response to frontend
```

Do not let frontend call Python directly. That would bypass your auth boundary.

Go should also protect against this:

```text
User A requesting score for Applicant B
```

So never expose:

```text
/api/score/100001
```

unless you have strict ownership checks.

Better:

```text
/api/score/me
```

The backend resolves the applicant ID internally.

## 8. Add explanation, but keep it simple first

Do not overbuild SHAP on day one.

First explanation layer:

* Show top contributing features based on model feature importance / logistic coefficients / SHAP if already available.
* Map technical feature names to human-readable reasons.

Create:

```text
ml.feature_dictionary
```

Example:

```text
EXT_SOURCE_2
в†’ External risk signal is low.

AMT_CREDIT_INCOME_RATIO
в†’ Requested credit is high relative to income.

BUREAU_DAYS_CREDIT_MEAN
в†’ Credit history is relatively recent or limited.

INSTALLMENTS_DPD_MEAN
в†’ Past installment delay pattern detected.
```

The user should never see ugly raw names like DAYS_BIRTH or AMT_ANNUITY_RATIO. Show understandable reason codes.

## 9. Add monitoring tables early

Not full production monitoring yet, just enough to look serious.

```text
ml.prediction_log
ml.score_distribution_daily
ml.feature_drift_report
ml.error_log
```

Track:

* Number of score requests
* Average PD
* Score-band distribution
* Missing feature count
* Failed scoring attempts
* Model version used
* Feature schema mismatches

Your model-hacking report already says validation should check noise, missingness, imputation mismatch, feature drift, weak segments, calibration, and uncertainty. The production version should start logging the signals needed to detect those same problems later.

## 10. Implementation order

Do it in this order. Not negotiable.

### Phase 1 ” Freeze the model contract

Build:

```text
feature_schema.json
selected_features.json
training_manifest.json
model_bundle_v001/
```

Output:

```text
One model bundle that can score a DataFrame only if columns match exactly.
```

Success check:

```text
Given an applicant row from old CSV, model predicts same result before and after bundling.
```

### Phase 2 ” Create PostgreSQL raw tables

Build:

```text
raw.application_train
raw.bureau
raw.previous_application
raw.installments_payments
raw.credit_card_balance
raw.pos_cash_balance
```

Output:

```text
CSV data loaded into PostgreSQL.
```

Success check:

* Row counts match CSV.
* Applicant IDs can be searched.
* Related tables join correctly.

### Phase 3 ” Build feature generation from DB

Build:

```text
build_features_for_applicant(applicant_id)
```

Output:

```text
One applicant ID в†’ one model-ready feature row.
```

Success check:

```text
Feature row generated from DB equals feature row generated from old CSV pipeline.
```

This is the hardest part. If this fails, the whole project is fake.

### Phase 4 ” Build FastAPI scoring service

Build:

```text
POST /internal/score/{applicant_id}
GET /internal/health
GET /internal/model-info
```

Output:

```text
Applicant ID в†’ PD + score band + explanation.
```

Success check:

* API returns score for known applicant.
* API fails cleanly for missing applicant.
* API logs feature snapshot and score result.

### Phase 5 ” Connect Go backend

Build:

```text
POST /api/score/me
GET /api/score/history
```

Output:

```text
Authenticated user can request their own score.
```

Success check:

* User cannot request another user's applicant ID.
* Score request appears in DB.
* Frontend receives clean result.

### Phase 6 ” Update frontend

Build:

* Score dashboard
* Get my score button
* Score result card
* Top reason codes
* Previous score history

The frontend should show:

* Risk band
* PD / score
* Decision recommendation
* Top positive factors
* Top negative factors
* Model version / score date

Do not show too much. A frontend overloaded with raw ML numbers looks bad.

### Phase 7 ” Add validation/monitoring dashboard later

Only after the basic flow works.

Add:

* Score distribution over time
* Failed requests
* Missing feature rate
* Feature drift summary
* Model version usage
* Risk-band volume

This becomes your њreal-world deployment layer.ќ

## 11. Recommended repo structure

I would structure it like this:

```text
credit-scoring-system/
  ml-research/
    notebooks/
    experiments/
    results/
    artifacts/
      model_bundle_v001/
    src/
      training/
      features/
      validation/
      calibration/

  scoring-service/
    app/
      api/
      services/
      db/
      schemas/
    tests/
    Dockerfile
    requirements.txt

  go-backend/
    cmd/
    internal/
      auth/
      users/
      scoring/
      applicants/
    migrations/
    go.mod

  frontend/
    src/
      pages/
      components/
      services/

  database/
    migrations/
      001_create_raw_tables.sql
      002_create_core_tables.sql
      003_create_ml_tables.sql
    seeds/

  docs/
    architecture.md
    api_contract.md
    model_bundle_contract.md
    database_schema.md
```

This is clean because it separates:

* Research code
* Production scoring service
* Main backend
* Frontend
* Database migrations
* Documentation

Do not mix training notebooks inside the FastAPI app. That is messy and will rot fast.

## 12. Minimum viable version

Your first working target should be this:

```text
User logs in
в†’ clicks Get My Score
в†’ Go verifies user
в†’ Go calls Python with applicant_id
в†’ Python builds features from PostgreSQL
в†’ Python scores with model_bundle_v001
в†’ Python saves feature_snapshot and score_result
в†’ Frontend shows score + reason codes
```

That is enough to make the project look dramatically stronger.

Do not start with:

* Kafka
* Airflow
* Redis
* Kubernetes
* MLflow server
* Real-time monitoring dashboard
* Complex admin panel

That would be premature architecture cosplay.

## 13. What I would build first tomorrow

Start with this exact sequence:

1. Create model_bundle_v001.
2. Create feature_schema.json.
3. Create PostgreSQL raw tables for application + bureau first.
4. Load only 1000 applicants as a test.
5. Build build_features_for_applicant(applicant_id).
6. Compare DB-generated features with old CSV-generated features.
7. Build FastAPI /internal/score/{applicant_id}.
8. Only then connect Go.
