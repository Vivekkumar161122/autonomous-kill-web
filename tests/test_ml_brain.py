import pytest
import time
from backend.models import FusedTrack, ThreatLevel
from backend.ml_brain.anomaly_engine import AnomalyDetectionBrain, min_distance_to_corridors

def test_corridor_distance():
    # Exactly on Trans-Sector Route ((-50, 0) to (50, 0))
    d = min_distance_to_corridors(0.0, 0.0)
    assert d < 0.1

    # Way off corridor at (0, 35)
    d_off = min_distance_to_corridors(0.0, 35.0)
    assert d_off > 10.0

def test_peacetime_routine_evaluation():
    brain = AnomalyDetectionBrain()
    now = time.time()
    # Routine commercial truck on corridor
    routine_track = FusedTrack(
        track_id="ROUTINE-01",
        timestamp=now,
        callsign="CIV-CARGO",
        lat=34.05,
        lon=-118.24,
        x=0.0,
        y=0.0,
        velocity_mps=22.0,
        heading_deg=90.0,
        altitude_m=100.0,
        rcs_dbm2=12.0,
        rf_intensity_mw=0.01, # ~ -20 dBm
        kinematic_uncertainty=0.05,
        fused_confidence=0.95
    )
    assess = brain.assess_track(routine_track)
    assert assess.threat_level in [ThreatLevel.ROUTINE, ThreatLevel.SUSPICIOUS]
    assert assess.anomaly_score < 0.60
    assert "Off-Corridor (km)" in assess.features_attributed

def test_left_of_launch_tel_anomaly():
    brain = AnomalyDetectionBrain()
    now = time.time()
    # High-risk anomalous TEL: 18km off road, high RF burst (+45 dBm = 31622 mW), large RCS (26 dBm²)
    tel_track = FusedTrack(
        track_id="ROGUE-TEL-99",
        timestamp=now,
        callsign="SUSPECT-TEL",
        lat=34.15,
        lon=-118.05,
        x=22.0,
        y=28.0,
        velocity_mps=0.0, # Halted in launch prep
        heading_deg=0.0,
        altitude_m=120.0,
        rcs_dbm2=26.0,
        rf_intensity_mw=31622.0, # +45 dBm
        kinematic_uncertainty=0.02,
        fused_confidence=0.98
    )
    assess = brain.assess_track(tel_track)
    assert assess.threat_level in [ThreatLevel.HOSTILE, ThreatLevel.CRITICAL_LAUNCH]
    assert assess.anomaly_score >= 0.70
    assert "Left-of-Launch" in assess.explanation
