import numpy as np
import math
import time
from typing import Dict, Optional, Tuple
from backend.models import RawSensorBundle, FusedTrack
from backend.sensor_fusion.synthetic_generators import latlon_to_cartesian, cartesian_to_latlon

class KalmanTrackFilter:
    """
    2D Kinematic Kalman Filter:
    State: [x, y, vx, vy] in km and km/s
    """
    def __init__(self, init_x: float, init_y: float, init_vx: float = 0.0, init_vy: float = 0.0):
        self.state = np.array([init_x, init_y, init_vx, init_vy], dtype=float)
        # Covariance matrix P
        self.P = np.diag([1.0, 1.0, 0.5, 0.5])
        # Process noise Q
        self.q_pos = 0.02
        self.q_vel = 0.05
        # Last update timestamp
        self.last_t = time.time()

    def predict(self, dt: float):
        if dt <= 0:
            dt = 0.1
        # State transition matrix F
        F = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        # Process noise covariance Q
        dt2 = 0.5 * (dt ** 2)
        G = np.array([
            [dt2, 0.0],
            [0.0, dt2],
            [dt, 0.0],
            [0.0, dt]
        ])
        Q = G @ np.diag([self.q_pos, self.q_vel]) @ G.T

        # Predict step
        self.state = F @ self.state
        self.P = F @ self.P @ F.T + Q

    def update(self, z: np.ndarray, R: np.ndarray):
        """
        Measurement update:
        z is measured [x, y]
        R is measurement noise covariance matrix
        """
        H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0]
        ])
        y = z - (H @ self.state) # Innovation / measurement residual
        S = H @ self.P @ H.T + R # Innovation covariance
        try:
            K = self.P @ H.T @ np.linalg.inv(S) # Kalman gain
        except np.linalg.LinAlgError:
            K = np.zeros((4, 2))

        self.state = self.state + (K @ y)
        I = np.eye(4)
        self.P = (I - K @ H) @ self.P

class SensorFusionEngine:
    """
    Multi-Sensor Fusion Engine combining Radar, Satellite GPS, and SIGINT RF.
    Maintains Kalman tracks and applies Bayesian Evidence Fusion for confidence.
    """
    def __init__(self):
        self.filters: Dict[str, KalmanTrackFilter] = {}

    def fuse_bundle(self, bundle: RawSensorBundle, callsign: str = "TARGET-UNKNOWN") -> FusedTrack:
        now = time.time()
        track_id = bundle.track_id

        # 1. Convert Radar polar measurement (range, azimuth) to Cartesian (x, y)
        rad_az = math.radians(bundle.radar.azimuth_deg)
        radar_x = bundle.radar.range_km * math.sin(rad_az)
        radar_y = bundle.radar.range_km * math.cos(rad_az)

        # 2. Convert Satellite GPS measurement (lat, lon) to Cartesian (x, y)
        sat_x, sat_y = latlon_to_cartesian(bundle.satellite.lat, bundle.satellite.lon)

        # 3. Kalman state estimation
        if track_id not in self.filters:
            # Initialize filter with weighted average of radar and sat
            init_x = 0.5 * (radar_x + sat_x)
            init_y = 0.5 * (radar_y + sat_y)
            self.filters[track_id] = KalmanTrackFilter(init_x, init_y)

        kf = self.filters[track_id]
        dt = max(0.01, now - kf.last_t)
        kf.last_t = now

        # Predict
        kf.predict(dt)

        # Update using Satellite (R_sat)
        # GPS standard deviation approx 50m = 0.05km
        R_sat = np.diag([0.05**2, 0.05**2])
        kf.update(np.array([sat_x, sat_y]), R_sat)

        # Update using Radar (R_radar)
        # Radar noise depends on SNR
        radar_err = max(0.02, 0.15 / (bundle.radar.snr_db / 10.0))
        R_radar = np.diag([radar_err**2, radar_err**2])
        kf.update(np.array([radar_x, radar_y]), R_radar)

        fused_x = float(kf.state[0])
        fused_y = float(kf.state[1])
        fused_vx = float(kf.state[2]) # km/s
        fused_vy = float(kf.state[3]) # km/s

        fused_speed_mps = float(math.hypot(fused_vx, fused_vy) * 1000.0) # convert to m/s
        heading_deg = float((math.degrees(math.atan2(fused_vx, fused_vy)) + 360.0) % 360.0)

        fused_lat, fused_lon = cartesian_to_latlon(fused_x, fused_y)

        # Kinematic positional uncertainty from trace of covariance P
        kinematic_uncertainty = float(math.sqrt(max(1e-6, np.trace(kf.P[:2, :2]))))

        # Bayesian Evidence Fusion for confidence
        # Combines radar SNR + satellite optical confidence + SIGINT signal power
        snr_factor = np.clip(bundle.radar.snr_db / 35.0, 0.1, 1.0)
        sat_factor = np.clip(bundle.satellite.optical_confidence, 0.1, 1.0)
        sigint_factor = np.clip((bundle.sigint.signal_power_dbm + 30.0) / 80.0, 0.1, 1.0)

        # Multiplicative Bayesian belief update
        prior = 0.5
        likelihood = (snr_factor * 0.45) + (sat_factor * 0.40) + (sigint_factor * 0.15)
        fused_confidence = float(np.clip(likelihood * 0.95 + (1.0 / (1.0 + kinematic_uncertainty)) * 0.05, 0.1, 0.99))

        # Convert RF power from dBm to milliwatts
        rf_mw = float(10 ** (bundle.sigint.signal_power_dbm / 10.0))

        return FusedTrack(
            track_id=track_id,
            timestamp=now,
            callsign=callsign,
            lat=round(fused_lat, 6),
            lon=round(fused_lon, 6),
            x=round(fused_x, 3),
            y=round(fused_y, 3),
            velocity_mps=round(fused_speed_mps, 1),
            heading_deg=round(heading_deg, 1),
            altitude_m=bundle.satellite.altitude_m,
            rcs_dbm2=bundle.radar.rcs_dbm2,
            rf_intensity_mw=round(rf_mw, 2),
            kinematic_uncertainty=round(kinematic_uncertainty, 4),
            fused_confidence=round(fused_confidence, 3)
        )
