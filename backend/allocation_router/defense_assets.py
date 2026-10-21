from typing import List
from backend.models import DefenseAsset, AssetType, AssetStatus

def create_default_defense_network() -> List[DefenseAsset]:
    """
    Initializes a multi-layered automated preemptive defense network:
    1. Cyber-Physical Infiltration Node (Global/Networked range, zero collateral)
    2. Tactical Electronic Warfare Jammer Tower Alpha & Bravo
    3. Directed Energy Weapon (DEW Laser Battery)
    4. C-UAS Autonomous Interceptor Drone Swarm Hub
    5. PATRIOT/Iron-Dome Style Kinetic SAM Battery
    """
    return [
        DefenseAsset(
            asset_id="NODE-CYBER-01",
            name="Aegis-Cyber Injection Gateway",
            asset_type=AssetType.CYBER_PAYLOAD,
            x=0.0,
            y=0.0,
            effective_range_km=150.0,
            pk_probability=0.88,
            cost_index=1.0,           # Minimal financial cost per activation
            collateral_risk=0.01,     # Zero kinetic collateral
            status=AssetStatus.READY,
            ammo_or_charge_pct=100.0
        ),
        DefenseAsset(
            asset_id="NODE-EW-ALPHA",
            name="Valkyrie High-Power EW Jammer (North)",
            asset_type=AssetType.EW_JAMMER,
            x=-18.0,
            y=24.0,
            effective_range_km=50.0,
            pk_probability=0.82,
            cost_index=2.5,
            collateral_risk=0.05,
            status=AssetStatus.READY,
            ammo_or_charge_pct=95.0
        ),
        DefenseAsset(
            asset_id="NODE-EW-BRAVO",
            name="Valkyrie High-Power EW Jammer (South)",
            asset_type=AssetType.EW_JAMMER,
            x=15.0,
            y=-20.0,
            effective_range_km=50.0,
            pk_probability=0.80,
            cost_index=2.5,
            collateral_risk=0.05,
            status=AssetStatus.READY,
            ammo_or_charge_pct=92.0
        ),
        DefenseAsset(
            asset_id="NODE-LASER-DEW",
            name="Helios-IV High Energy Laser (DEW)",
            asset_type=AssetType.LASER_DEW,
            x=-5.0,
            y=-10.0,
            effective_range_km=28.0,
            pk_probability=0.91,
            cost_index=4.0,
            collateral_risk=0.08,
            status=AssetStatus.READY,
            ammo_or_charge_pct=90.0
        ),
        DefenseAsset(
            asset_id="NODE-DRONE-SWARM",
            name="Hornet Interceptor Drone Hub",
            asset_type=AssetType.COUNTER_DRONE,
            x=20.0,
            y=15.0,
            effective_range_km=38.0,
            pk_probability=0.86,
            cost_index=5.0,
            collateral_risk=0.15,
            status=AssetStatus.READY,
            ammo_or_charge_pct=85.0
        ),
        DefenseAsset(
            asset_id="NODE-SAM-BATTERY",
            name="Iron Shield Kinetic SAM Battery",
            asset_type=AssetType.KINETIC_SAM,
            x=-2.0,
            y=5.0,
            effective_range_km=75.0,
            pk_probability=0.95,
            cost_index=8.5,           # High missile replenishment cost
            collateral_risk=0.30,     # Debris / kinetic splash
            status=AssetStatus.READY,
            ammo_or_charge_pct=100.0
        )
    ]
