import os
import joblib
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from backend.models import FusedTrack, AnomalyAssessment, ThreatLevel

# Designated peacetime corridors (commercial roads / air lanes)
# Defined as line segments: [(x1, y1), (x2, y2)]
CORRIDORS = [
    ((-60.0, -30.0), (60.0, 30.0)),   # Highway Alpha
    ((-40.0, 40.0), (40.0, -40.0)),   # Corridor Bravo
    ((-50.0, 0.0), (50.0, 0.0))       # Trans-Sector Transit Route
]

def min_distance_to_corridors(x: float, y: float) -> float:
    min_dist = 999.0
    p = np.array([x, y])
    for (x1, y1), (x2, y2) in CORRIDORS:
        a = np.array([x1, y1])
        b = np.array([x2, y2])
        ba = b - a
        norm_ba = np.linalg.norm(ba)
        if norm_ba < 1e-5:
            dist = float(np.linalg.norm(p - a))
        else:
            t = float(np.clip(np.dot(p - a, ba) / (norm_ba ** 2), 0.0, 1.0))
            proj = a + t * ba
            dist = float(np.linalg.norm(p - proj))
        if dist < min_dist:
            min_dist = dist
    return min_dist

class AnomalyDetectionBrain:
    """
    ML-Driven Left-of-Launch Anomaly Classifier and Kinematic Threat Assessor.
    Combines Isolation Forest anomaly scores with explainable attribution rules.
    """
    def __init__(self, model_path: str = "backend/ml_brain/models/anomaly_detector.joblib"):
        self.model_path = model_path
        self.model_data = None
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            self.model_data = joblib.load(self.model_path)
            print(f"[ML-Brain] Anomaly detection model loaded from {self.model_path}")
        else:
            print(f"[ML-Brain] Warning: model not found at {self.model_path}. Training a new one...")
            from backend.ml_brain.train_detector import train_and_export_anomaly_models
            self.model_data = train_and_export_anomaly_models()

    def assess_track(
        self,
        current_track: FusedTrack,
        track_history: Optional[List[FusedTrack]] = None
    ) -> AnomalyAssessment:
        if track_history is None:
            track_history = []

        # 1. Kinematic and physical feature extraction
        vel = current_track.velocity_mps

        # Velocity variance calculation from history
        if len(track_history) >= 2:
            vels = [t.velocity_mps for t in track_history[-8:]] + [vel]
            vel_var = float(np.var(vels))
        else:
            vel_var = 0.5

        # Off-corridor distance
        off_corridor_dist = min_distance_to_corridors(current_track.x, current_track.y)

        # Radar Cross Section
        rcs = current_track.rcs_dbm2

        # Convert RF intensity (mW) to dBm: dBm = 10 * log10(mW)
        rf_mw = max(1e-4, current_track.rf_intensity_mw)
        rf_power_dbm = 10.0 * math.log10(rf_mw)
        rf_entropy = 0.88 if rf_power_dbm > 25.0 else 0.35

        # Strategic proximity (distance to defense origin (0, 0))
        strategic_dist = math.hypot(current_track.x, current_track.y)

        # Stationary dwell calculation: how long object has remained within 0.5km
        dwell_min = 0.0
        if len(track_history) >= 3:
            recent_tracks = track_history[-10:]
            dists = [math.hypot(t.x - current_track.x, t.y - current_track.y) for t in recent_tracks]
            if max(dists) < 0.8: # stayed in place
                dwell_min = (current_track.timestamp - recent_tracks[0].timestamp) / 60.0

        features = [
            vel,
            vel_var,
            off_corridor_dist,
            rcs,
            rf_power_dbm,
            rf_entropy,
            strategic_dist,
            dwell_min
        ]

        # 2. Model inference
        scaler = self.model_data["scaler"]
        iso_forest = self.model_data["isolation_forest"]
        s_min = self.model_data["score_min"]
        s_max = self.model_data["score_max"]

        X_feat = np.array([features])
        X_scaled = scaler.transform(X_feat)

        raw_score = -float(iso_forest.decision_function(X_scaled)[0])
        norm_score = float(np.clip((raw_score - s_min) / (s_max - s_min + 1e-8), 0.0, 1.0))

        # 3. Threat Level Categorization
        if norm_score >= 0.80 or (rf_power_dbm > 38.0 and off_corridor_dist > 4.0):
            threat = ThreatLevel.CRITICAL_LAUNCH
        elif norm_score >= 0.62:
            threat = ThreatLevel.HOSTILE
        elif norm_score >= 0.38:
            threat = ThreatLevel.SUSPICIOUS
        else:
            threat = ThreatLevel.ROUTINE

        # 4. Feature attribution & explainability
        feature_dict = {
            "Velocity (m/s)": round(vel, 1),
            "Off-Corridor (km)": round(off_corridor_dist, 2),
            "RCS (dBm²)": round(rcs, 1),
            "RF Power (dBm)": round(rf_power_dbm, 1),
            "Strategic Distance (km)": round(strategic_dist, 1),
            "Dwell Time (min)": round(dwell_min, 1)
        }

        # Build natural language tactical explanation
        reasons = []
        if off_corridor_dist > 5.0:
            reasons.append(f"Off civilian corridor by {off_corridor_dist:.1f}km")
        if rf_power_dbm > 25.0:
            reasons.append(f"High military RF telemetry burst ({rf_power_dbm:.1f} dBm)")
        if rcs > 20.0:
            reasons.append(f"Elevated radar cross-section {rcs:.1f}dBm² (structural erection profile)")
        if dwell_min > 5.0 and strategic_dist < 30.0:
            reasons.append(f"Concealed stationary staging within {strategic_dist:.1f}km of strategic sector")

        if not reasons:
            explanation = "Normal commercial/routine trajectory within authorized corridor limits."
        else:
            explanation = "Left-of-Launch Preemptive Indicators: " + "; ".join(reasons)

        rf_ratio = max(0.0, min(1.0, (rf_power_dbm + 20.0) / 60.0))

        return AnomalyAssessment(
            track_id=current_track.track_id,
            timestamp=current_track.timestamp,
            anomaly_score=round(norm_score, 3),
            threat_level=threat,
            isolation_score=round(raw_score, 4),
            deviation_km=round(off_corridor_dist, 2),
            rf_anomaly_ratio=round(rf_ratio, 3),
            features_attributed=feature_dict,
            explanation=explanation
        )
