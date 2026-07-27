/* =========================================================
   NZCC — Live Investigation
   ========================================================= */

async function renderInvestigation() {
  const view = document.getElementById('view-investigation');
  if (!view) return;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Live Investigation</h1>
        <p class="muted">End-to-end AI investigation pipeline with live evidence and progress</p>
      </div>
      <div class="action-buttons">
        <button class="btn-secondary" type="button" onclick="setActiveView('alerts');renderCurrentView()"><i class="fas fa-list"></i> Select Alert</button>
        <button id="refresh-investigation" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3>Current Investigation</h3></div>
      <div id="investigation-summary"></div>
    </div>

    <div class="card">
      <div class="card-header">
        <div><h3>AI Investigation Pipeline</h3><span class="muted">Animated stage progress</span></div>
        <div id="investigation-progress-label" class="muted"></div>
      </div>
      <div id="investigation-progress-bar"></div>
      <div id="investigation-pipeline-h" class="pipeline-horizontal" style="margin-top:14px"></div>
    </div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><h3>Stage Detail</h3></div>
        <div id="investigation-pipeline" class="pipeline-flow"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Investigation Timeline</h3></div>
        <div id="investigation-timeline" class="timeline-container"></div>
      </div>
    </div>

    <div class="grid-row three-col">
      <div class="card">
        <div class="card-header"><h3>Evidence Summary</h3></div>
        <div id="evidence-cards" class="evidence-grid"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Collected Metrics</h3></div>
        <div id="live-metrics" class="metrics-grid"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Historical Matches</h3></div>
        <div id="historical-incidents" class="incidents-grid"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3>Log Intelligence</h3></div>
      <div id="recent-logs" class="logs-list"></div>
    </div>

    <div class="card rca-card">
      <div class="card-header"><h3>AI Root Cause Analysis</h3></div>
      <div id="investigation-rca"></div>
    </div>
  `;

  if (!STATE.selectedAlert) {
    document.getElementById('investigation-summary').innerHTML = showEmpty(
      'Select an alert from Active Alerts to begin a live investigation walkthrough.',
      'No Investigation Selected',
      'fa-microscope'
    );
    document.getElementById('investigation-pipeline').innerHTML = '';
    document.getElementById('investigation-pipeline-h').innerHTML = (window.NZCC_CONFIG.PIPELINE_STAGES || [])
      .map((s) => UI.createPipelineChip(s, 'waiting')).join('');
    document.getElementById('investigation-timeline').innerHTML = showPlaceholder('Waiting for Backend', 'Timeline appears when an investigation is selected.');
    document.getElementById('evidence-cards').innerHTML = showPlaceholder('No Data Available', 'Evidence cards populate during investigation.');
    document.getElementById('live-metrics').innerHTML = showPlaceholder('Metric Collection Pending', 'Metrics appear after playbook execution.');
    document.getElementById('historical-incidents').innerHTML = showPlaceholder('Historical Incident Intelligence', 'Similar incidents appear after semantic matching.');
    document.getElementById('recent-logs').innerHTML = showPlaceholder('Log Collection Pending', 'Logs are not currently available for this host. Investigation continues using metrics and historical intelligence.');
    document.getElementById('investigation-rca').innerHTML = showPlaceholder('AI Investigation Engine', 'Root cause output appears when analysis completes.');
    bindRefreshButtons();
    return;
  }

  const alert = STATE.selectedAlert;
  const metrics = STATE.currentInvestigationMetrics || [];
  const logs = STATE.currentInvestigationLogs || [];
  const stages = UI.derivePipelineStages(alert, STATE.rca, metrics, logs, STATE.knowledge);
  const completed = stages.filter((s) => s.status === 'completed').length;
  const progress = Math.round((completed / Math.max(stages.length, 1)) * 100);
  const current = stages.find((s) => s.status === 'processing') || stages[stages.length - 1];
  const elapsed = alert.createdAt ? Math.max(0, Math.floor((Date.now() - new Date(alert.createdAt).getTime()) / 1000)) : null;

  document.getElementById('investigation-summary').innerHTML = `
    <div class="investigation-context">
      <div class="metric-card">
        <h4 style="margin-bottom:10px">${escapeHtml(alert.problem || '—')}</h4>
        <p><strong>Host:</strong> ${escapeHtml(alert.host || '—')}</p>
        <p><strong>Technology:</strong> ${escapeHtml(alert.technology || '—')}</p>
        <p style="margin-top:8px">${UI.createBadge(alert.severity || 'Information', severityClass(alert.severity))}</p>
      </div>
      <div class="metric-card">
        <h4 style="margin-bottom:10px">Processing Status</h4>
        <p><strong>Current Stage:</strong> ${escapeHtml(current?.name || '—')}</p>
        <p><strong>Elapsed:</strong> ${escapeHtml(formatDuration(elapsed))}</p>
        <p><strong>ServiceNow:</strong> ${escapeHtml(alert.incidentNumber || 'Awaiting correlation')}</p>
        <p style="margin-top:8px">${UI.createBadge(alert.status || 'Open', 'info')}</p>
      </div>
    </div>
  `;

  document.getElementById('investigation-progress-label').textContent = `${progress}% complete · ${current?.name || ''}`;
  document.getElementById('investigation-progress-bar').innerHTML = `
    <div class="progress-bar"><div class="progress-fill" style="width:${progress}%">${progress}%</div></div>
  `;
  document.getElementById('investigation-pipeline-h').innerHTML = stages.map((s) => UI.createPipelineChip(s.name, s.status)).join('');
  document.getElementById('investigation-pipeline').innerHTML = stages.map((s) => UI.createPipelineStep(s.name, s.status)).join('');

  document.getElementById('investigation-timeline').innerHTML = [
    { title: 'Alert received', time: alert.createdAt },
    { title: 'Alert parsed & normalized', time: alert.createdAt },
    { title: 'ServiceNow correlation attempted', time: alert.createdAt },
    { title: 'Trigger & playbook resolution', time: alert.createdAt },
    { title: 'Historical incident intelligence search', time: alert.createdAt },
    { title: 'Evidence correlation & AI RCA', time: alert.createdAt }
  ].map((e, i) => UI.createTimelineEntry(e.title, e.time, i === 5 && STATE.rca?.rootCause ? 'active' : 'completed')).join('');

  const logOk = hasData(logs) && !/not currently available|unavailable/i.test(String(logs[0]?.message || ''));
  document.getElementById('evidence-cards').innerHTML = [
    { name: 'ITSM', ok: !!(alert.incidentNumber && alert.incidentNumber !== '—'), count: alert.incidentNumber && alert.incidentNumber !== '—' ? '1' : '0' },
    { name: 'Metrics', ok: hasData(metrics), count: String(metrics.length) },
    { name: 'Logs', ok: logOk, count: String(logOk ? logs.length : 0) },
    { name: 'History', ok: hasData(STATE.knowledge), count: String(Math.min(STATE.knowledge.length, 4)) },
    { name: 'Playbook', ok: !!alert.technology, count: alert.technology ? '1' : '0' }
  ].map((e) => `
    <div class="evidence-card ${e.ok ? 'collected' : ''}">
      <div class="evidence-header"><h4>${escapeHtml(e.name)}</h4>${UI.createBadge(e.ok ? 'Ready' : 'Pending', e.ok ? 'success' : 'muted')}</div>
      <div class="evidence-count">${escapeHtml(e.count)}</div>
    </div>
  `).join('');

  document.getElementById('live-metrics').innerHTML = hasData(metrics)
    ? metrics.slice(0, 8).map((m) => UI.createMetricCard(m.name, m.value, m.unit)).join('')
    : showPlaceholder('Metric not collected for this technology.', 'Metrics will appear once collection completes for the selected host.');

  const similar = UI.similarIncidents(alert, STATE.knowledge);
  document.getElementById('historical-incidents').innerHTML = similar.length
    ? similar.map((inc) => `
        <div class="incident-card">
          <div style="text-align:center;margin-bottom:10px">
            <strong style="font-size:20px;color:var(--success)">${inc.similarity}%</strong>
            <p class="muted">similarity</p>
          </div>
          <p><strong>${escapeHtml(inc.problem || '—')}</strong></p>
          <p class="muted">${escapeHtml(inc.technology || '—')}</p>
          <p class="muted" style="margin-top:6px">Root: ${escapeHtml(inc.rootCause || '—')}</p>
        </div>`).join('')
    : showPlaceholder('Historical Incident Intelligence', 'No similar indexed investigations matched this case yet.');

  document.getElementById('recent-logs').innerHTML = logOk
    ? logs.slice(0, 12).map((log) => {
        const msg = String(log.message || '');
        const cls = /error/i.test(msg) ? 'error' : /warn/i.test(msg) ? 'warning' : 'info';
        return `<div class="log-entry ${cls}"><div class="muted" style="font-size:10px">${formatTime(log.timestamp)} · ${escapeHtml(log.host || '')}</div><div>${escapeHtml(msg)}</div></div>`;
      }).join('')
    : showPlaceholder(
      'Logs Unavailable',
      'Logs are not currently available for this host. Investigation continues using metrics and historical intelligence.'
    );

  const rca = STATE.rca;
  const conf = confidencePercent(rca?.confidence);
  document.getElementById('investigation-rca').innerHTML = rca?.rootCause
    ? `
      <div class="rca-content">
        <div class="rca-section"><h4>Root Cause</h4><p>${escapeHtml(rca.rootCause)}</p></div>
        <div class="rca-section"><h4>Business Impact</h4><p>${escapeHtml(rca.impact || 'Impact assessment in progress.')}</p></div>
        <div class="rca-section">
          <h4>Confidence</h4>
          <div class="progress-bar"><div class="progress-fill" style="width:${conf}%"></div></div>
          <span class="muted">${conf}% confidence</span>
        </div>
        <div class="rca-section">
          <h4>AI Investigation Progress</h4>
          <p class="muted">${progress}% of pipeline stages complete. ${hasRcaPending(rca) ? 'Analysis refining…' : 'Analysis ready for review.'}</p>
        </div>
      </div>`
    : showPlaceholder('AI Investigation Engine', 'Root cause analysis is being generated from live evidence.');

  bindRefreshButtons();
}

function hasRcaPending(rca) {
  return !rca?.rootCause || String(rca.rootCause).includes('being generated');
}

window.renderInvestigation = renderInvestigation;
