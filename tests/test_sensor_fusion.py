import pytest
import math
from backend.sensor_fusion.synthetic_generators import SyntheticSensorGenerator, latlon_to_cartesian, cartesian_to_latlon
from backend.sensor_fusion.kalman_bayesian_fusion import SensorFusionEngine, KalmanTrackFilter

def test_latlon_cartesian_roundtrip():
    orig_x, orig_y = 25.4, -18.2
    lat, lon = cartesian_to_latlon(orig_x, orig_y)
    rec_x, rec_y = latlon_to_cartesian(lat, lon)
    assert math.isclose(orig_x, rec_x, abs_tol=1e-3)
    assert math.isclose(orig_y, rec_y, abs_tol=1e-3)

def test_synthetic_sensor_generation():
    gen = SyntheticSensorGenerator(seed=42)
    bundle = gen.bundle_all_sensors(
        track_id="TEST-01",
        true_x=10.0,
        true_y=15.0,
        true_vx=0.02,
        true_vy=0.01,
        is_hostile=False
    )
    assert bundle.radar.range_km > 0
    assert 0.0 <= bundle.radar.azimuth_deg < 360.0
    assert bundle.satellite.optical_confidence >= 0.5
    assert bundle.sigint.signal_power_dbm < 10.0 # Routine baseline

def test_hostile_rf_spike():
    gen = SyntheticSensorGenerator(seed=99)
    bundle = gen.bundle_all_sensors(
        track_id="TEL-01",
        true_x=5.0,
        true_y=5.0,
        true_vx=0.0,
        true_vy=0.0,
        is_hostile=True,
        is_launch_prep=True
    )
    # Launch prep must produce high RF power > 35 dBm
    assert bundle.sigint.signal_power_dbm > 35.0
    assert bundle.sigint.chatter_entropy > 0.85

def test_kalman_bayesian_fusion_engine():
    engine = SensorFusionEngine()
    gen = SyntheticSensorGenerator(seed=12)

    bundle1 = gen.bundle_all_sensors("TRK-A", 10.0, 10.0, 0.01, 0.01)
    fused1 = engine.fuse_bundle(bundle1, callsign="ALPHA-1")

    assert fused1.track_id == "TRK-A"
    assert math.isclose(fused1.x, 10.0, abs_tol=2.0)
    assert math.isclose(fused1.y, 10.0, abs_tol=2.0)
    assert 0.0 < fused1.fused_confidence <= 1.0
    assert fused1.kinematic_uncertainty > 0
