let tacticalCanvas = null;
let currentTrackId = null;
let isAutonomous = true;
let socket = null;
let prevNeutralizedCount = 0;

document.addEventListener('DOMContentLoaded', () => {
  tacticalCanvas = new TacticalCanvas('tacticalCanvas');
  window.onTrackSelected = (trackId) => {
    currentTrackId = trackId;
    updateTrackInspector();
  };

  setupEventListeners();
  connectWebSocket();
});

function setupEventListeners() {
  // Scenario selector buttons
  const scenarioBtns = document.querySelectorAll('.scenario-btn');
  scenarioBtns.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const scenario = btn.dataset.scenario;
      scenarioBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      try {
        await fetch('/api/scenario', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario })
        });
        window.tacticalAudio.playRadarChirp();
      } catch (err) {
        console.error('Error setting scenario:', err);
      }
    });
  });

  // Autonomous Mode Toggle
  const modeBtn = document.getElementById('modeToggleBtn');
  modeBtn.addEventListener('click', async () => {
    isAutonomous = !isAutonomous;
    updateModeUI();
    try {
      await fetch('/api/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ autonomous: isAutonomous })
      });
    } catch (err) {
      console.error('Error toggling mode:', err);
    }
  });

  // Audio mute button
  const audioBtn = document.getElementById('audioToggleBtn');
  audioBtn.addEventListener('click', () => {
    const isMuted = window.tacticalAudio.toggleMute();
    audioBtn.textContent = isMuted ? '🔇 AUDIO: OFF' : '🔊 AUDIO: ON';
    audioBtn.style.color = isMuted ? '#4e6587' : '#00f0ff';
  });
}

