import pytest
import time
from backend.models import (
    FusedTrack,
    AnomalyAssessment,
    DefenseAsset,
    ThreatLevel,
    AssetType,
    AssetStatus
)
from backend.allocation_router.defense_assets import create_default_defense_network
from backend.allocation_router.hungarian_optimizer import HungarianTargetAllocator

def test_defense_network_initialization():
    assets = create_default_defense_network()
    assert len(assets) >= 5
    types = [a.asset_type for a in assets]
    assert AssetType.CYBER_PAYLOAD in types
    assert AssetType.EW_JAMMER in types
    assert AssetType.LASER_DEW in types
    assert AssetType.KINETIC_SAM in types

def test_hungarian_allocation_speed_and_assignment():
    allocator = HungarianTargetAllocator()
    assets = create_default_defense_network()

    now = time.time()
    track_tel = FusedTrack(
        track_id="TGT-TEL-01",
        timestamp=now,
        callsign="TEL-01",
        lat=34.0, lon=-118.0,
        x=10.0, y=10.0,
        velocity_mps=0.0, heading_deg=0.0,
        altitude_m=100.0, rcs_dbm2=24.0,
        rf_intensity_mw=50000.0,
        kinematic_uncertainty=0.01,
        fused_confidence=0.99
    )
    assess_tel = AnomalyAssessment(
        track_id="TGT-TEL-01",
        timestamp=now,
        anomaly_score=0.95,
        threat_level=ThreatLevel.CRITICAL_LAUNCH,
        isolation_score=0.35,
        deviation_km=14.0,
        rf_anomaly_ratio=0.92,
        features_attributed={},
        explanation="Imminent launch prep"
    )

    t0 = time.time()
    allocations = allocator.allocate_targets([(track_tel, assess_tel)], assets)
    elapsed_ms = (time.time() - t0) * 1000.0

    assert elapsed_ms < 50.0 # Hungarian algorithm must solve in under 50ms (usually < 3ms)
    assert len(allocations) == 1
    assert allocations[0].track_id == "TGT-TEL-01"
    assert allocations[0].expected_pk > 0.50
    assert allocations[0].status == "ENGAGING"
