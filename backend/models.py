from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import time

class ThreatLevel(str, Enum):
    ROUTINE = "ROUTINE"           # Stage 0: Normal commercial/routine civilian
    SUSPICIOUS = "SUSPICIOUS"     # Stage 1: Minor trajectory or RF deviation
    HOSTILE = "HOSTILE"           # Stage 2: Confirmed hostile staging / off-corridor
    CRITICAL_LAUNCH = "CRITICAL"  # Stage 3: Left-of-launch imminent TEL erect/lock

class AssetType(str, Enum):
    CYBER_PAYLOAD = "CYBER_PAYLOAD"       # SCADA/Datalink injection (Zero collateral, speed of light)
    EW_JAMMER = "EW_JAMMER"               # High-power microwave / RF jamming (Non-kinetic)
    LASER_DEW = "LASER_DEW"               # Directed Energy Weapon (Line of sight, fast)
    COUNTER_DRONE = "COUNTER_DRONE"       # Interceptor drone swarm (Kinetic / medium range)
    KINETIC_SAM = "KINETIC_SAM"           # Surface-to-Air missile battery (Lethal kinetic intercept)

class AssetStatus(str, Enum):
    READY = "READY"
    TRACKING = "TRACKING"
    ENGAGED = "ENGAGED"
    COOLDOWN = "COOLDOWN"

class RadarLog(BaseModel):
    sensor_id: str = "RADAR-X01"
    timestamp: float
    azimuth_deg: float
    range_km: float
    doppler_mps: float
    rcs_dbm2: float            # Radar cross section
    snr_db: float

class SatelliteObservation(BaseModel):
    sensor_id: str = "SAT-SAR04"
    timestamp: float
    lat: float
    lon: float
    altitude_m: float
    convoy_count: int
    optical_confidence: float

class RfSigintBurst(BaseModel):
    sensor_id: str = "SIGINT-ARRAY9"
    timestamp: float
    center_freq_mhz: float
    bandwidth_mhz: float
    signal_power_dbm: float
    burst_duration_ms: float
    chatter_entropy: float      # Military encryption entropy

class RawSensorBundle(BaseModel):
    track_id: str
    radar: RadarLog
    satellite: SatelliteObservation
    sigint: RfSigintBurst

class FusedTrack(BaseModel):
    track_id: str
    timestamp: float
    callsign: str
    lat: float
    lon: float
    x: float                   # Tactical Cartesian km from grid center
    y: float                   # Tactical Cartesian km from grid center
    velocity_mps: float
    heading_deg: float
    altitude_m: float
    rcs_dbm2: float
    rf_intensity_mw: float
    kinematic_uncertainty: float
    fused_confidence: float

class AnomalyAssessment(BaseModel):
    track_id: str
    timestamp: float
    anomaly_score: float       # 0.0 (Normal) to 1.0 (Critical anomaly)
    threat_level: ThreatLevel
    isolation_score: float
    deviation_km: float
    rf_anomaly_ratio: float
    features_attributed: Dict[str, float]
    explanation: str

class DefenseAsset(BaseModel):
    asset_id: str
    name: str
    asset_type: AssetType
    x: float                   # km on tactical grid
    y: float                   # km on tactical grid
    effective_range_km: float
    pk_probability: float      # Probability of suppression kill (0.0 to 1.0)
    cost_index: float          # 1 to 10 scale (Cyber=1, SAM=9)
    collateral_risk: float     # 0.0 to 1.0
    status: AssetStatus = AssetStatus.READY
    cooldown_remaining_s: float = 0.0
    ammo_or_charge_pct: float = 100.0
    target_track_id: Optional[str] = None

class AllocationResult(BaseModel):
    allocation_id: str
    timestamp: float
    track_id: str
    asset_id: str
    asset_name: str
    asset_type: AssetType
    threat_level: ThreatLevel
    distance_km: float
    calculated_utility: float
    expected_pk: float
    estimated_time_to_suppress_s: float
    status: str                # ASSIGNED, SUPPRESSING, NEUTRALIZED, ABORTED
    algorithm_solve_time_ms: float

class SystemMetrics(BaseModel):
    active_threats: int
    anomalies_detected: int
    allocations_executed: int
    neutralized_count: int
    mean_solver_latency_ms: float
    mean_fusion_latency_ms: float
    avg_pk_success_rate: float
    autonomous_mode: bool = True
