/* =========================================================
   NZCC — Logs Explorer
   ========================================================= */

async function renderLogs() {
  const view = document.getElementById('view-logs');
  if (!view) return;

  const hosts = [...new Set((STATE.logs || []).map((l) => l.host).filter(Boolean))].sort();
  const techs = [...new Set((STATE.knowledge || []).map((k) => k.technology).filter(Boolean))].sort();
  const selectedHost = STATE.selectedAlert?.host || '';

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Logs Explorer</h1>
        <p class="muted">Investigation log intelligence with search and severity highlighting</p>
      </div>
      <button id="refresh-logs" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
    </div>

    <div class="card">
      <div class="filters-grid">
        <select id="logs-host"><option value="">All Hosts</option>${hosts.map((h) => `<option value="${escapeHtml(h)}" ${h === selectedHost ? 'selected' : ''}>${escapeHtml(h)}</option>`).join('')}</select>
        <select id="logs-tech"><option value="">All Technologies</option>${techs.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('')}</select>
        <select id="logs-severity">
          <option value="">All Severities</option>
          <option value="ERROR">Errors</option>
          <option value="WARN">Warnings</option>
          <option value="INFO">Info</option>
        </select>
        <select id="logs-timerange">
          <option value="1h">Last 1h</option>
          <option value="6h">Last 6h</option>
          <option value="24h" selected>Last 24h</option>
        </select>
        <input type="search" id="logs-search" placeholder="Search keywords…" />
      </div>
    </div>

    <div id="logs-stats" class="kpi-grid"></div>

    <div class="card">
      <div class="card-header">
        <div><h3>Live Log Viewer</h3><span class="muted">Keyword highlighting enabled</span></div>
        <span class="status-pill live">Streaming view</span>
      </div>
      <div id="logs-list" class="logs-list"></div>
      <div id="logs-empty"></div>
    </div>
  `;

  const highlight = (text, query) => {
    const safe = escapeHtml(text);
    if (!query) return safe;
    try {
      const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig');
      return safe.replace(re, '<span class="hl">$1</span>');
    } catch {
      return safe;
    }
  };

  const paint = () => {
    const host = document.getElementById('logs-host')?.value || '';
    const severity = document.getElementById('logs-severity')?.value || '';
    const q = (document.getElementById('logs-search')?.value || '').trim();
    let rows = STATE.logs || [];

    const unavailable = rows.length === 1 && /not currently available|unavailable/i.test(String(rows[0]?.message || ''));

    if (host) rows = rows.filter((l) => l.host === host);
    if (severity) {
      rows = rows.filter((l) => String(l.message || '').toUpperCase().includes(severity));
    }
    if (q) {
      rows = rows.filter((l) => String(l.message || '').toLowerCase().includes(q.toLowerCase()));
    }

    const errors = rows.filter((l) => /error/i.test(String(l.message || ''))).length;
    const warns = rows.filter((l) => /warn/i.test(String(l.message || ''))).length;

    document.getElementById('logs-stats').innerHTML = [
      UI.createKpiCard(unavailable ? 0 : rows.length, 'Log Entries'),
      UI.createKpiCard(errors, 'Errors', '', 'critical'),
      UI.createKpiCard(warns, 'Warnings', '', 'warning'),
      UI.createKpiCard(new Set(rows.map((l) => l.host).filter(Boolean)).size, 'Sources')
    ].join('');

    const list = document.getElementById('logs-list');
    const empty = document.getElementById('logs-empty');

    if (!hasData(STATE.logs) || unavailable || !rows.length) {
      list.innerHTML = '';
      empty.innerHTML = showEmpty(
        'Logs are not currently available for this host. Investigation continues using metrics and historical intelligence.',
        'Logs Unavailable',
        'fa-terminal'
      );
      return;
    }

    empty.innerHTML = '';
    list.innerHTML = rows.slice(0, 80).map((log) => {
      const msg = String(log.message || '');
      const cls = /error/i.test(msg) ? 'error' : /warn/i.test(msg) ? 'warning' : 'info';
      return `
        <div class="log-entry ${cls}">
          <div class="muted" style="font-size:10px">${formatTime(log.timestamp)} · ${escapeHtml(log.host || 'unknown')}</div>
          <div>${highlight(msg, q)}</div>
        </div>`;
    }).join('');
  };

  ['logs-host', 'logs-tech', 'logs-severity', 'logs-timerange', 'logs-search'].forEach((id) => {
    document.getElementById(id)?.addEventListener('change', paint);
    document.getElementById(id)?.addEventListener('input', paint);
  });

  paint();
  bindRefreshButtons();
}

window.renderLogs = renderLogs;
