import pandas as pd
import numpy as np
import joblib
import json

class FinalInferencePipeline:
    def __init__(self, preprocessor, iv_filter, selector, model, feature_names):
        self.preprocessor = preprocessor 
        self.iv_filter = iv_filter
        self.selector = selector
        self.model = model
        self.feature_names = feature_names

    def predict_prob(self, raw_df: pd.DataFrame) -> np.ndarray:
        x = self.preprocessor.transform(raw_df)
        x = self.iv_filter.transform(x)
        x = self.selector.transform(x)
        
        missing_cols = set(self.feature_names) - set(x.columns)
        for col in missing_cols:
            x[col] = 0
        x = x[self.feature_names]
        return self.model.predict_proba(x)[:, 1]

def create_and_export_bundle(
    X_train_raw, fitted_preprocessor, fitted_iv_filter, 
    fitted_selector, fitted_model, final_feature_names, 
    threshold, export_path
):
    """
    Saves the Joblib bundle AND a filtered Metadata JSON for the Go Gateway.
    """
    # 1. Save Joblib Bundle (For FastAPI)
    pipeline = FinalInferencePipeline(
        preprocessor=fitted_preprocessor,
        iv_filter=fitted_iv_filter,
        selector=fitted_selector,
        model=fitted_model,
        feature_names=final_feature_names
    )
    joblib.dump(pipeline, export_path)

    # 2. Filter logic: Identify which RAW columns are needed
    # Some final features are direct (e.g. 'AMT_CREDIT')
    # Some are OHE (e.g. 'CODE_GENDER_M' comes from 'CODE_GENDER')
    required_raw_columns = []
    
    for final_f in final_feature_names:
        if final_f in X_train_raw.columns:
            required_raw_columns.append(final_f)
        else:
            # Check if this final feature is a one-hot encoded version of a raw column
            for raw_col in X_train_raw.columns:
                # e.g. if 'NAME_INCOME_TYPE_Working' starts with 'NAME_INCOME_TYPE'
                if final_f.startswith(raw_col + "_"):
                    required_raw_columns.append(raw_col)
                    break
    
    # Remove duplicates and sort
    required_raw_columns = sorted(list(set(required_raw_columns)))

    # 3. Save Metadata JSON (Only containing required features)
    metadata = {
        "model_name": "catboost_credit_risk",
        "threshold": float(threshold),
        "required_features_count": len(required_raw_columns),
        "features": []
    }
    
    for col in required_raw_columns:
        dtype = "number" if pd.api.types.is_numeric_dtype(X_train_raw[col]) else "string"
        metadata["features"].append({
            "name": col,
            "type": dtype
        })
    
    json_path = export_path.replace(".joblib", ".json")
    with open(json_path, "w") as f:
        json.dump(metadata, f, indent=4)
        
    print("Export Successful!")
    print(f"Python Bundle: {export_path}")
    print(f"Go Metadata: {json_path} (Now only {len(required_raw_columns)} fields)")


    