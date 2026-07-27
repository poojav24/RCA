/* =========================================================
   NZCC — Dashboard
   ========================================================= */

async function renderDashboard() {
  const view = document.getElementById('view-dashboard');
  if (!view) return;

  const d = STATE.dashboard;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Executive Overview</h1>
        <p class="muted">Real-time visibility into alerts, investigations, and AI root cause analysis</p>
      </div>
      <div class="action-buttons">
        <button id="refresh-dashboard" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
      </div>
    </div>

    <div id="kpi-grid" class="kpi-grid"></div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header">
          <div><h3>Alert Trend</h3><span class="muted">Operational load</span></div>
          <button class="btn-icon small" type="button" onclick="openChartModal('trend-chart')" title="Expand"><i class="fas fa-expand"></i></button>
        </div>
        <div id="trend-chart" class="chart-container"></div>
      </div>
      <div class="card">
        <div class="card-header"><div><h3>Severity Distribution</h3><span class="muted">Current workload</span></div></div>
        <div id="severity-chart"></div>
      </div>
    </div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><div><h3>Technology Distribution</h3><span class="muted">Active platforms</span></div></div>
        <div id="technology-chart"></div>
      </div>
      <div class="card">
        <div class="card-header"><div><h3>Incident Status</h3><span class="muted">Operational pulse</span></div></div>
        <div id="pulse-list" class="pulse-list"></div>
      </div>
    </div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><div><h3>Top Affected Hosts</h3><span class="muted">From knowledge repository</span></div></div>
        <div id="top-hosts"></div>
      </div>
      <div class="card">
        <div class="card-header"><div><h3>Latest Investigations</h3><span class="muted">Select to open RCA</span></div></div>
        <div id="latest-investigations" class="activity-list"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><div><h3>Recent Activity Timeline</h3><span class="muted">Investigation events</span></div></div>
      <div id="activity-timeline" class="timeline-container"></div>
    </div>

    <div class="card">
      <div class="card-header"><div><h3>Platform Connectivity</h3><span class="muted">Backend integration status</span></div></div>
      <div id="backend-health" class="health-grid"></div>
    </div>
  `;

  const kpi = document.getElementById('kpi-grid');
  if (!d || isUnavailable(d)) {
    kpi.innerHTML = showSkeletonGrid(5) + showPlaceholder('Waiting for Backend', 'Dashboard metrics will appear once the investigation engine publishes summary data.');
  } else {
    kpi.innerHTML = [
      UI.createKpiCard(d.todayAlerts ?? STATE.alerts.length, "Today's Alerts", 'Ingested investigations', ''),
      UI.createKpiCard(d.openIncidents ?? STATE.alerts.length, 'Open Alerts', 'Active workload', 'warning'),
      UI.createKpiCard(d.resolvedIncidents ?? 0, 'Resolved Alerts', 'Closed investigations', 'success'),
      UI.createKpiCard(d.criticalAlerts ?? 0, 'Critical Alerts', 'Priority attention', 'critical'),
      UI.createKpiCard(d.avgRcaTime || '—', 'Average RCA Time', 'Investigation speed', 'info'),
      UI.createKpiCard(d.connectedHosts ?? 0, 'Connected Hosts', 'Monitored estate', ''),
      UI.createKpiCard(d.knowledgeSize ?? STATE.knowledge.length, 'Knowledge Entries', 'Incident intelligence', ''),
      UI.createKpiCard(`${d.historicalReuse ?? 0}%`, 'Historical RCA Reuse', 'Learning efficiency', 'success'),
      UI.createKpiCard(d.connectedTechnologies ?? 0, 'Active Technologies', 'Coverage domains', ''),
      UI.createKpiCard(d.backendStatus || STATE.systemStatus?.status || 'Operational', 'Backend Status', 'Platform health', 'success')
    ].join('');

    UI.renderChart('trend-chart', 'trend', d.alertTrend || []);
    UI.renderChart('severity-chart', 'donut', d.severityDistribution || []);
    UI.renderChart('technology-chart', 'bar', d.technologyDistribution || []);

    document.getElementById('pulse-list').innerHTML = [
      { label: 'System Health', value: `${d.systemHealth ?? '—'}%` },
      { label: 'Knowledge Growth', value: d.knowledgeGrowth || '—' },
      { label: 'Open Workload', value: d.openIncidents ?? STATE.alerts.length },
      { label: 'Engine Status', value: d.backendStatus || 'Operational' }
    ].map((item) => `
      <div class="pulse-item"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(String(item.value))}</strong></div>
    `).join('');
  }

  // Top hosts from real knowledge
  const hostCounts = {};
  STATE.knowledge.forEach((k) => {
    if (!k.host) return;
    hostCounts[k.host] = (hostCounts[k.host] || 0) + 1;
  });
  const ranked = Object.entries(hostCounts).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const maxHost = ranked[0]?.[1] || 1;
  const topHosts = document.getElementById('top-hosts');
  if (!ranked.length) {
    topHosts.innerHTML = showEmpty('Host impact ranking will appear as investigations are stored.', 'No Host Data Yet', 'fa-server');
  } else {
    topHosts.innerHTML = `<div class="host-rank">${ranked.map(([host, count]) => `
      <div class="host-rank-item">
        <span class="host-rank-name">${escapeHtml(host)}</span>
        <div class="host-rank-bar"><div class="host-rank-fill" style="width:${Math.round((count / maxHost) * 100)}%"></div></div>
        <span class="host-rank-count">${count}</span>
      </div>`).join('')}</div>`;
  }

  const latest = document.getElementById('latest-investigations');
  if (!hasData(STATE.alerts)) {
    latest.innerHTML = showEmpty('New investigations will appear here as alerts are processed.', 'No Investigations Yet', 'fa-microscope');
  } else {
    latest.innerHTML = STATE.alerts.slice(0, 6).map((a) => UI.createActivityItem(a)).join('');
    latest.querySelectorAll('.activity-item').forEach((el) => {
      el.addEventListener('click', () => selectAlert(el.dataset.id, { view: 'rca' }));
    });
  }

  const timeline = document.getElementById('activity-timeline');
  if (!hasData(STATE.alerts)) {
    timeline.innerHTML = showEmpty('Activity timeline populates as the AI Investigation Engine processes alerts.', 'Awaiting Activity', 'fa-clock');
  } else {
    timeline.innerHTML = STATE.alerts.slice(0, 8).map((a, i) =>
      UI.createTimelineEntry(
        `${a.problem || 'Alert'} on ${a.host || 'host'}`,
        a.createdAt,
        i === 0 ? 'active' : 'completed'
      )
    ).join('');
  }

  const connected = STATE.connected;
  document.getElementById('backend-health').innerHTML = [
    { name: 'Alert Ingestion', ok: connected },
    { name: 'ITSM Correlation', ok: connected },
    { name: 'Log Intelligence', ok: connected },
    { name: 'Knowledge Repository', ok: connected },
    { name: 'AI Investigation Engine', ok: connected },
    { name: 'Historical Incident Intelligence', ok: connected }
  ].map((x) => UI.createHealthIndicator(x.name, x.ok)).join('');

  bindRefreshButtons();
}

window.renderDashboard = renderDashboard;
