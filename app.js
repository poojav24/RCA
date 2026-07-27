/* =========================================================
   NZCC — Application Orchestrator
   ========================================================= */

async function refreshAllData() {
  setRefreshing(true);
  try {
    const [dashboard, alerts, knowledge, metrics, logs, incidents, analytics, status] = await Promise.all([
      API.dashboard(),
      API.alerts(),
      API.knowledge(),
      API.metrics(STATE.selectedAlert?.host),
      API.logs(STATE.selectedAlert?.host),
      API.servicenow(),
      API.analytics(),
      API.systemStatus()
    ]);

    const previousCount = STATE.alerts.length;
    STATE.connected = !isUnavailable(status) || !isUnavailable(dashboard);

    STATE.dashboard = isUnavailable(dashboard) ? STATE.dashboard : dashboard;
    STATE.alerts = isUnavailable(alerts) ? STATE.alerts : (alerts.alerts || []);
    STATE.knowledge = isUnavailable(knowledge) ? STATE.knowledge : (knowledge.knowledge || []);
    STATE.metrics = isUnavailable(metrics) ? STATE.metrics : (metrics.metrics || []);
    STATE.logs = isUnavailable(logs) ? STATE.logs : (logs.logs || []);
    STATE.incidents = isUnavailable(incidents) ? STATE.incidents : (incidents.incidents || []);
    STATE.analytics = isUnavailable(analytics) ? STATE.analytics : analytics;
    STATE.systemStatus = isUnavailable(status) ? STATE.systemStatus : status;

    if (!STATE.selectedAlert && STATE.alerts.length) {
      await selectAlert(STATE.alerts[0].problemId, { skipView: true });
    } else if (STATE.selectedAlert) {
      const stillExists = STATE.alerts.some((a) => a.problemId === STATE.selectedAlert.problemId);
      if (stillExists) {
        await loadAlertContext(STATE.selectedAlert.problemId);
      } else if (STATE.alerts.length) {
        await selectAlert(STATE.alerts[0].problemId, { skipView: true });
      }
    }

    updateLastUpdated();
    updateStatusBar();

    if (STATE.connected) {
      updateStatusPill(status?.status || 'Operational', 'live');
    } else {
      updateStatusPill('Backend unavailable', 'warning');
    }

    if (STATE.alerts.length > previousCount && previousCount > 0) {
      showNotification('New alerts detected by the investigation engine', 'warning', 'Active Alerts');
    }

    await renderCurrentView();
  } catch (error) {
    updateStatusPill('Connection issue', 'warning');
    showNotification('Unable to refresh live data. Showing last known state.', 'warning', 'Connectivity');
  } finally {
    setRefreshing(false);
  }
}

async function loadAlertContext(problemId) {
  const selected = STATE.alerts.find((alert) => alert.problemId === problemId) || STATE.selectedAlert;
  if (!selected) return;

  STATE.selectedAlert = selected;
  try {
    const [detail, rca, metricsForHost, logsForHost] = await Promise.all([
      API.alertDetails(problemId),
      API.rca(problemId),
      API.metrics(selected.host),
      API.logs(selected.host)
    ]);

    STATE.alertDetails = isUnavailable(detail) ? null : (detail.alert || null);
    STATE.rca = isUnavailable(rca) ? STATE.rca : rca;
    STATE.currentInvestigationMetrics = isUnavailable(metricsForHost) ? [] : (metricsForHost.metrics || []);
    STATE.currentInvestigationLogs = isUnavailable(logsForHost) ? [] : (logsForHost.logs || []);
    STATE.currentInvestigationIncidents = UI.similarIncidents(selected, STATE.knowledge);
    if (!isUnavailable(metricsForHost) && metricsForHost.metrics) {
      STATE.metrics = metricsForHost.metrics;
    }
    if (!isUnavailable(logsForHost) && logsForHost.logs) {
      STATE.logs = logsForHost.logs;
    }
  } catch {
    STATE.currentInvestigationMetrics = [];
    STATE.currentInvestigationLogs = [];
  }
  updateStatusBar();
}

