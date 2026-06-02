FROM python:3.12-slim

WORKDIR /app

# System deps for lightgbm + shap
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model files (now under model/output/)
COPY model/output/xgboost_eligibility_v3.pkl /app/models/xgboost_eligibility_v3.pkl
COPY model/output/xgboost_anomaly_v2.pkl     /app/models/xgboost_anomaly_v2.pkl

# Copy data generation + inference code (now under model/)
COPY model/province_master_config.json /app/province_master_config.json
COPY model/regenerate_data.py          /app/regenerate_data.py
COPY model/predict.py                  /app/predict.py

# Copy backend application
COPY backend/ /app/

# Override default local-dev paths to Docker paths
ENV PROVINCE_CONFIG_PATH=/app/province_master_config.json
ENV MODEL_ELIGIBILITY_PATH=/app/models/xgboost_eligibility_v3.pkl
ENV MODEL_ANOMALY_PATH=/app/models/xgboost_anomaly_v2.pkl

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
