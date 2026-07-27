/* =========================================================
   NZCC — Active Alerts
   ========================================================= */

async function renderAlerts() {
  const view = document.getElementById('view-alerts');
  if (!view) return;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Active Alerts</h1>
        <p class="muted">Live alert inventory with severity, technology, and ITSM linkage</p>
      </div>
      <div class="action-buttons">
        <button id="refresh-alerts" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div><h3>Alert Workbench</h3><span class="muted" id="alerts-count-label"></span></div>
        <div class="filters-compact">
          <input type="search" id="alerts-search" placeholder="Search host, problem, technology…" />
          <select id="alerts-severity">
            <option value="">All Severities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Average">Average</option>
            <option value="Information">Information</option>
          </select>
          <select id="alerts-status">
            <option value="">All Status</option>
            <option value="Open">Open</option>
            <option value="Resolved">Resolved</option>
          </select>
          <select id="alerts-tech">
            <option value="">All Technologies</option>
          </select>
        </div>
      </div>
      <div id="alerts-table-wrap" class="table-wrapper">
        <table id="alerts-table">
          <thead>
            <tr>
              <th data-sort="severity">Severity</th>
              <th data-sort="host">Host</th>
              <th data-sort="problem">Problem</th>
              <th data-sort="technology">Technology</th>
              <th data-sort="trigger">Trigger</th>
              <th data-sort="status">Status</th>
              <th data-sort="createdAt">Created Time</th>
              <th data-sort="incidentNumber">ServiceNow Incident</th>
              <th></th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="alerts-empty"></div>
    </div>
  `;

  const techs = [...new Set(STATE.alerts.map((a) => a.technology).filter(Boolean))].sort();
  const techSel = document.getElementById('alerts-tech');
  techSel.innerHTML = '<option value="">All Technologies</option>' +
    techs.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');

  ['alerts-search', 'alerts-severity', 'alerts-status', 'alerts-tech'].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', paintAlertsTable);
    el.addEventListener('change', paintAlertsTable);
  });

  document.querySelectorAll('#alerts-table thead th[data-sort]').forEach((th) => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (STATE.sortAlerts.key === key) {
        STATE.sortAlerts.dir = STATE.sortAlerts.dir === 'asc' ? 'desc' : 'asc';
      } else {
        STATE.sortAlerts.key = key;
        STATE.sortAlerts.dir = 'asc';
      }
      paintAlertsTable();
    });
  });

  paintAlertsTable();
  bindRefreshButtons();
}

function getFilteredAlerts() {
  const search = (document.getElementById('alerts-search')?.value || '').toLowerCase();
  const severity = document.getElementById('alerts-severity')?.value || '';
  const status = document.getElementById('alerts-status')?.value || '';
  const tech = document.getElementById('alerts-tech')?.value || '';

  let rows = STATE.alerts.filter((alert) => {
    const blob = `${alert.problem || ''} ${alert.host || ''} ${alert.technology || ''} ${alert.incidentNumber || ''}`.toLowerCase();
    const matchSearch = !search || blob.includes(search);
    const matchSeverity = !severity || String(alert.severity) === severity;
    const matchStatus = !status || String(alert.status) === status;
    const matchTech = !tech || alert.technology === tech;
    return matchSearch && matchSeverity && matchStatus && matchTech;
  });

  const { key, dir } = STATE.sortAlerts || { key: 'createdAt', dir: 'desc' };
  rows = rows.slice().sort((a, b) => {
    const av = a[key] ?? '';
    const bv = b[key] ?? '';
    if (key === 'createdAt') {
      return dir === 'asc'
        ? new Date(av).getTime() - new Date(bv).getTime()
        : new Date(bv).getTime() - new Date(av).getTime();
    }
    return dir === 'asc'
      ? String(av).localeCompare(String(bv))
      : String(bv).localeCompare(String(av));
  });

  return rows;
}

function paintAlertsTable() {
  const tbody = document.querySelector('#alerts-table tbody');
  const empty = document.getElementById('alerts-empty');
  const label = document.getElementById('alerts-count-label');
  if (!tbody) return;

  if (!hasData(STATE.alerts)) {
    tbody.innerHTML = '';
    if (empty) {
      empty.innerHTML = showEmpty(
        'Alerts will appear here as the investigation engine processes new events.',
        'No Active Alerts',
        'fa-bell-slash'
      );
    }
    if (label) label.textContent = '0 alerts';
    return;
  }

  const filtered = getFilteredAlerts();
  if (label) label.textContent = `${filtered.length} of ${STATE.alerts.length} alerts`;

  if (!filtered.length) {
    tbody.innerHTML = '';
    if (empty) empty.innerHTML = showEmpty('Try adjusting search or filters.', 'No Matching Alerts', 'fa-filter');
    return;
  }

  if (empty) empty.innerHTML = '';
  tbody.innerHTML = filtered.map((alert) => {
    const selected = STATE.selectedAlert?.problemId === alert.problemId ? 'selected' : '';
    return `
      <tr class="${selected}" data-id="${escapeHtml(alert.problemId || '')}">
        <td>${UI.createBadge(alert.severity || 'Information', severityClass(alert.severity))}</td>
        <td>${escapeHtml(alert.host || '—')}</td>
        <td>${escapeHtml(alert.problem || '—')}</td>
        <td>${escapeHtml(alert.technology || '—')}</td>
        <td>${escapeHtml(alert.trigger || '—')}</td>
        <td>${UI.createBadge(alert.status || 'Open', 'info')}</td>
        <td>${escapeHtml(formatTime(alert.createdAt))}</td>
        <td>${escapeHtml(alert.incidentNumber || '—')}</td>
        <td><button class="btn-primary" style="padding:6px 10px;font-size:11px" type="button" data-open-rca="${escapeHtml(alert.problemId || '')}">Open RCA</button></td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('tr').forEach((tr) => {
    tr.addEventListener('click', (e) => {
      if (e.target.closest('button')) return;
      selectAlert(tr.dataset.id, { view: 'rca' });
    });
  });
  tbody.querySelectorAll('[data-open-rca]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      selectAlert(btn.getAttribute('data-open-rca'), { view: 'rca' });
    });
  });
}

window.renderAlerts = renderAlerts;
window.paintAlertsTable = paintAlertsTable;
