class TacticalCanvas {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.sweepAngle = 0;
    this.scale = 1.0; // pixels per km
    this.centerX = 0;
    this.centerY = 0;
    this.selectedTrackId = null;

    this.latestState = {
      tracks: [],
      assets: [],
      allocations: [],
      assessments: {},
      targets_meta: {}
    };

    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.canvas.addEventListener('click', (e) => this.handleClick(e));

    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.canvas.style.width = `${rect.width}px`;
    this.canvas.style.height = `${rect.height}px`;

    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    this.centerX = rect.width / 2;
    this.centerY = rect.height / 2;
    // Map approx 140km across screen height
    this.scale = (Math.min(rect.width, rect.height) * 0.85) / 140.0;
  }

  kmToPixel(kmX, kmY) {
    return {
      x: this.centerX + (kmX * this.scale),
      y: this.centerY - (kmY * this.scale) // Y is inverted in canvas
    };
  }

  pixelToKm(px, py) {
    return {
      x: (px - this.centerX) / this.scale,
      y: (this.centerY - py) / this.scale
    };
  }

  updateState(state) {
    this.latestState = state;
  }

  handleClick(e) {
    const rect = this.canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    let closestId = null;
    let minD = 20; // 20px threshold

    for (const track of this.latestState.tracks) {
      const pos = this.kmToPixel(track.x, track.y);
      const d = Math.hypot(clickX - pos.x, clickY - pos.y);
      if (d < minD) {
        minD = d;
        closestId = track.track_id;
      }
    }

    if (closestId) {
      this.selectedTrackId = closestId;
      if (window.onTrackSelected) {
        window.onTrackSelected(closestId);
      }
    }
  }

  animate() {
    const w = this.canvas.width / window.devicePixelRatio;
    const h = this.canvas.height / window.devicePixelRatio;

    // Clear background
    this.ctx.fillStyle = '#060a12';
    this.ctx.fillRect(0, 0, w, h);

    // 1. Draw Tactical Grid & Range Rings
    this.drawGridAndRings();

    // 2. Draw Civilian Designated Corridors
    this.drawCivilianCorridors();

    // 3. Draw Rotating Radar Sweep
    this.drawRadarSweep();

    // 4. Draw Defensive Asset Bases & Range Bubbles
    this.drawDefenseAssets();

    // 5. Draw Kill-Web Allocation Directed Beams
    this.drawKillWebBeams();

    // 6. Draw Targets & Telemetry Tracks
    this.drawTargets();

    // Advance sweep angle
    this.sweepAngle = (this.sweepAngle + 0.02) % (Math.PI * 2);

    requestAnimationFrame(this.animate);
  }

  drawGridAndRings() {
    const ctx = this.ctx;
    const rings = [25, 50, 70];

    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.12)';
    ctx.fillStyle = 'rgba(0, 240, 255, 0.4)';
    ctx.font = '10px "JetBrains Mono"';

    // Range rings
    rings.forEach((rKm) => {
      const radiusPx = rKm * this.scale;
      ctx.beginPath();
      ctx.arc(this.centerX, this.centerY, radiusPx, 0, Math.PI * 2);
      ctx.stroke();

      // Ring distance labels
      ctx.fillText(`${rKm} KM`, this.centerX + radiusPx + 4, this.centerY - 4);
    });

    // Azimuth Crosshairs
    ctx.beginPath();
    ctx.moveTo(this.centerX - 75 * this.scale, this.centerY);
    ctx.lineTo(this.centerX + 75 * this.scale, this.centerY);
    ctx.moveTo(this.centerX, this.centerY - 75 * this.scale);
    ctx.lineTo(this.centerX, this.centerY + 75 * this.scale);
    ctx.stroke();

    // Cardinal bearings
    ctx.fillText('000° [N]', this.centerX - 18, this.centerY - 72 * this.scale);
    ctx.fillText('090° [E]', this.centerX + 72 * this.scale, this.centerY + 14);
    ctx.fillText('180° [S]', this.centerX - 18, this.centerY + 76 * this.scale);
    ctx.fillText('270° [W]', this.centerX - 78 * this.scale - 30, this.centerY + 14);

    ctx.restore();
  }

  drawCivilianCorridors() {
    const ctx = this.ctx;
    const corridors = [
      [[-60.0, -30.0], [60.0, 30.0]],
      [[-40.0, 40.0], [40.0, -40.0]],
      [[-50.0, 0.0], [50.0, 0.0]]
    ];

    ctx.save();
    ctx.setLineDash([6, 6]);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(0, 255, 136, 0.16)';

    corridors.forEach(([start, end]) => {
      const p1 = this.kmToPixel(start[0], start[1]);
      const p2 = this.kmToPixel(end[0], end[1]);
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    });

    ctx.restore();
  }

  drawRadarSweep() {
    const ctx = this.ctx;
    const maxR = 75 * this.scale;

    ctx.save();
    ctx.translate(this.centerX, this.centerY);

    // Conic gradient sweep slice
    const sweepWidth = 0.35; // radians
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, maxR, this.sweepAngle - sweepWidth, this.sweepAngle);
    ctx.closePath();

    const sweepGrad = ctx.createRadialGradient(0, 0, 5, 0, 0, maxR);
    sweepGrad.addColorStop(0, 'rgba(0, 240, 255, 0.02)');
    sweepGrad.addColorStop(0.8, 'rgba(0, 240, 255, 0.08)');
    sweepGrad.addColorStop(1, 'rgba(0, 240, 255, 0.15)');

    ctx.fillStyle = sweepGrad;
    ctx.fill();

    // Leading edge line
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(Math.cos(this.sweepAngle) * maxR, Math.sin(this.sweepAngle) * maxR);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.45)';
    ctx.stroke();

    ctx.restore();
  }

  drawDefenseAssets() {
    const ctx = this.ctx;
    const assets = this.latestState.assets || [];

    assets.forEach((asset) => {
      const p = this.kmToPixel(asset.x, asset.y);

      ctx.save();

      // Range bubble
      ctx.beginPath();
      ctx.arc(p.x, p.y, asset.effective_range_km * this.scale, 0, Math.PI * 2);
      ctx.lineWidth = 1;
      ctx.strokeStyle = asset.status === 'ENGAGED' ? 'rgba(192, 64, 255, 0.25)' : 'rgba(0, 255, 136, 0.08)';
      ctx.setLineDash([4, 4]);
      ctx.stroke();

      // Asset Icon Base
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.fillStyle = asset.status === 'ENGAGED' ? '#c040ff' : '#00ff88';
      ctx.fill();

      // Outer ring
      ctx.beginPath();
      ctx.arc(p.x, p.y, 10, 0, Math.PI * 2);
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = asset.status === 'ENGAGED' ? '#c040ff' : 'rgba(0, 255, 136, 0.6)';
      ctx.stroke();

      // Name label
      ctx.fillStyle = '#8ba3c7';
      ctx.font = '9px "JetBrains Mono"';
      ctx.fillText(asset.name.split(' ')[0], p.x + 12, p.y + 3);

      ctx.restore();
    });
  }

  drawKillWebBeams() {
    const ctx = this.ctx;
    const allocations = this.latestState.allocations || [];
    const assets = this.latestState.assets || [];
    const tracks = this.latestState.tracks || [];

    const now = Date.now() / 1000;

    allocations.forEach((alloc) => {
      const asset = assets.find((a) => a.asset_id === alloc.asset_id);
      const track = tracks.find((t) => t.track_id === alloc.track_id);

      if (!asset || !track) return;

      const pAsset = this.kmToPixel(asset.x, asset.y);
      const pTrack = this.kmToPixel(track.x, track.y);

      ctx.save();

      // Glow effect
      ctx.shadowBlur = 12;

      if (alloc.asset_type === 'CYBER_PAYLOAD') {
        // High-frequency cyber packet wave
        ctx.strokeStyle = '#00f0ff';
        ctx.shadowColor = '#00f0ff';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.lineDashOffset = -now * 30;
      } else if (alloc.asset_type === 'EW_JAMMER') {
        // High-power jamming cone / wave
        ctx.strokeStyle = '#c040ff';
        ctx.shadowColor = '#c040ff';
        ctx.lineWidth = 2.5;
        ctx.setLineDash([8, 4]);
        ctx.lineDashOffset = -now * 40;
      } else if (alloc.asset_type === 'LASER_DEW') {
        // Continuous high-energy laser beam
        ctx.strokeStyle = '#38bdf8';
        ctx.shadowColor = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.setLineDash([]);
      } else {
        // Drone or SAM intercept vector
        ctx.strokeStyle = '#ffb700';
        ctx.shadowColor = '#ffb700';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 6]);
      }

      ctx.beginPath();
      ctx.moveTo(pAsset.x, pAsset.y);
      ctx.lineTo(pTrack.x, pTrack.y);
      ctx.stroke();

      // Pulse at target impact point
      ctx.beginPath();
      ctx.arc(pTrack.x, pTrack.y, 14 + Math.sin(now * 10) * 4, 0, Math.PI * 2);
      ctx.strokeStyle = ctx.strokeStyle;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.restore();
    });
  }

  drawTargets() {
    const ctx = this.ctx;
    const tracks = this.latestState.tracks || [];
    const assessments = this.latestState.assessments || {};
    const meta = this.latestState.targets_meta || {};

    tracks.forEach((track) => {
      const p = this.kmToPixel(track.x, track.y);
      const assess = assessments[track.track_id] || { threat_level: 'ROUTINE', anomaly_score: 0.1 };
      const m = meta[track.track_id] || { neutralize_progress: 0, is_launch_prep: false };

      ctx.save();

      let color = '#00f0ff';
      if (assess.threat_level === 'CRITICAL') color = '#ff003c';
      else if (assess.threat_level === 'HOSTILE') color = '#ff3366';
      else if (assess.threat_level === 'SUSPICIOUS') color = '#ffb700';

      // Velocity vector line
      const headingRad = ((track.heading_deg - 90) * Math.PI) / 180;
      const vLen = Math.min(30, (track.velocity_mps / 1000) * 20 * this.scale);
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x + Math.cos(headingRad) * vLen, p.y + Math.sin(headingRad) * vLen);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Target shape
      ctx.fillStyle = color;
      ctx.strokeStyle = color;

      if (assess.threat_level === 'CRITICAL' || assess.threat_level === 'HOSTILE') {
        // Hostile pulsing diamond / box
        const pulse = Math.sin(Date.now() / 150) * 2;
        ctx.beginPath();
        ctx.rect(p.x - 6 - pulse, p.y - 6 - pulse, 12 + (pulse * 2), 12 + (pulse * 2));
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        // Routine diamond
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fill();
      }

      // Preemptive Neutralization Progress Ring
      if (m.neutralize_progress > 0) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 14, -Math.PI / 2, (-Math.PI / 2) + (m.neutralize_progress * Math.PI * 2));
        ctx.strokeStyle = '#00ff88';
        ctx.lineWidth = 3;
        ctx.stroke();
      }

      // Callsign tag & Anomaly Score
      ctx.font = '10px "JetBrains Mono"';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(track.callsign, p.x + 10, p.y - 4);

      ctx.font = '9px "JetBrains Mono"';
      ctx.fillStyle = color;
      ctx.fillText(`ANOM:${assess.anomaly_score.toFixed(2)} [${assess.threat_level}]`, p.x + 10, p.y + 8);

      // Selected ring
      if (this.selectedTrackId === track.track_id) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 18, 0, Math.PI * 2);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.stroke();
      }

      ctx.restore();
    });
  }
}

window.TacticalCanvas = TacticalCanvas;