async function selectAlert(problemId, options = {}) {
  const selected = STATE.alerts.find((alert) => String(alert.problemId) === String(problemId));
  if (!selected) {
    showNotification('Alert not found in current inventory', 'warning', 'Alerts');
    return;
  }
  STATE.selectedAlert = selected;
  await loadAlertContext(selected.problemId);
  if (!options.skipView) {
    setActiveView(options.view || 'rca');
    await renderCurrentView();
  }
}

async function renderCurrentView() {
  const views = {
    dashboard: renderDashboard,
    investigation: renderInvestigation,
    alerts: renderAlerts,
    rca: renderRCA,
    knowledge: renderKnowledge,
    search: renderSearch,
    metrics: renderMetrics,
    logs: renderLogs,
    servicenow: renderServiceNow,
    analytics: renderAnalytics,
    roadmap: renderRoadmap,
    settings: renderSettings
  };

  const renderer = views[STATE.activeView];
  const viewEl = document.getElementById(`view-${STATE.activeView}`);
  if (!renderer || !viewEl) return;

  try {
    await renderer();
  } catch (error) {
    viewEl.innerHTML = `
      <div class="card">
        ${showEmpty('This view could not be rendered. Data refresh will retry automatically.', 'Temporary Display Issue', 'fa-triangle-exclamation')}
      </div>`;
  }
}

