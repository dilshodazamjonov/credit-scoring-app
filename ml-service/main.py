import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel


# 1. Path Setup
# Ensure the directory containing 'src' is in the Python path so Joblib 
# can find Preprocessor and FinalInferencePipeline during deserialization.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

threshold = float(os.getenv("RISK_THRESHOLD", "0.46"))  # Default threshold if not set in env
is_debug = os.getenv("APP_ENV").lower() == "developement"

# 2. Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml-service")

# 3. Model State Management
# We store the model in a dictionary to manage it within the FastAPI lifespan
model_assets = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    Loads the model bundle once when the server starts.
    """
    bundle_path = os.path.join(current_dir, "models", "catboost_production_bundle.joblib")
    
    if not os.path.exists(bundle_path):
        logger.error(f"Model bundle not found at {bundle_path}")
        # We don't exit here so the container stays up for debugging, 
        # but the health check will fail.
    else:
        try:
            logger.info(f"Loading model bundle from {bundle_path}...")
            model_assets["bundle"] = joblib.load(bundle_path)
            logger.info("Model bundle loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model bundle: {e}")

    yield
    # Clean up on shutdown
    model_assets.clear()

# 4. FastAPI App Initialization
app = FastAPI(
    title="Home Credit Risk Scoring API",
    description="ML Service for predicting loan default probability.",
    version="1.0.0",
    lifespan=lifespan
)

# 5. Input/Output Schemas
class ScoringRequest(BaseModel):
    """
    Flexible input schema. The Go Gateway will handle strict 
    feature-by-feature validation.
    """
    data: Dict[str, Any]

class ScoringResponse(BaseModel):
    probability: float
    is_high_risk: bool
    threshold: float
    status: str

# 6. Endpoints
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Check if the service is alive and the model is loaded."""
    if "bundle" not in model_assets:
        return {"status": "unhealthy", "reason": "model_not_loaded"}
    return {"status": "healthy", "model": "catboost_v1"}

@app.post("/predict", response_model=ScoringResponse)
async def predict(request: ScoringRequest):
    """
    Receives raw features, runs the pipeline, and returns credit risk.
    """
    if "bundle" not in model_assets:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Model is currently unavailable."
        )

    try:
        # 1. Convert incoming JSON data to a single-row DataFrame
        input_df = pd.DataFrame([request.data])
        
        # 2. Inference via the Pipeline wrapper
        # The pipeline handles: Preprocessing -> IV Filtering -> Selection -> Scaling -> CatBoost
        bundle = model_assets["bundle"]
        probability = float(bundle.predict_prob(input_df)[0])  
        
        return ScoringResponse(
            probability=round(probability, 4),
            is_high_risk=probability > threshold,
            threshold=threshold,
            status="success"
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing input: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


    