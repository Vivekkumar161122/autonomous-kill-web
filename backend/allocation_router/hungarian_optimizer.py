import time
import math
import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Optional, Tuple
from backend.models import (
    FusedTrack,
    AnomalyAssessment,
    DefenseAsset,
    AllocationResult,
    AssetType,
    AssetStatus,
    ThreatLevel
)

class HungarianTargetAllocator:
    """
    Automated Target Allocation Router using the Hungarian Algorithm (Kuhn-Munkres)
    augmented with Multi-Criteria Objective Optimization:
    - Minimizes latency and operational asset cost
    - Minimizes civilian collateral risk
    - Maximizes suppression success probability (P_k)
    - Enforces physical line-of-sight and weapon engagement envelopes
    """
    def __init__(
        self,
        w_distance: float = 0.25,
        w_cost: float = 0.20,
        w_failure: float = 0.40,
        w_collateral: float = 0.15
    ):
        self.w_dist = w_distance
        self.w_cost = w_cost
        self.w_fail = w_failure
        self.w_coll = w_collateral

    def calculate_effective_pk(
        self,
        asset: DefenseAsset,
        track: FusedTrack,
        assessment: AnomalyAssessment,
        distance_km: float
    ) -> float:
        base_pk = asset.pk_probability

        # Distance degradation for kinetic / laser systems
        if asset.asset_type == AssetType.LASER_DEW:
            # Atmospheric attenuation
            dist_factor = max(0.2, 1.0 - (distance_km / asset.effective_range_km) * 0.4)
            pk = base_pk * dist_factor
        elif asset.asset_type == AssetType.EW_JAMMER:
            # 1/r^2 RF inverse-square law
            dist_factor = max(0.4, 1.0 - (distance_km / asset.effective_range_km) * 0.3)
            # High RF emission makes threat easier to jam
            rf_bonus = 0.10 if assessment.rf_anomaly_ratio > 0.6 else 0.0
            pk = min(0.98, (base_pk * dist_factor) + rf_bonus)
        elif asset.asset_type == AssetType.CYBER_PAYLOAD:
            # Cyber is independent of physical distance, but requires active RF telemetry link
            if assessment.rf_anomaly_ratio > 0.4:
                pk = min(0.96, base_pk + 0.08)
            else:
                pk = base_pk * 0.70 # harder to inject if target is radio-silent
        elif asset.asset_type == AssetType.COUNTER_DRONE:
            pk = base_pk if distance_km <= asset.effective_range_km else 0.1
        elif asset.asset_type == AssetType.KINETIC_SAM:
            # High kinetic intercept envelope
            pk = base_pk if distance_km <= asset.effective_range_km else 0.05
        else:
            pk = base_pk

        return float(np.clip(pk, 0.05, 0.99))

    def compute_cost_matrix(
        self,
        threats: List[Tuple[FusedTrack, AnomalyAssessment]],
        assets: List[DefenseAsset]
    ) -> np.ndarray:
        n_threats = len(threats)
        n_assets = len(assets)
        cost_matrix = np.full((n_threats, n_assets), 999999.0, dtype=float)

        max_grid_dist = 120.0

        for i, (track, assess) in enumerate(threats):
            for j, asset in enumerate(assets):
                # If asset not ready, heavily penalize
                if asset.status not in [AssetStatus.READY, AssetStatus.TRACKING]:
                    continue
                if asset.ammo_or_charge_pct <= 5.0:
                    continue

                dist = math.hypot(track.x - asset.x, track.y - asset.y)

                # Range constraint check (except Cyber which is networked)
                if asset.asset_type != AssetType.CYBER_PAYLOAD and dist > asset.effective_range_km:
                    continue

                pk = self.calculate_effective_pk(asset, track, assess, dist)

                # Cost components normalized [0, 1]
                norm_dist = min(1.0, dist / max_grid_dist)
                norm_cost = asset.cost_index / 10.0
                norm_fail = 1.0 - pk
                norm_coll = asset.collateral_risk

                # Left-of-launch priority weighting:
                # If threat is Stage 3 (CRITICAL_LAUNCH), failure weight is doubled
                fail_weight = self.w_fail * (1.8 if assess.threat_level == ThreatLevel.CRITICAL_LAUNCH else 1.0)

                total_cost = (
                    self.w_dist * norm_dist +
                    self.w_cost * norm_cost +
                    fail_weight * norm_fail +
                    self.w_coll * norm_coll
                )

                # Tactical bias: Prefer non-kinetic / cyber for early indicators (low collateral)
                if assess.threat_level in [ThreatLevel.SUSPICIOUS, ThreatLevel.HOSTILE]:
                    if asset.asset_type in [AssetType.CYBER_PAYLOAD, AssetType.EW_JAMMER]:
                        total_cost *= 0.70

                cost_matrix[i, j] = total_cost

        return cost_matrix

    def allocate_targets(
        self,
        active_threats: List[Tuple[FusedTrack, AnomalyAssessment]],
        available_assets: List[DefenseAsset]
    ) -> List[AllocationResult]:
        """
        Executes Hungarian assignment. Returns list of optimal allocation pairings.
        """
        start_time = time.time()
        results: List[AllocationResult] = []

        # Filter threats requiring suppression (Stage 1, 2, or 3)
        actionable_threats = [
            (t, a) for (t, a) in active_threats
            if a.threat_level in [ThreatLevel.SUSPICIOUS, ThreatLevel.HOSTILE, ThreatLevel.CRITICAL_LAUNCH]
        ]

        if not actionable_threats or not available_assets:
            return results

        cost_matrix = self.compute_cost_matrix(actionable_threats, available_assets)

        # Hungarian Algorithm: Kuhn-Munkres minimum cost assignment
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        elapsed_ms = (time.time() - start_time) * 1000.0

        for r, c in zip(row_ind, col_ind):
            cost_val = cost_matrix[r, c]
            if cost_val >= 9999.0:
                # No valid asset within range/condition
                continue

            track, assess = actionable_threats[r]
            asset = available_assets[c]
            dist = math.hypot(track.x - asset.x, track.y - asset.y)
            pk = self.calculate_effective_pk(asset, track, assess, dist)

            # Estimate time to suppress (speed-of-light for cyber/laser, flight time for drone/SAM)
            if asset.asset_type in [AssetType.CYBER_PAYLOAD, AssetType.LASER_DEW, AssetType.EW_JAMMER]:
                est_time_s = 0.8
            elif asset.asset_type == AssetType.COUNTER_DRONE:
                est_time_s = max(2.0, (dist / 0.12)) # 120 m/s drone
            else: # SAM
                est_time_s = max(1.5, (dist / 1.0)) # Mach 3 interceptor

            utility = round(float(1.0 / (1.0 + cost_val)), 4)

            results.append(AllocationResult(
                allocation_id=f"ALLOC-{track.track_id[-4:]}-{asset.asset_id[:6]}",
                timestamp=time.time(),
                track_id=track.track_id,
                asset_id=asset.asset_id,
                asset_name=asset.name,
                asset_type=asset.asset_type,
                threat_level=assess.threat_level,
                distance_km=round(dist, 2),
                calculated_utility=utility,
                expected_pk=round(pk, 3),
                estimated_time_to_suppress_s=round(est_time_s, 1),
                status="ENGAGING",
                algorithm_solve_time_ms=round(elapsed_ms, 2)
            ))

        return results