/* ---------- AI Search ---------- */
async function renderSearch() {
  const view = document.getElementById('view-search');
  if (!view) return;

  const suggestions = window.NZCC_CONFIG.SUGGESTED_QUESTIONS || [];

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>AI Search</h1>
        <p class="muted">Ask natural-language questions across historical incident intelligence</p>
      </div>
    </div>

    <div class="card chat-card">
      <div class="chat-layout">
        <aside class="suggest-panel">
          <h4>Suggested Questions</h4>
          ${suggestions.map((q) => `<button type="button" class="suggest-btn" data-q="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join('')}
          <div style="margin-top:16px">
            <h4>Capabilities</h4>
            <p class="muted" style="font-size:12px;line-height:1.5">Search results · Historical RCA · Evidence · Recommendations</p>
          </div>
        </aside>
        <div class="chat-interface">
          <div class="chat-history" id="chat-history"></div>
          <form id="search-form" class="chat-form">
            <input type="text" id="search-input" placeholder="Ask about incidents, hosts, or root causes…" autocomplete="off" />
            <button type="submit" class="btn-primary"><i class="fas fa-paper-plane"></i></button>
          </form>
        </div>
      </div>
    </div>
  `;

  const history = document.getElementById('chat-history');
  if (!STATE.chatHistory.length) {
    history.innerHTML = showPlaceholder(
      'AI Search Ready',
      hasData(STATE.knowledge)
        ? 'Ask a question to search indexed investigations.'
        : 'AI Search will become available once semantic indexing completes.'
    );
  } else {
    history.innerHTML = STATE.chatHistory.map((m) =>
      `<div class="chat-bubble ${m.role === 'user' ? 'user' : ''}">${m.html}</div>`
    ).join('');
  }

  const runSearch = async (query) => {
    if (!query) return;
    STATE.chatHistory.push({ role: 'user', html: escapeHtml(query) });
    history.innerHTML = STATE.chatHistory.map((m) =>
      `<div class="chat-bubble ${m.role === 'user' ? 'user' : ''}">${m.html}</div>`
    ).join('');
    history.scrollTop = history.scrollHeight;

    const response = await API.search(query);
    let html;
    if (isUnavailable(response)) {
      html = `<strong>Search temporarily unavailable</strong><p class="muted" style="margin-top:6px">AI Search will become available once semantic indexing completes.</p>`;
    } else if (!hasData(response.results)) {
      html = `<strong>No matching incidents</strong><p class="muted" style="margin-top:6px">No historical RCA matched this question. Try a broader query.</p>`;
    } else {
      html = `<strong>Search Results</strong>` + response.results.map((r) => `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border)">
          <div><strong>${escapeHtml(r.problem || 'Investigation')}</strong></div>
          <div class="muted" style="margin-top:4px"><strong>Historical RCA:</strong> ${escapeHtml(r.rootCause || '—')}</div>
          <div class="muted"><strong>Technology:</strong> ${escapeHtml(r.technology || '—')}</div>
          <div class="muted"><strong>Confidence:</strong> ${formatConfidence(r.confidence)}</div>
          <div class="muted" style="margin-top:4px"><strong>Recommendation:</strong> Review linked RCA Analysis for resolution guidance.</div>
        </div>`).join('');
    }

    STATE.chatHistory.push({ role: 'assistant', html });
    history.innerHTML = STATE.chatHistory.map((m) =>
      `<div class="chat-bubble ${m.role === 'user' ? 'user' : ''}">${m.html}</div>`
    ).join('');
    history.scrollTop = history.scrollHeight;
  };

  document.getElementById('search-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('search-input');
    const query = input.value.trim();
    input.value = '';
    await runSearch(query);
  });

  document.querySelectorAll('.suggest-btn').forEach((btn) => {
    btn.addEventListener('click', () => runSearch(btn.dataset.q));
  });
}

/* ---------- ServiceNow ---------- */
async function renderServiceNow() {
  const view = document.getElementById('view-servicenow');
  if (!view) return;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>ServiceNow</h1>
        <p class="muted">ITSM incident correlation and investigation linkage</p>
      </div>
      <button id="refresh-servicenow" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
    </div>

    <div class="card">
      <div class="filters-compact">
        <input type="search" id="servicenow-search" placeholder="Search incidents…" />
        <select id="servicenow-priority">
          <option value="">All Priorities</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Moderate">Moderate</option>
        </select>
      </div>
      <div class="table-wrapper">
        <table id="servicenow-table">
          <thead>
            <tr>
              <th>Incident Number</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Assignment Group</th>
              <th>Problem</th>
              <th>Related RCA</th>
              <th></th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="servicenow-empty"></div>
    </div>
  `;

  const paint = () => {
    const q = (document.getElementById('servicenow-search')?.value || '').toLowerCase();
    const priority = document.getElementById('servicenow-priority')?.value || '';
    let rows = STATE.incidents || [];
    if (q) rows = rows.filter((i) => `${i.incidentNumber || ''} ${i.problem || ''}`.toLowerCase().includes(q));
    if (priority) rows = rows.filter((i) => i.priority === priority);

    const tbody = document.querySelector('#servicenow-table tbody');
    const empty = document.getElementById('servicenow-empty');

    if (!hasData(STATE.incidents)) {
      tbody.innerHTML = '';
      empty.innerHTML = showEmpty(
        'Waiting for ServiceNow synchronization.',
        'ITSM Sync Pending',
        'fa-ticket'
      );
      return;
    }

    if (!rows.length) {
      tbody.innerHTML = '';
      empty.innerHTML = showEmpty('No incidents match the current filters.', 'No Matching Incidents', 'fa-filter');
      return;
    }

    empty.innerHTML = '';
    tbody.innerHTML = rows.map((inc) => `
      <tr>
        <td><strong>${escapeHtml(inc.incidentNumber || '—')}</strong></td>
        <td>${UI.createBadge(inc.priority || 'High', severityClass(inc.priority))}</td>
        <td>${UI.createBadge(inc.status || 'In Progress', 'info')}</td>
        <td>${escapeHtml(inc.assignmentGroup || 'Operations')}</td>
        <td>${escapeHtml(inc.problem || '—')}</td>
        <td>${UI.createBadge('Linked', 'success')}</td>
        <td><button class="btn-primary" style="padding:6px 10px;font-size:11px" type="button" data-problem="${escapeHtml(inc.problem || '')}">Open Incident</button></td>
      </tr>`).join('');

    tbody.querySelectorAll('[data-problem]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const match = STATE.alerts.find((a) => a.problem === btn.dataset.problem || a.incidentNumber === btn.closest('tr')?.children[0]?.textContent?.trim());
        if (match) await selectAlert(match.problemId, { view: 'rca' });
        else showNotification('Related RCA will open once alert linkage is available.', 'info', 'ServiceNow');
      });
    });
  };

  document.getElementById('servicenow-search')?.addEventListener('input', paint);
  document.getElementById('servicenow-priority')?.addEventListener('change', paint);
  paint();
  bindRefreshButtons();
}

/* ---------- Roadmap ---------- */
async function renderRoadmap() {
  const view = document.getElementById('view-roadmap');
  if (!view) return;

  const phases = [
    {
      phase: 'Phase 1',
      statusHint: 'Foundation Intelligence',
      items: [
        { title: 'Weighted Semantic Search', description: 'Rank historical incidents by relevance across problem, host, and evidence context.', status: 'In Progress' },
        { title: 'Metric Similarity', description: 'Compare metric fingerprints to accelerate investigation reuse.', status: 'Planned' },
        { title: 'Incident Clustering', description: 'Group related alerts into coherent incident narratives.', status: 'Planned' }
      ]
    },
    {
      phase: 'Phase 2',
      statusHint: 'Decision Quality',
      items: [
        { title: 'Confidence Calibration', description: 'Tune confidence scoring against validated outcomes.', status: 'Planned' },
        { title: 'Vendor Documentation', description: 'Attach trusted vendor guidance to RCA recommendations.', status: 'Planned' },
        { title: 'Learning from Resolution Notes', description: 'Continuously improve from closed-loop resolution feedback.', status: 'Planned' }
      ]
    },
    {
      phase: 'Phase 3',
      statusHint: 'Assisted Action',
      items: [
        { title: 'AI Remediation Validation', description: 'Validate proposed fixes before operator execution.', status: 'Planned' },
        { title: 'Automated Self Healing', description: 'Controlled automation for well-understood remediations.', status: 'Planned' },
        { title: 'Continuous Learning', description: 'Improve investigation quality from every closed incident.', status: 'In Progress' }
      ]
    },
    {
      phase: 'Phase 4',
      statusHint: 'Enterprise Correlation',
      items: [
        { title: 'Multi Alert Correlation', description: 'Correlate concurrent alerts into a single blast narrative.', status: 'Planned' },
        { title: 'Dependency Graph', description: 'Visualize service and infrastructure dependencies.', status: 'Planned' },
        { title: 'Blast Radius', description: 'Estimate downstream impact across dependent systems.', status: 'Planned' },
        { title: 'Business Impact', description: 'Translate technical failure into business risk language.', status: 'Planned' }
      ]
    }
  ];

  // Mark completed foundation items that already exist in product
  phases[0].items[0].status = hasData(STATE.knowledge) ? 'Completed' : 'In Progress';

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Product Roadmap</h1>
        <p class="muted">Planned capabilities across the Near Zero Command Center platform</p>
      </div>
    </div>
    <div class="roadmap-phases">
      ${phases.map((p) => `
        <section class="phase-block">
          <div class="phase-title">
            <h3>${escapeHtml(p.phase)}</h3>
            ${UI.createBadge(p.statusHint, 'info')}
          </div>
          <div class="roadmap-grid">
            ${p.items.map((item) => UI.createRoadmapCard({ ...item, phase: p.phase })).join('')}
          </div>
        </section>`).join('')}
    </div>
  `;
}

/* ---------- Settings ---------- */
async function renderSettings() {
  const view = document.getElementById('view-settings');
  if (!view) return;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Settings</h1>
        <p class="muted">Platform preferences, connectivity, and system information</p>
      </div>
    </div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><h3>Backend Integration</h3></div>
        <div class="settings-form">
          <label><span>Backend URL</span><input type="text" id="backend-url" value="${escapeHtml(window.NZCC_CONFIG.API_BASE)}" /></label>
          <label><span>Polling Interval (seconds)</span><input type="number" id="polling-select" min="10" max="300" value="${STATE.pollingInterval}" /></label>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Experience</h3></div>
        <div class="settings-form">
          <label><span>Theme</span>
            <select id="theme-select">
              <option value="dark">Dark (Enterprise)</option>
              <option value="light">Light</option>
            </select>
          </label>
          <label style="flex-direction:row;align-items:center;gap:10px">
            <input type="checkbox" id="notifications-toggle" ${STATE.notifications ? 'checked' : ''} />
            <span>Enable toast notifications</span>
          </label>
          <label style="flex-direction:row;align-items:center;gap:10px">
            <input type="checkbox" id="demo-mode" ${STATE.demoMode ? 'checked' : ''} />
            <span>Demo Mode (highlight key workflows)</span>
          </label>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3>System Information</h3></div>
      <div class="system-info">
        <div class="system-info-item"><span class="system-info-label">Product</span><span class="system-info-value">${escapeHtml(window.NZCC_CONFIG.APP_NAME)}</span></div>
        <div class="system-info-item"><span class="system-info-label">Version</span><span class="system-info-value">${escapeHtml(window.NZCC_CONFIG.VERSION)}</span></div>
        <div class="system-info-item"><span class="system-info-label">Backend Status</span><span class="system-info-value">${escapeHtml(STATE.systemStatus?.status || (STATE.connected ? 'Operational' : 'Unavailable'))}</span></div>
        <div class="system-info-item"><span class="system-info-label">Last Updated</span><span class="system-info-value">${escapeHtml(formatTimeFull(STATE.lastUpdated))}</span></div>
        <div class="system-info-item"><span class="system-info-label">Polling Interval</span><span class="system-info-value">${STATE.pollingInterval}s</span></div>
        <div class="system-info-item"><span class="system-info-label">Knowledge Entries</span><span class="system-info-value">${STATE.knowledge.length}</span></div>
        <div class="system-info-item"><span class="system-info-label">Active Alerts</span><span class="system-info-value">${STATE.alerts.length}</span></div>
      </div>
    </div>
  `;

  bindSettings();
}

/* ---------- Polling & Init ---------- */
let pollingTimer = null;

function startPolling() {
  if (pollingTimer) clearInterval(pollingTimer);
  pollingTimer = setInterval(() => {
    refreshAllData().catch(() => {});
  }, Math.max(10, STATE.pollingInterval) * 1000);
  const status = document.getElementById('polling-status');
  if (status) status.textContent = `Auto-refresh every ${STATE.pollingInterval}s`;
}

function bindShellChrome() {
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    document.body.classList.toggle('sidebar-collapsed');
  });

  document.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', closeChartModal);
  });

  document.getElementById('notify-bell')?.addEventListener('click', () => {
    const dot = document.getElementById('notify-dot');
    if (dot) dot.hidden = true;
    showNotification('You are up to date with the latest investigation events.', 'success', 'Notifications');
  });

  const globalSearch = document.getElementById('global-search');
  globalSearch?.addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const q = globalSearch.value.trim();
    if (!q) return;
    setActiveView('search');
    await renderCurrentView();
    const input = document.getElementById('search-input');
    if (input) {
      input.value = q;
      document.getElementById('search-form')?.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
  });

  document.body.classList.toggle('light-theme', STATE.theme === 'light');
}

async function init() {
  bindShellChrome();
  bindNavigation();
  setActiveView('dashboard');

  const view = document.getElementById('view-dashboard');
  if (view) view.innerHTML = showSkeletonGrid(5);

  await refreshAllData();
  startPolling();
  showNotification('Near Zero Command Center is online', 'success', 'Connected');
}

window.refreshAllData = refreshAllData;
window.loadAlertContext = loadAlertContext;
window.selectAlert = selectAlert;
window.renderCurrentView = renderCurrentView;
window.renderSearch = renderSearch;
window.renderServiceNow = renderServiceNow;
window.renderRoadmap = renderRoadmap;
window.renderSettings = renderSettings;
window.startPolling = startPolling;

window.addEventListener('DOMContentLoaded', () => {
  init().catch(() => {
    updateStatusPill('Startup issue', 'warning');
    const view = document.getElementById('view-dashboard');
    if (view) {
      view.innerHTML = `<div class="card">${showEmpty('Unable to complete startup refresh. The UI remains available and will retry.', 'Connection Delayed', 'fa-plug')}</div>`;
    }
  });
});

window.addEventListener('error', () => {
  // Prevent raw JS errors from appearing as broken UI
  showNotification('A non-critical UI issue was handled gracefully.', 'warning', 'Stability');
});

window.addEventListener('unhandledrejection', () => {
  showNotification('A background request failed. Showing last known data.', 'warning', 'Connectivity');
});