function updateModeUI() {
  const modeBtn = document.getElementById('modeToggleBtn');
  if (isAutonomous) {
    modeBtn.className = 'mode-toggle-btn';
    modeBtn.innerHTML = '⚡ MODE: AUTONOMOUS PREEMPTIVE';
  } else {
    modeBtn.className = 'mode-toggle-btn manual';
    modeBtn.innerHTML = '🛡️ MODE: HUMAN-IN-THE-LOOP (MANUAL AUTH)';
  }
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/stream`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log('[WebSocket] Connected to tactical stream');
    document.getElementById('streamStatus').textContent = 'CONNECTED';
    document.getElementById('streamStatus').style.color = 'var(--accent-emerald)';
  };

  socket.onmessage = (event) => {
    try {
      const state = JSON.parse(event.data);
      tacticalCanvas.updateState(state);
      renderUI(state);
    } catch (err) {
      console.error('Failed to parse state:', err);
    }
  };

  socket.onclose = () => {
    console.warn('[WebSocket] Connection closed. Reconnecting in 1.5s...');
    document.getElementById('streamStatus').textContent = 'RECONNECTING';
    document.getElementById('streamStatus').style.color = 'var(--accent-amber)';
    setTimeout(connectWebSocket, 1500);
  };
}

function renderUI(state) {
  const { metrics, tracks, assessments, assets, allocations, targets_meta } = state;

  // Sound triggers
  if (metrics.anomalies_detected > 0) {
    const hasHostile = tracks.some((t) => {
      const a = assessments[t.track_id];
      return a && (a.threat_level === 'HOSTILE' || a.threat_level === 'CRITICAL');
    });
    if (hasHostile) {
      window.tacticalAudio.playThreatWarning();
    }
  }

  if (metrics.neutralized_count > prevNeutralizedCount) {
    window.tacticalAudio.playNeutralizePulse();
    prevNeutralizedCount = metrics.neutralized_count;
  }

  // 1. Update Metrics in Header / Ticker
  document.getElementById('metricThreats').textContent = metrics.active_threats;
  document.getElementById('metricNeutralized').textContent = metrics.neutralized_count;
  document.getElementById('metricSolverLat').textContent = `${metrics.mean_solver_latency_ms}ms`;
  document.getElementById('metricFusionLat').textContent = `${metrics.mean_fusion_latency_ms}ms`;

  // 2. Select track if none selected or current target is gone
  if (!currentTrackId || !tracks.some((t) => t.track_id === currentTrackId)) {
    // Pick the most hostile track or first track
    const hostile = tracks.find((t) => {
      const a = assessments[t.track_id];
      return a && (a.threat_level === 'CRITICAL' || a.threat_level === 'HOSTILE');
    });
    currentTrackId = hostile ? hostile.track_id : (tracks[0] ? tracks[0].track_id : null);
    tacticalCanvas.selectedTrackId = currentTrackId;
  }

  // 3. Render Track Details
  updateTrackInspector(state);

  // 4. Render Allocation Table
  renderAllocations(allocations, assessments);

  // 5. Render Defense Asset Nodes
  renderDefenseNodes(assets);
}

function updateTrackInspector(state = tacticalCanvas.latestState) {
  if (!currentTrackId) {
    document.getElementById('inspectorCallsign').textContent = 'NO ACTIVE TRACK';
    return;
  }

  const track = (state.tracks || []).find((t) => t.track_id === currentTrackId);
  const assess = (state.assessments || {})[currentTrackId];

  if (!track || !assess) return;

  // Header info
  document.getElementById('inspectorCallsign').textContent = `${track.callsign} [${track.track_id}]`;
  document.getElementById('telemetryCoords').textContent = `X:${track.x.toFixed(2)} Y:${track.y.toFixed(2)} (${track.lat.toFixed(4)}, ${track.lon.toFixed(4)})`;
  document.getElementById('telemetryVel').textContent = `${track.velocity_mps.toFixed(1)} m/s (${(track.velocity_mps * 3.6).toFixed(0)} km/h)`;
  document.getElementById('telemetryHeading').textContent = `${track.heading_deg.toFixed(1)}°`;
  document.getElementById('telemetryRcs').textContent = `${track.rcs_dbm2.toFixed(1)} dBm²`;
  document.getElementById('telemetryRf').textContent = `${track.rf_intensity_mw.toFixed(2)} mW`;
  document.getElementById('telemetryConfidence').textContent = `${(track.fused_confidence * 100).toFixed(0)}%`;

  // Anomaly Gauge
  const gaugePercent = Math.min(100, Math.round(assess.anomaly_score * 100));
  const gaugeCircle = document.getElementById('gaugeFillCircle');
  const circumference = 2 * Math.PI * 30; // r=30
  const offset = circumference - (gaugePercent / 100) * circumference;
  gaugeCircle.style.strokeDasharray = `${circumference}`;
  gaugeCircle.style.strokeDashoffset = `${offset}`;

  let gaugeColor = '#00f0ff';
  if (assess.threat_level === 'CRITICAL') gaugeColor = '#ff003c';
  else if (assess.threat_level === 'HOSTILE') gaugeColor = '#ff3366';
  else if (assess.threat_level === 'SUSPICIOUS') gaugeColor = '#ffb700';

  gaugeCircle.style.stroke = gaugeColor;
  document.getElementById('gaugeScoreText').textContent = `${(assess.anomaly_score).toFixed(2)}`;

  // Threat Stage Badge
  const stageBadge = document.getElementById('threatStageBadge');
  stageBadge.textContent = `THREAT LEVEL: ${assess.threat_level}`;
  stageBadge.className = `threat-stage-badge stage-${assess.threat_level.toLowerCase()}`;

  // Explanation
  document.getElementById('threatExplanation').textContent = assess.explanation;

  // Feature Attribution Bars
  const attrList = document.getElementById('attributionList');
  attrList.innerHTML = '';
  for (const [key, val] of Object.entries(assess.features_attributed || {})) {
    let norm = 0.5;
    if (key.includes('Off-Corridor')) norm = Math.min(1.0, val / 20.0);
    else if (key.includes('RF Power')) norm = Math.min(1.0, (val + 20) / 60.0);
    else if (key.includes('RCS')) norm = Math.min(1.0, val / 30.0);
    else if (key.includes('Velocity')) norm = Math.min(1.0, val / 80.0);

    const row = document.createElement('div');
    row.className = 'attribution-row';
    row.innerHTML = `
      <span style="color:var(--text-secondary)">${key}: <strong style="color:#fff">${val}</strong></span>
      <div class="attribution-bar-bg">
        <div class="attribution-bar-fill" style="width: ${Math.round(norm * 100)}%; background: ${gaugeColor}"></div>
      </div>
    `;
    attrList.appendChild(row);
  }
}

function renderAllocations(allocations, assessments) {
  const tbody = document.getElementById('allocationsTableBody');
  if (!allocations || allocations.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:10px;">SECTOR CLEAR - NO ACTIVE SUPPRESSION ENGAGEMENTS</td></tr>`;
    return;
  }

  tbody.innerHTML = allocations.map((alloc) => {
    let badgeClass = 'badge-cyber';
    if (alloc.asset_type === 'EW_JAMMER') badgeClass = 'badge-ew';
    else if (alloc.asset_type === 'LASER_DEW') badgeClass = 'badge-dew';
    else if (alloc.asset_type === 'COUNTER_DRONE') badgeClass = 'badge-drone';
    else if (alloc.asset_type === 'KINETIC_SAM') badgeClass = 'badge-sam';

    return `
      <tr>
        <td><strong style="color:#fff">${alloc.track_id}</strong></td>
        <td><span class="asset-badge ${badgeClass}">${alloc.asset_name.split(' ')[0]}</span></td>
        <td>${(alloc.expected_pk * 100).toFixed(0)}%</td>
        <td style="color:var(--accent-cyan)">${alloc.calculated_utility.toFixed(3)}</td>
        <td>
          ${!isAutonomous ? 
            `<button class="suppress-btn" onclick="authorizeManual('${alloc.track_id}', '${alloc.asset_id}')">AUTHORIZE</button>` :
            `<span style="color:var(--accent-emerald); font-weight:600">ENGAGED</span>`
          }
        </td>
      </tr>
    `;
  }).join('');
}

function renderDefenseNodes(assets) {
  const container = document.getElementById('defenseNodesGrid');
  if (!assets) return;

  container.innerHTML = assets.map((a) => {
    let statusClass = 'ready';
    if (a.status === 'ENGAGED') statusClass = 'engaged';
    else if (a.status === 'COOLDOWN') statusClass = 'cooldown';

    return `
      <div class="node-item">
        <div class="node-header">
          <span style="color:#fff; font-weight:600">${a.name.split(' ')[0]}</span>
          <div class="node-status ${statusClass}"></div>
        </div>
        <div style="color:var(--text-muted); font-size:9px">${a.asset_type}</div>
        <div style="display:flex; justify-content:space-between; margin-top:3px; color:var(--text-secondary)">
          <span>PK: ${(a.pk_probability * 100).toFixed(0)}%</span>
          <span>CHG: ${Math.round(a.ammo_or_charge_pct)}%</span>
        </div>
      </div>
    `;
  }).join('');
}

async function authorizeManual(trackId, assetId) {
  try {
    await fetch('/api/manual_suppress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ track_id: trackId, asset_id: assetId })
    });
    window.tacticalAudio.playNeutralizePulse();
  } catch (err) {
    console.error('Error in manual authorization:', err);
  }
}
window.authorizeManual = authorizeManual;
