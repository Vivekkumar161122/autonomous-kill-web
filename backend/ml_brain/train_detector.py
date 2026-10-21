import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
from backend.ml_brain.dataset_generator import generate_synthetic_threat_dataset

FEATURE_COLUMNS = [
    "velocity_mps",
    "velocity_variance",
    "off_corridor_dist_km",
    "rcs_dbm2",
    "rf_power_dbm",
    "rf_entropy",
    "strategic_proximity_km",
    "stationary_dwell_min"
]

def train_and_export_anomaly_models():
    os.makedirs("data", exist_ok=True)
    os.makedirs("backend/ml_brain/models", exist_ok=True)

    csv_path = "data/synthetic_military_patterns.csv"
    if not os.path.exists(csv_path):
        df = generate_synthetic_threat_dataset(n_samples=5000, seed=42)
        df.to_csv(csv_path, index=False)
    else:
        df = pd.read_csv(csv_path)

    X = df[FEATURE_COLUMNS].values
    y = df["is_hostile"].values

    # Train scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train Isolation Forest on normal baseline (unsupervised zero-day detector)
    X_normal = X_scaled[y == 0]
    iso_forest = IsolationForest(
        n_estimators=150,
        contamination=0.15,
        random_state=42,
        max_samples="auto"
    )
    iso_forest.fit(X_normal)

    # Supervised Random Forest for benchmark comparison & feature importances
    rf_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_clf.fit(X_scaled, y)

    # Calculate metrics
    # IsolationForest decision_function returns negative values for anomalies
    iso_scores = -iso_forest.decision_function(X_scaled)
    # Normalize score between 0.0 and 1.0
    min_s, max_s = iso_scores.min(), iso_scores.max()
    normalized_scores = (iso_scores - min_s) / (max_s - min_s + 1e-8)
    
    auc = roc_auc_score(y, normalized_scores)
    print(f"=== Isolation Forest ROC-AUC on Hostile Staging: {auc:.4f} ===")

    # Feature importances from supervised reference
    importances = dict(zip(FEATURE_COLUMNS, [round(float(val), 4) for val in rf_clf.feature_importances_]))
    print("Feature Importances:", importances)

    model_payload = {
        "scaler": scaler,
        "isolation_forest": iso_forest,
        "rf_classifier": rf_clf,
        "feature_columns": FEATURE_COLUMNS,
        "score_min": float(min_s),
        "score_max": float(max_s),
        "feature_importances": importances,
        "roc_auc": float(auc)
    }

    model_path = "backend/ml_brain/models/anomaly_detector.joblib"
    joblib.dump(model_payload, model_path)
    print(f"Trained model exported successfully to {model_path}")
    return model_payload

if __name__ == "__main__":
    train_and_export_anomaly_models()
