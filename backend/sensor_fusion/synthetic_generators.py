import numpy as np
import time
import math
from typing import Dict, Any, Tuple
from backend.models import RadarLog, SatelliteObservation, RfSigintBurst, RawSensorBundle

# Strategic center coordinates (Reference base station)
CENTER_LAT = 34.0522
CENTER_LON = -118.2437
KM_PER_LAT = 111.0
KM_PER_LON = 111.0 * math.cos(math.radians(CENTER_LAT))

def latlon_to_cartesian(lat: float, lon: float) -> Tuple[float, float]:
    x = (lon - CENTER_LON) * KM_PER_LON
    y = (lat - CENTER_LAT) * KM_PER_LAT
    return x, y

def cartesian_to_latlon(x: float, y: float) -> Tuple[float, float]:
    lat = CENTER_LAT + (y / KM_PER_LAT)
    lon = CENTER_LON + (x / KM_PER_LON)
    return lat, lon

class SyntheticSensorGenerator:
    """
    Simulates three independent multi-spectral intelligence feeds:
    1. Ground-based Pulse Doppler Radar (Azimuth, Range, Doppler, RCS)
    2. Space-based Synthetic Aperture Radar (SAR) / Optical Satellite (GPS, Convoy cluster)
    3. Airborne / Ground SIGINT Radio Frequency Array (MHz center frequency, power spike, military encryption entropy)
    """
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def generate_radar_log(
        self,
        true_x: float,
        true_y: float,
        true_vx: float,
        true_vy: float,
        base_rcs: float = 12.0,
        is_hostile: bool = False
    ) -> RadarLog:
        # Distance & angle from origin (0,0) where radar sits
        distance = math.hypot(true_x, true_y)
        azimuth_deg = (math.degrees(math.atan2(true_x, true_y)) + 360.0) % 360.0

        # Radial doppler velocity
        if distance > 1e-4:
            radial_vel = (true_x * true_vx + true_y * true_vy) / distance
        else:
            radial_vel = 0.0

        # Radar noise characteristics (Gaussian noise on range and azimuth)
        range_noise = self.rng.normal(0, 0.08) # 80m standard deviation
        azimuth_noise = self.rng.normal(0, 0.35) # 0.35 degrees noise
        meas_range = max(0.1, distance + range_noise)
        meas_azimuth = (azimuth_deg + azimuth_noise) % 360.0

        # Radar Cross Section (RCS) fluctuations (Swerling model representation)
        rcs_fluctuation = self.rng.normal(0, 1.5)
        if is_hostile:
            # Active missile canister erection or radar lock causes sudden RCS shift
            rcs = base_rcs + 6.0 + rcs_fluctuation
        else:
            rcs = max(1.0, base_rcs + rcs_fluctuation)

        snr = max(5.0, 32.0 - (20 * math.log10(max(1.0, distance))) + self.rng.normal(0, 1.0))

        return RadarLog(
            sensor_id="AN/MPQ-64-RADAR",
            timestamp=time.time(),
            azimuth_deg=round(meas_azimuth, 2),
            range_km=round(meas_range, 3),
            doppler_mps=round(radial_vel + self.rng.normal(0, 0.5), 2),
            rcs_dbm2=round(rcs, 2),
            snr_db=round(snr, 1)
        )

    def generate_satellite_obs(
        self,
        true_x: float,
        true_y: float,
        true_alt: float = 150.0,
        is_hostile: bool = False
    ) -> SatelliteObservation:
        # True coordinates converted to lat/lon + GPS atmospheric jitter
        jitter_x = self.rng.normal(0, 0.05) # 50m jitter
        jitter_y = self.rng.normal(0, 0.05)
        noisy_x = true_x + jitter_x
        noisy_y = true_y + jitter_y
        meas_lat, meas_lon = cartesian_to_latlon(noisy_x, noisy_y)

        # Tactical optical confidence
        confidence = float(np.clip(self.rng.normal(0.88, 0.05), 0.5, 0.99))
        convoy_count = int(self.rng.choice([1, 2, 3, 5]) if is_hostile else 1)

        return SatelliteObservation(
            sensor_id="SENTINEL-SAR-03",
            timestamp=time.time(),
            lat=round(meas_lat, 6),
            lon=round(meas_lon, 6),
            altitude_m=round(true_alt + self.rng.normal(0, 2.0), 1),
            convoy_count=convoy_count,
            optical_confidence=round(confidence, 3)
        )

    def generate_sigint_burst(
        self,
        is_hostile: bool = False,
        is_launch_prep: bool = False
    ) -> RfSigintBurst:
        if is_launch_prep:
            # Military telemetry frequency, massive RF spike, high entropy encryption
            center_freq = 433.92 + self.rng.normal(0, 0.5)
            bandwidth = 20.0 + self.rng.normal(0, 2.0)
            power_dbm = 48.0 + self.rng.normal(0, 3.0) # High power transmit
            duration = 450.0 + self.rng.normal(0, 50.0)
            entropy = 0.94 + self.rng.normal(0, 0.02)
        elif is_hostile:
            # Suspicious tactical command net chatter
            center_freq = 312.5 + self.rng.normal(0, 1.0)
            bandwidth = 10.0 + self.rng.normal(0, 1.0)
            power_dbm = 28.0 + self.rng.normal(0, 2.5)
            duration = 180.0 + self.rng.normal(0, 30.0)
            entropy = 0.82 + self.rng.normal(0, 0.04)
        else:
            # Routine commercial / low-power baseline
            center_freq = 1575.42 + self.rng.normal(0, 2.0)
            bandwidth = 2.0 + self.rng.normal(0, 0.2)
            power_dbm = -10.0 + self.rng.normal(0, 4.0)
            duration = 35.0 + self.rng.normal(0, 10.0)
            entropy = 0.35 + self.rng.normal(0, 0.08)

        return RfSigintBurst(
            sensor_id="SIGINT-ECHELON-V",
            timestamp=time.time(),
            center_freq_mhz=round(float(center_freq), 2),
            bandwidth_mhz=round(float(bandwidth), 2),
            signal_power_dbm=round(float(power_dbm), 2),
            burst_duration_ms=round(float(duration), 1),
            chatter_entropy=round(float(np.clip(entropy, 0.1, 0.99)), 3)
        )

    def bundle_all_sensors(
        self,
        track_id: str,
        true_x: float,
        true_y: float,
        true_vx: float,
        true_vy: float,
        is_hostile: bool = False,
        is_launch_prep: bool = False
    ) -> RawSensorBundle:
        radar = self.generate_radar_log(true_x, true_y, true_vx, true_vy, is_hostile=is_hostile)
        satellite = self.generate_satellite_obs(true_x, true_y, is_hostile=is_hostile)
        sigint = self.generate_sigint_burst(is_hostile=is_hostile, is_launch_prep=is_launch_prep)

        return RawSensorBundle(
            track_id=track_id,
            radar=radar,
            satellite=satellite,
            sigint=sigint
        )
