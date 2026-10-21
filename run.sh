#!/usr/bin/env bash
# Automated Preemptive Suppression Architecture - Kill-Web Prototype
# Start script for MCA project evaluation

set -e

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "[!] .venv not found. Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

# Ensure ML model is trained
if [ ! -f "backend/ml_brain/models/anomaly_detector.joblib" ]; then
    echo "[*] Training initial Isolation Forest anomaly detector..."
    PYTHONPATH=. .venv/bin/python -m backend.ml_brain.train_detector
fi

echo "[*] Launching Autonomous Kill-Web C2 Console on http://127.0.0.1:8000"
PYTHONPATH=. .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
