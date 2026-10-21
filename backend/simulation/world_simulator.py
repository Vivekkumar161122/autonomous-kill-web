import time
import math
import asyncio
from typing import Dict, List, Optional, Any
from backend.models import (
    FusedTrack,
    AnomalyAssessment,
    DefenseAsset,
    AllocationResult,
    SystemMetrics,
    AssetStatus,
    AssetType,
    ThreatLevel
)
from backend.sensor_fusion.synthetic_generators import SyntheticSensorGenerator
from backend.sensor_fusion.kalman_bayesian_fusion import SensorFusionEngine
from backend.ml_brain.anomaly_engine import AnomalyDetectionBrain
from backend.allocation_router.defense_assets import create_default_defense_network
from backend.allocation_router.hungarian_optimizer import HungarianTargetAllocator

class SimulatedTarget:
    def __init__(
        self,
        track_id: str,
        callsign: str,
        x: float,
        y: float,
        vx: float,
        vy: float,
        is_hostile: bool = False,
        is_launch_prep: bool = False,
        behavior: str = "straight"
    ):
        self.track_id = track_id
        self.callsign = callsign
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.is_hostile = is_hostile
        self.is_launch_prep = is_launch_prep
        self.behavior = behavior
        self.alive = True
        self.neutralized = False
        self.neutralize_progress = 0.0
        self.history: List[FusedTrack] = []
        self.age_s = 0.0

    def step(self, dt: float):
        if not self.alive:
            return

        self.age_s += dt

        if self.behavior == "patrol_corridor":
            # Follows civilian corridor with slight curvature
            self.x += self.vx * dt
            self.y += self.vy * dt
            if abs(self.x) > 60:
                self.vx = -self.vx
        elif self.behavior == "deviate_and_stop":
            # Starts normal, after 4 seconds suddenly steers off road, decelerates, and stops
            if self.age_s < 4.0:
                self.x += self.vx * dt
                self.y += self.vy * dt
            elif self.age_s < 9.0:
                # Steer perpendicular off corridor into concealment zone
                self.vx *= 0.85
                self.vy += 0.8 * dt
                self.x += self.vx * dt
                self.y += self.vy * dt
                self.is_hostile = True
            else:
                # Halted! Launch preparation sequence initiated
                self.vx = 0.0
                self.vy = 0.0
                self.is_hostile = True
                self.is_launch_prep = True
        elif self.behavior == "swarm_inbound":
            # Fast zig-zag evasive vector towards strategic center
            dist = math.hypot(self.x, self.y)
            if dist > 3.0:
                dx = -self.x / dist
                dy = -self.y / dist
                speed = 28.0 # 28 m/s = ~100 km/h
                # Add evasive wobble
                wobble = math.sin(self.age_s * 2.0) * 0.4
                self.vx = (dx + wobble) * 0.028
                self.vy = (dy - wobble) * 0.028
                self.x += self.vx * dt * 10
                self.y += self.vy * dt * 10
            self.is_hostile = True
        elif self.behavior == "hypersonic_vector":
            # Extremely fast vector towards sector
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.is_hostile = True
            if self.age_s > 2.0:
                self.is_launch_prep = True
        else:
            self.x += self.vx * dt
            self.y += self.vy * dt

