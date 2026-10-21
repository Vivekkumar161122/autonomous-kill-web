import numpy as np
import pandas as pd
import os
import math

def generate_synthetic_threat_dataset(n_samples: int = 4000, seed: int = 42) -> pd.DataFrame:
    """
    Generates synthetic feature vectors representing:
    Class 0 (Normal Peacetime / Routine Commercial): 85%
    Class 1 (Hostile Preparation / Left-of-Launch Anomaly): 15%

    Features:
    1. velocity_mps: Object speed (m/s)
    2. velocity_variance: Jerk / acceleration variance
    3. off_corridor_dist_km: Distance from designated civilian / peacetime transit corridors
    4. rcs_dbm2: Radar Cross Section
    5. rf_power_dbm: Radio Frequency burst power
    6. rf_entropy: Military encryption entropy of signal
    7. proximity_to_strategic_asset_km: Distance to friendly airbase/nuclear command/capital
    8. stationary_dwell_min: Time spent halted in non-designated staging area
    """
    rng = np.random.default_rng(seed)
    n_normal = int(n_samples * 0.85)
    n_hostile = n_samples - n_normal

    # Normal baseline samples
    normal_vel = rng.normal(loc=22.0, scale=6.0, size=n_normal) # ~80 km/h ground or routine speed
    normal_vel = np.clip(normal_vel, 2.0, 45.0)
    normal_vel_var = rng.exponential(scale=1.5, size=n_normal)
    normal_corridor = rng.exponential(scale=0.8, size=n_normal) # tightly follows road corridor
    normal_rcs = rng.normal(loc=12.0, scale=2.5, size=n_normal) # standard truck / small air frame
    normal_rf = rng.normal(loc=-12.0, scale=5.0, size=n_normal) # low routine RF
    normal_entropy = rng.beta(a=2, b=5, size=n_normal) # low to medium entropy
    normal_strategic_dist = rng.uniform(low=25.0, high=120.0, size=n_normal)
    normal_dwell = rng.exponential(scale=2.0, size=n_normal)

    df_normal = pd.DataFrame({
        "velocity_mps": normal_vel,
        "velocity_variance": normal_vel_var,
        "off_corridor_dist_km": normal_corridor,
        "rcs_dbm2": normal_rcs,
        "rf_power_dbm": normal_rf,
        "rf_entropy": normal_entropy,
        "strategic_proximity_km": normal_strategic_dist,
        "stationary_dwell_min": normal_dwell,
        "is_hostile": 0
    })

    # Hostile Left-of-Launch Anomaly samples
    # Features of mobile missile TEL or covert staging:
    # Off designated highway into tree line/clearing, sudden deceleration, high dwell time,
    # large RF telemetry spike before launch, increased RCS as hydraulic canisters erect
    hostile_vel = rng.choice([
        rng.normal(loc=5.0, scale=2.0, size=n_hostile),   # creeping into firing position
        rng.normal(loc=65.0, scale=10.0, size=n_hostile)  # high speed sprint to evasion point
    ])
    hostile_vel = np.clip(hostile_vel, 0.0, 95.0)
    hostile_vel_var = rng.exponential(scale=8.0, size=n_hostile) + 5.0 # extreme acceleration/braking
    hostile_corridor = rng.uniform(low=4.0, high=22.0, size=n_hostile) # completely off corridor
    hostile_rcs = rng.normal(loc=24.0, scale=4.0, size=n_hostile) # large TEL / erector boom reflection
    hostile_rf = rng.normal(loc=38.0, scale=8.0, size=n_hostile) # massive tactical telemetry burst
    hostile_entropy = rng.beta(a=8, b=2, size=n_hostile) # heavy military encryption (~0.85-0.98)
    hostile_strategic_dist = rng.uniform(low=2.0, high=28.0, size=n_hostile) # threatening critical zone
    hostile_dwell = rng.exponential(scale=18.0, size=n_hostile) + 10.0 # halted in concealment

    df_hostile = pd.DataFrame({
        "velocity_mps": hostile_vel,
        "velocity_variance": hostile_vel_var,
        "off_corridor_dist_km": hostile_corridor,
        "rcs_dbm2": hostile_rcs,
        "rf_power_dbm": hostile_rf,
        "rf_entropy": hostile_entropy,
        "strategic_proximity_km": hostile_strategic_dist,
        "stationary_dwell_min": hostile_dwell,
        "is_hostile": 1
    })

    df = pd.concat([df_normal, df_hostile], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = generate_synthetic_threat_dataset()
    path = "data/synthetic_military_patterns.csv"
    df.to_csv(path, index=False)
    print(f"Dataset generated at {path} with {len(df)} records ({df['is_hostile'].sum()} hostile).")
