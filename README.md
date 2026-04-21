# CreditCore — AI-Powered Credit Risk Assessment Platform

[![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)]()
[![ML Model](https://img.shields.io/badge/ML-CatBoost-orange)]()
[![License](https://img.shields.io/badge/License-Proprietary-red)]()

---

## Executive Summary

CreditCore is a production-grade, microservices-based credit risk assessment system that leverages machine learning to provide real-time loan application decisions. The platform combines a high-performance Go API gateway with a Python-based ML service, delivering instant credit decisions through an intuitive web interface.

**Key Capabilities:**
- Real-time credit risk scoring using CatBoost gradient boosting models
- Automated feature engineering and selection (RF/mRMR algorithms)
- Scalable microservices architecture with containerized deployment
- Sub-second inference latency for production workloads
- Comprehensive input validation and error handling

---

## System Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Browser   │──────│  Go Gateway  │──────│  Python ML svc  │
│  (Frontend) │      │  (Fiber)     │      │  (FastAPI)      │
└─────────────┘      └──────────────┘      └─────────────────┘
     :3001              :3000                   :8000
```

### Component Overview

| Component | Technology | Port | Responsibility |
|-----------|------------|------|----------------|
| **Frontend** | Vanilla JavaScript, HTML5, CSS3 | 3001 | User interface, form validation, result visualization |
| **Gateway** | Go (Fiber v2), HTTP proxy | 3000 | Request routing, CORS, load balancing, API aggregation |
| **ML Service** | Python 3.13, FastAPI, CatBoost | 8000 | Model inference, preprocessing, feature selection |

---

## Technical Stack

### Machine Learning Service

**Core Dependencies:**
- `catboost>=1.2.10` — Gradient boosting model inference
- `fastapi>=0.135.3` — Async API framework
- `scikit-learn>=1.8.0` — Preprocessing pipelines
- `pandas>=3.0.2` — Data manipulation
- `numpy>=2.4.4` — Numerical computations
- `uvicorn>=0.44.0` — ASGI server

**ML Pipeline Components:**

1. **Preprocessing (`src/preprocessing.py`)**
   - `NumericalScaler`: Missing value imputation (mean/median/zero) + StandardScaler/MinMaxScaler
   - `CategoricalEncoder`: Low-cardinality → One-Hot Encoding, High-cardinality → Label Encoding
   - Handles infinite values, missing columns, and type conversion

2. **Feature Selection (`src/feature_selection.py`)**
   - `FeatureSelector`: RF-based and mRMR (minimum Redundancy Maximum Relevance) selection
   - Parallel processing with joblib for scalability
   - Compatible with sklearn pipeline architecture

3. **Pipeline (`src/pipeline.py`)**
   - End-to-end preprocessing + model inference
   - Serialized model bundle (CatBoost)
   - Thread-safe inference with logging

### API Gateway

**Core Dependencies:**
- `go 1.26.2`
- `github.com/gofiber/fiber/v2` — High-performance HTTP server
- `github.com/google/uuid` — Request tracking

**Features:**
- Reverse proxy to ML service
- CORS configuration for frontend
- Request/response logging
- Health check endpoints

### Frontend

**Technology:**
- Pure JavaScript (ES6+, no framework dependencies)
- HTML5 semantic markup
- CSS3 with custom properties (CSS variables)
- Google Fonts (Plus Jakarta Sans)

**Features:**
- Dynamic form generation from model schema
- Real-time validation
- Test scenario prefill (Good Credit / High Risk)
- Interactive risk visualization with animated meter
- Responsive design

---

## Data Schema

### Input Features

Number of input fields are dynamically generated for the production, using js and Go lang endpoint

### Output Schema

```json
{
  "decision": "APPROVED | DECLINED",
  "probability": 0.234,
  "threshold": 0.4763,
  "status": "success"
}
```

**Decision Logic:**
- `APPROVED` if `probability < threshold`
- `DECLINED` if `probability >= threshold`

---

## Deployment

### Prerequisites

- Docker & Docker Compose
- Python 3.13+ (for local development)
- Go 1.26+ (for gateway development)

### Docker Compose Setup

```bash
# Start all services
docker-compose up --build

# Access points:
# - Frontend: http://localhost:3001
# - Gateway:  http://localhost:3000
# - ML API:   http://localhost:8000
```

### Individual Service Deployment

**ML Service:**
```bash
cd ml-service
# Using uv (recommended)
uv run python main.py

# Or with pip
pip install -e .
python main.py
```

**Gateway:**
```bash
cd gateway
go run main.go
```

**Frontend:**
```bash
cd frontend
# Serve with any static server
python -m http.server 3001
# Or use npx
npx serve -l 3001
```

---

## API Reference

### POST `/apply`

**Request:**
```bash
curl -X POST http://localhost:3000/apply \
  -H "Content-Type: application/json" \
  -d '{
    "AMT_ANNUITY": 15000,
    "AMT_GOODS_PRICE": 180000,
    "DAYS_BIRTH": -14965,
    ...
  }'
```

**Response:**
```json
{
  "decision": "APPROVED",
  "probability": 0.23,
  "threshold": 0.4763,
  "status": "success"
}
```

### GET `/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-13T10:30:00Z"
}
```

---

## Development Guidelines

### Code Quality

- **ML Service**: Follows sklearn transformer API conventions
- **Gateway**: Fiber middleware pattern for extensibility
- **Frontend**: Vanilla JS with explicit 'use strict' mode

### Testing Strategy

```bash
# ML Service tests (if implemented)
cd ml-service
pytest

# Gateway tests
cd gateway
go test ./...
```

### Logging

All services implement structured logging:
- ML Service: Python `logging` module with module-level loggers
- Gateway: Fiber request logging with UUID correlation
- Frontend: Console logging for debugging (production-ready error handling)

---

## Performance Characteristics

| Metric | Target |
|--------|--------|
| Inference Latency | < 100ms (p95) |
| Throughput | 1000+ req/sec |
| Startup Time | < 5s (warm) |
| Memory Footprint | ~200MB (ML service) |

---

## Security Considerations

- **Input Validation**: All numeric fields validated for range and type
- **CORS**: Configured for specific origins in production
- **Data Privacy**: No persistent storage of application data (stateless)
- **Error Handling**: No stack traces or sensitive data exposed in responses

---

## Monitoring & Observability

**Recommended additions for production:**
- Request metrics (Prometheus/Grafana)
- Distributed tracing (OpenTelemetry)
- Health check endpoints with dependency checks
- Structured JSON logging for log aggregation

---

## Future Enhancements

1. **Model Versioning**: A/B testing infrastructure for model updates
2. **Explainability**: SHAP/LIME integration for decision explanations
3. **Batch Processing**: Async job queue for bulk applications
4. **Multi-tenancy**: Tenant isolation and resource quotas
5. **Audit Trail**: Immutable logging for compliance

---

## Support

For technical inquiries or production support, contact the NLP-Core-Team.

---

*CreditCore — Production-Ready Credit Risk Assessment*