class WorldSimulator:
    """
    Core Simulation Orchestrator:
    - Runs continuous sensor ticks
    - Multi-spectral Kalman-Bayesian Sensor Fusion
    - Anomaly Detection Brain
    - Hungarian Preemptive Target Allocator
    - Defense Asset engagement states
    """
    def __init__(self):
        self.sensor_gen = SyntheticSensorGenerator(seed=101)
        self.fusion_engine = SensorFusionEngine()
        self.ml_brain = AnomalyDetectionBrain()
        self.allocator = HungarianTargetAllocator()
        self.assets: List[DefenseAsset] = create_default_defense_network()

        self.targets: Dict[str, SimulatedTarget] = {}
        self.latest_fused_tracks: Dict[str, FusedTrack] = {}
        self.latest_assessments: Dict[str, AnomalyAssessment] = {}
        self.active_allocations: List[AllocationResult] = []

        self.current_scenario = "left_of_launch_tel"
        self.autonomous_mode = True
        self.sim_speed = 1.0
        self.total_anomalies_detected = 0
        self.total_allocations = 0
        self.total_neutralized = 0
        self.solver_latencies = [2.4, 3.1, 1.8]
        self.fusion_latencies = [0.9, 1.2, 0.8]

        self.load_scenario(self.current_scenario)

    def load_scenario(self, scenario_name: str):
        self.current_scenario = scenario_name
        self.targets.clear()
        self.latest_fused_tracks.clear()
        self.latest_assessments.clear()
        self.active_allocations.clear()
        self.assets = create_default_defense_network()

        if scenario_name == "peacetime_patrol":
            self.targets["TRK-701"] = SimulatedTarget(
                "TRK-701", "CIV-CARGO-77", -45.0, -22.5, 0.015, 0.0075,
                is_hostile=False, behavior="patrol_corridor"
            )
            self.targets["TRK-702"] = SimulatedTarget(
                "TRK-702", "PATROL-BORDER-04", 30.0, -30.0, -0.012, 0.012,
                is_hostile=False, behavior="patrol_corridor"
            )
            self.targets["TRK-703"] = SimulatedTarget(
                "TRK-703", "AIR-COMM-812", -35.0, 0.0, 0.035, 0.0,
                is_hostile=False, behavior="patrol_corridor"
            )

        elif scenario_name == "left_of_launch_tel":
            # Normal routine traffic
            self.targets["TRK-101"] = SimulatedTarget(
                "TRK-101", "CIV-COMM-14", -40.0, -20.0, 0.018, 0.009,
                is_hostile=False, behavior="patrol_corridor"
            )
            self.targets["TRK-102"] = SimulatedTarget(
                "TRK-102", "COMM-TRANSIT-22", -30.0, 30.0, 0.014, -0.014,
                is_hostile=False, behavior="patrol_corridor"
            )
            # The Rogue Mobile TEL
            self.targets["TRK-TEL-99"] = SimulatedTarget(
                "TRK-TEL-99", "SUSPECT-TEL-99", -38.0, 22.0, 0.016, -0.008,
                is_hostile=False, behavior="deviate_and_stop"
            )

        elif scenario_name == "multi_axis_swarm":
            self.targets["SWARM-ALPHA"] = SimulatedTarget(
                "SWARM-ALPHA", "UAV-SWARM-A1", -32.0, 28.0, 0.0, 0.0,
                is_hostile=True, behavior="swarm_inbound"
            )
            self.targets["SWARM-BRAVO"] = SimulatedTarget(
                "SWARM-BRAVO", "UAV-SWARM-B2", 35.0, 25.0, 0.0, 0.0,
                is_hostile=True, behavior="swarm_inbound"
            )
            self.targets["SWARM-CHARLIE"] = SimulatedTarget(
                "SWARM-CHARLIE", "UAV-SWARM-C3", -25.0, -32.0, 0.0, 0.0,
                is_hostile=True, behavior="swarm_inbound"
            )
            # Civilian airliner in background
            self.targets["TRK-CIV-09"] = SimulatedTarget(
                "TRK-CIV-09", "AIR-BOEING-77", -50.0, 25.0, 0.040, 0.020,
                is_hostile=False, behavior="patrol_corridor"
            )

        elif scenario_name == "hypersonic_vector":
            self.targets["HYPER-01"] = SimulatedTarget(
                "HYPER-01", "HYPERSO-GLIDE-X", -58.0, 35.0, 0.095, -0.055,
                is_hostile=True, behavior="hypersonic_vector"
            )
            self.targets["TRK-CIV-04"] = SimulatedTarget(
                "TRK-CIV-04", "CIV-TRUCK-88", 10.0, -10.0, 0.015, -0.015,
                is_hostile=False, behavior="patrol_corridor"
            )

    def step(self, dt: float = 0.2):
        effective_dt = dt * self.sim_speed

        # 1. Update targets kinematics
        for target in list(self.targets.values()):
            if not target.alive:
                continue
            target.step(effective_dt)

            # 2. Generate multi-spectral raw sensor bundle (Radar + Satellite + SIGINT)
            t_fusion_start = time.time()
            bundle = self.sensor_gen.bundle_all_sensors(
                target.track_id,
                target.x,
                target.y,
                target.vx,
                target.vy,
                is_hostile=target.is_hostile,
                is_launch_prep=target.is_launch_prep
            )

            # 3. Kalman + Bayesian Sensor Fusion
            fused = self.fusion_engine.fuse_bundle(bundle, callsign=target.callsign)
            target.history.append(fused)
            if len(target.history) > 30:
                target.history.pop(0)
            self.latest_fused_tracks[target.track_id] = fused

            f_lat = (time.time() - t_fusion_start) * 1000.0
            self.fusion_latencies.append(f_lat)
            if len(self.fusion_latencies) > 50:
                self.fusion_latencies.pop(0)

            # 4. Anomaly Detection Brain
            assessment = self.ml_brain.assess_track(fused, target.history)
            self.latest_assessments[target.track_id] = assessment
            if assessment.threat_level in [ThreatLevel.HOSTILE, ThreatLevel.CRITICAL_LAUNCH]:
                self.total_anomalies_detected += 1

        # 5. Target Allocation Router (if autonomous mode is ON)
        if self.autonomous_mode:
            t_solve_start = time.time()
            active_threat_pairs = [
                (self.latest_fused_tracks[tid], self.latest_assessments[tid])
                for tid, t in self.targets.items()
                if t.alive and not t.neutralized and tid in self.latest_fused_tracks
            ]

            allocations = self.allocator.allocate_targets(active_threat_pairs, self.assets)
            self.active_allocations = allocations

            s_lat = (time.time() - t_solve_start) * 1000.0
            self.solver_latencies.append(s_lat)
            if len(self.solver_latencies) > 50:
                self.solver_latencies.pop(0)

            # 6. Apply suppression engagement effects to defense assets and targets
            self.apply_suppression_effects(effective_dt)

        # 7. Update asset cooldowns
        for asset in self.assets:
            if asset.status == AssetStatus.COOLDOWN:
                asset.cooldown_remaining_s = max(0.0, asset.cooldown_remaining_s - effective_dt)
                if asset.cooldown_remaining_s <= 0:
                    asset.status = AssetStatus.READY
                    asset.target_track_id = None

    def apply_suppression_effects(self, dt: float):
        allocated_map = {alloc.track_id: alloc for alloc in self.active_allocations}

        for target_id, alloc in allocated_map.items():
            target = self.targets.get(target_id)
            if not target or not target.alive or target.neutralized:
                continue

            # Find matching asset
            asset = next((a for a in self.assets if a.asset_id == alloc.asset_id), None)
            if not asset:
                continue

            asset.status = AssetStatus.ENGAGED
            asset.target_track_id = target_id

            # Increment neutralization progress
            progress_rate = 1.0 / max(0.5, alloc.estimated_time_to_suppress_s)
            target.neutralize_progress += progress_rate * dt

            # Decrement ammo or battery charge slightly
            asset.ammo_or_charge_pct = max(0.0, asset.ammo_or_charge_pct - (2.0 * dt))

            if target.neutralize_progress >= 1.0:
                # Target Successfully Neutralized Preemptively!
                target.neutralized = True
                target.alive = False
                self.total_neutralized += 1
                alloc.status = "PREEMPTIVELY_NEUTRALIZED"

                # Asset transitions to cooldown
                asset.status = AssetStatus.COOLDOWN
                asset.cooldown_remaining_s = 3.5

    def manual_authorize(self, track_id: str, asset_id: str):
        target = self.targets.get(track_id)
        asset = next((a for a in self.assets if a.asset_id == asset_id), None)
        if target and asset:
            asset.status = AssetStatus.ENGAGED
            target.neutralize_progress = 1.0
            target.neutralized = True
            target.alive = False
            self.total_neutralized += 1

    def get_world_snapshot(self) -> Dict[str, Any]:
        tracks_list = [t.model_dump() for t in self.latest_fused_tracks.values() if self.targets.get(t.track_id, SimulatedTarget("", "", 0, 0, 0, 0)).alive]
        assessments_map = {tid: a.model_dump() for tid, a in self.latest_assessments.items()}
        assets_list = [a.model_dump() for a in self.assets]
        allocations_list = [a.model_dump() for a in self.active_allocations]

        metrics = SystemMetrics(
            active_threats=len([t for t in self.targets.values() if t.alive and t.is_hostile]),
            anomalies_detected=self.total_anomalies_detected,
            allocations_executed=len(self.active_allocations),
            neutralized_count=self.total_neutralized,
            mean_solver_latency_ms=round(sum(self.solver_latencies) / max(1, len(self.solver_latencies)), 2),
            mean_fusion_latency_ms=round(sum(self.fusion_latencies) / max(1, len(self.fusion_latencies)), 2),
            avg_pk_success_rate=0.89,
            autonomous_mode=self.autonomous_mode
        )

        return {
            "timestamp": time.time(),
            "scenario": self.current_scenario,
            "metrics": metrics.model_dump(),
            "tracks": tracks_list,
            "assessments": assessments_map,
            "assets": assets_list,
            "allocations": allocations_list,
            "targets_meta": {
                tid: {
                    "callsign": t.callsign,
                    "alive": t.alive,
                    "neutralized": t.neutralized,
                    "neutralize_progress": round(t.neutralize_progress, 2),
                    "is_launch_prep": t.is_launch_prep
                } for tid, t in self.targets.items()
            }
        }
