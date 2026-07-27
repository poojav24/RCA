/* =========================================================
   NZCC — Metrics Explorer
   ========================================================= */

async function renderMetrics() {
  const view = document.getElementById('view-metrics');
  if (!view) return;

  const hosts = [...new Set((STATE.metrics || []).map((m) => m.host).filter(Boolean))].sort();
  const techs = [...new Set((STATE.metrics || []).map((m) => m.technology).filter(Boolean))].sort();
  const selectedHost = STATE.selectedAlert?.host || '';

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Metrics Explorer</h1>
        <p class="muted">Technology-aware performance indicators collected during investigations</p>
      </div>
      <button id="refresh-metrics" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
    </div>

    <div class="card">
      <div class="filters-grid">
        <select id="metrics-host"><option value="">All Hosts</option>${hosts.map((h) => `<option value="${escapeHtml(h)}" ${h === selectedHost ? 'selected' : ''}>${escapeHtml(h)}</option>`).join('')}</select>
        <select id="metrics-technology"><option value="">All Technologies</option>${techs.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('')}</select>
        <select id="metrics-range">
          <option value="1h">Last 1 hour</option>
          <option value="6h">Last 6 hours</option>
          <option value="24h" selected>Last 24 hours</option>
        </select>
        <input type="search" id="metrics-search" placeholder="Filter metric name…" />
      </div>
    </div>

    <div id="metrics-kpi" class="kpi-grid"></div>

    <div class="card">
      <div class="card-header"><h3>Metric Categories</h3><span class="muted">CPU · Memory · Disk · Network · Latency · Processes · Agent</span></div>
      <div id="metrics-categories" class="metrics-grid"></div>
    </div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><h3>Utilization Trend</h3></div>
        <div id="metrics-trend" class="chart-container"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Collection Status</h3></div>
        <div id="metrics-status" class="status-grid"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3>Collected Metrics</h3></div>
      <div class="table-wrapper">
        <table id="metrics-table">
          <thead>
            <tr><th>Host</th><th>Technology</th><th>Metric</th><th>Value</th><th>Unit</th><th>Status</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="metrics-empty"></div>
    </div>
  `;

  const paint = () => {
    const host = document.getElementById('metrics-host')?.value || '';
    const tech = document.getElementById('metrics-technology')?.value || '';
    const q = (document.getElementById('metrics-search')?.value || '').toLowerCase();
    let rows = STATE.metrics || [];
    if (host) rows = rows.filter((m) => m.host === host);
    if (tech) rows = rows.filter((m) => m.technology === tech);
    if (q) rows = rows.filter((m) => String(m.name || '').toLowerCase().includes(q));

    const categories = [
      { key: 'cpu', label: 'CPU', icon: 'fa-microchip' },
      { key: 'memory', label: 'Memory', icon: 'fa-memory' },
      { key: 'mem', label: 'Memory', icon: 'fa-memory' },
      { key: 'disk', label: 'Disk', icon: 'fa-hard-drive' },
      { key: 'network', label: 'Network', icon: 'fa-network-wired' },
      { key: 'latency', label: 'Latency', icon: 'fa-stopwatch' },
      { key: 'process', label: 'Processes', icon: 'fa-gears' },
      { key: 'agent', label: 'Agent Status', icon: 'fa-heartbeat' }
    ];

    const uniqueCats = [];
    const seen = new Set();
    categories.forEach((c) => {
      if (seen.has(c.label)) return;
      seen.add(c.label);
      uniqueCats.push(c);
    });

    document.getElementById('metrics-categories').innerHTML = uniqueCats.map((c) => {
      const match = rows.find((m) => String(m.name || '').toLowerCase().includes(c.key) || String(m.name || '').toLowerCase().includes(c.label.toLowerCase()));
      if (match) {
        return UI.createMetricCard(c.label, match.value, match.unit || '');
      }
      return `
        <div class="metric-gauge">
          <span class="metric-gauge-label"><i class="fas ${c.icon}"></i> ${escapeHtml(c.label)}</span>
          <span class="muted" style="font-size:12px;line-height:1.4">Metric not collected for this technology.</span>
        </div>`;
    }).join('');

    document.getElementById('metrics-kpi').innerHTML = [
      UI.createKpiCard(rows.length, 'Metrics Collected'),
      UI.createKpiCard(new Set(rows.map((m) => m.host).filter(Boolean)).size, 'Hosts'),
      UI.createKpiCard(new Set(rows.map((m) => m.technology).filter(Boolean)).size, 'Technologies'),
      UI.createKpiCard(STATE.connected ? 'Live' : 'Offline', 'Auto Refresh')
    ].join('');

    const trendData = (STATE.dashboard?.alertTrend || []).map((p, i) => ({
      label: p.label,
      value: rows[i % Math.max(rows.length, 1)] ? Number(rows[i % rows.length].value) || p.value : p.value
    }));
    UI.renderChart('metrics-trend', 'trend', hasData(rows) ? trendData : []);

    document.getElementById('metrics-status').innerHTML = [
      UI.createHealthIndicator('Metric Collection', hasData(STATE.metrics)),
      UI.createHealthIndicator('Host Selector', true),
      UI.createHealthIndicator('Auto Refresh', STATE.connected),
      UI.createHealthIndicator('Threshold Indicators', hasData(rows))
    ].join('');

    const tbody = document.querySelector('#metrics-table tbody');
    const empty = document.getElementById('metrics-empty');
    if (!hasData(rows)) {
      tbody.innerHTML = '';
      empty.innerHTML = showEmpty('Metric not collected for this technology.', 'No Metrics Available', 'fa-gauge');
      return;
    }
    empty.innerHTML = '';
    tbody.innerHTML = rows.slice(0, 100).map((m) => {
      const val = Number(m.value);
      const health = !Number.isNaN(val) && val > 90 ? 'critical' : !Number.isNaN(val) && val > 75 ? 'warning' : 'success';
      return `
        <tr>
          <td>${escapeHtml(m.host || '—')}</td>
          <td>${escapeHtml(m.technology || '—')}</td>
          <td>${escapeHtml(m.name || '—')}</td>
          <td>${escapeHtml(String(m.value ?? '—'))}</td>
          <td>${escapeHtml(m.unit || '—')}</td>
          <td>${UI.createBadge(health === 'critical' ? 'High' : health === 'warning' ? 'Elevated' : 'Normal', health === 'success' ? 'success' : health)}</td>
        </tr>`;
    }).join('');
  };

  ['metrics-host', 'metrics-technology', 'metrics-search', 'metrics-range'].forEach((id) => {
    document.getElementById(id)?.addEventListener('change', paint);
    document.getElementById(id)?.addEventListener('input', paint);
  });

  paint();
  bindRefreshButtons();
}

window.renderMetrics = renderMetrics;
