/* =========================================================
   NZCC — RCA Analysis (primary demo page)
   ========================================================= */

async function renderRCA() {
  const view = document.getElementById('view-rca');
  if (!view) return;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>RCA Analysis</h1>
        <p class="muted">Primary investigation brief — evidence, AI root cause, and recommended resolution</p>
      </div>
      <div class="action-buttons">
        <button class="btn-secondary" type="button" onclick="setActiveView('investigation');renderCurrentView()"><i class="fas fa-microscope"></i> Live View</button>
        <button id="refresh-rca" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
        <button id="export-rca" class="btn-primary" type="button"><i class="fas fa-file-pdf"></i> Export PDF</button>
      </div>
    </div>

    <div id="rca-body"></div>
  `;

  const body = document.getElementById('rca-body');

  if (!STATE.selectedAlert) {
    body.innerHTML = `
      <div class="card">
        ${showEmpty('Choose an alert from Active Alerts to open a full RCA brief.', 'No Investigation Selected', 'fa-brain')}
      </div>`;
    bindRefreshButtons();
    return;
  }

  const alert = STATE.selectedAlert;
  const rca = STATE.rca || {};
  const metrics = STATE.currentInvestigationMetrics || [];
  const logs = STATE.currentInvestigationLogs || [];
  const similar = UI.similarIncidents(alert, STATE.knowledge);
  const stages = UI.derivePipelineStages(alert, rca, metrics, logs, STATE.knowledge);
  const conf = confidencePercent(rca.confidence);
  const reasoning = asArray(rca.reasoning);
  const resolution = asArray(rca.recommendedResolution);
  const diagnostics = asArray(rca.nextDiagnostics);
  const logOk = hasData(logs) && !/not currently available|unavailable/i.test(String(logs[0]?.message || ''));
  const elapsed = alert.createdAt ? Math.max(0, Math.floor((Date.now() - new Date(alert.createdAt).getTime()) / 1000)) : null;
  const hasRca = rca.rootCause && !String(rca.rootCause).includes('being generated');

  body.innerHTML = `
    <div class="card">
      <div class="card-header"><h3>Alert Summary</h3>${UI.createBadge(alert.status || 'Open', 'info')}</div>
      <div class="summary-grid">
        <div class="metric-card"><strong>Problem</strong><p style="margin-top:6px">${escapeHtml(alert.problem || '—')}</p></div>
        <div class="metric-card"><strong>Host</strong><p style="margin-top:6px">${escapeHtml(alert.host || '—')}</p></div>
        <div class="metric-card"><strong>Technology</strong><p style="margin-top:6px">${escapeHtml(alert.technology || '—')}</p></div>
        <div class="metric-card"><strong>Severity</strong><p style="margin-top:6px">${UI.createBadge(alert.severity || 'Information', severityClass(alert.severity))}</p></div>
        <div class="metric-card"><strong>Trigger</strong><p style="margin-top:6px">${escapeHtml(alert.trigger || '—')}</p></div>
        <div class="metric-card"><strong>Event</strong><p style="margin-top:6px">${escapeHtml(alert.problemId || '—')}</p></div>
        <div class="metric-card"><strong>ServiceNow</strong><p style="margin-top:6px">${escapeHtml(alert.incidentNumber || 'Awaiting sync')}</p></div>
        <div class="metric-card"><strong>Investigation Duration</strong><p style="margin-top:6px">${escapeHtml(formatDuration(elapsed))}</p></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3>Investigation Pipeline</h3></div>
      <div class="pipeline-horizontal">${stages.map((s) => UI.createPipelineChip(s.name, s.status)).join('')}</div>
    </div>

    <div class="grid-row two-col">
      <div class="card collapsible">
        <div class="card-header"><h3>Metrics Summary</h3><i class="fas fa-chevron-down collapse-icon"></i></div>
        <div class="card-body">
          <div class="metrics-grid">
            ${hasData(metrics)
              ? metrics.slice(0, 10).map((m) => UI.createMetricCard(m.name, m.value, m.unit)).join('')
              : showPlaceholder('Metric not collected for this technology.', 'Metric evidence will appear once collection completes.')}
          </div>
        </div>
      </div>
      <div class="card collapsible">
        <div class="card-header"><h3>Log Summary</h3><i class="fas fa-chevron-down collapse-icon"></i></div>
        <div class="card-body">
          <div class="logs-list">
            ${logOk
              ? logs.slice(0, 10).map((log) => {
                  const msg = String(log.message || '');
                  const cls = /error/i.test(msg) ? 'error' : /warn/i.test(msg) ? 'warning' : 'info';
                  return `<div class="log-entry ${cls}"><div class="muted" style="font-size:10px">${formatTime(log.timestamp)}</div><div>${escapeHtml(msg)}</div></div>`;
                }).join('')
              : showPlaceholder(
                'Logs Unavailable',
                'Logs are not currently available for this host. Investigation continues using metrics and historical intelligence.'
              )}
          </div>
        </div>
      </div>
    </div>

    <div class="card collapsible">
      <div class="card-header"><h3>Historical Similar Incidents</h3><i class="fas fa-chevron-down collapse-icon"></i></div>
      <div class="card-body">
        <div class="incidents-grid">
          ${similar.length
            ? similar.map((inc) => `
                <div class="incident-card">
                  <div style="text-align:center;margin-bottom:8px">
                    <strong style="font-size:18px;color:var(--success)">${inc.similarity}%</strong>
                    <p class="muted">similarity</p>
                  </div>
                  <p><strong>${escapeHtml(inc.problem || '—')}</strong></p>
                  <p class="muted">${escapeHtml(inc.technology || '—')}</p>
                  <p class="muted" style="margin-top:6px">${escapeHtml(inc.rootCause || '—')}</p>
                </div>`).join('')
            : showPlaceholder('Historical Incident Intelligence', 'Similar indexed investigations will appear here when matches are available.')}
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3>Evidence Sources</h3></div>
      <div class="evidence-grid">
        ${[
          { name: 'Alert Context', ok: true },
          { name: 'ITSM Correlation', ok: !!(alert.incidentNumber && alert.incidentNumber !== '—') },
          { name: 'Metrics', ok: hasData(metrics) },
          { name: 'Log Intelligence', ok: logOk },
          { name: 'Historical Intelligence', ok: similar.length > 0 },
          { name: 'AI Investigation Engine', ok: !!hasRca }
        ].map((e) => `
          <div class="evidence-card ${e.ok ? 'collected' : ''}">
            <div class="evidence-header"><h4>${escapeHtml(e.name)}</h4>${UI.createBadge(e.ok ? 'Available' : 'Pending', e.ok ? 'success' : 'muted')}</div>
          </div>`).join('')}
      </div>
    </div>

    <div class="card rca-main">
      <div class="card-header">
        <h3>AI Root Cause</h3>
        ${UI.createBadge(hasRca ? 'Ready' : 'In Progress', hasRca ? 'success' : 'high')}
      </div>
      <div class="rca-content">
        <div class="rca-section">
          <h4>Root Cause</h4>
          <p>${escapeHtml(hasRca ? rca.rootCause : 'Root cause is being generated from live evidence.')}</p>
        </div>
        <div class="rca-section">
          <h4>Business Impact</h4>
          <p>${escapeHtml(rca.impact || 'Impact assessment will appear when analysis completes.')}</p>
        </div>
        <div class="rca-section">
          <h4>Confidence</h4>
          <div class="confidence-ring">
            <div style="flex:1">
              <div class="progress-bar"><div class="progress-fill" style="width:${conf}%"></div></div>
            </div>
            <strong style="font-size:22px;color:var(--accent)">${conf}%</strong>
          </div>
        </div>
        <div class="rca-section">
          <h4>Reasoning</h4>
          ${reasoning.length
            ? `<ul style="padding-left:18px;line-height:1.6">${reasoning.map((r) => `<li>${escapeHtml(String(r))}</li>`).join('')}</ul>`
            : showPlaceholder('Awaiting backend integration', 'Detailed reasoning will be shown when available.')}
        </div>
      </div>
    </div>

    <div class="grid-row two-col">
      <div class="card collapsible">
        <div class="card-header"><h3>Recommended Resolution</h3><i class="fas fa-chevron-down collapse-icon"></i></div>
        <div class="card-body resolution-steps">
          ${resolution.length
            ? resolution.map((step, i) => `<div><strong>${i + 1}.</strong> ${escapeHtml(String(step))}</div>`).join('')
            : showPlaceholder('No Data Available Yet', 'Resolution guidance will appear after AI analysis completes.')}
        </div>
      </div>
      <div class="card collapsible">
        <div class="card-header"><h3>Validation Checklist</h3><i class="fas fa-chevron-down collapse-icon"></i></div>
        <div class="card-body checklist">
          ${(diagnostics.length
            ? diagnostics
            : [
              'Confirm alert condition is still active',
              'Validate collected metrics against thresholds',
              'Review recommended resolution with on-call owner',
              'Update ServiceNow with investigation outcome'
            ]).map((item, i) => `
              <div class="check-item">
                <i class="fas ${i < (hasRca ? 2 : 0) ? 'fa-circle-check done' : 'fa-circle pending'}"></i>
                <span>${escapeHtml(String(item))}</span>
              </div>`).join('')}
        </div>
      </div>
    </div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><h3>Investigation Timeline</h3></div>
        <div class="timeline-container">
          ${[
            'Alert received',
            'Evidence collection started',
            'Historical intelligence searched',
            'AI root cause generated',
            'Knowledge repository updated'
          ].map((t, i) => UI.createTimelineEntry(t, alert.createdAt, i === 3 && hasRca ? 'active' : 'completed')).join('')}
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Investigation Statistics</h3></div>
        <div class="statistics-grid">
          ${UI.createKpiCard(metrics.length, 'Metrics')}
          ${UI.createKpiCard(logOk ? logs.length : 0, 'Log Entries')}
          ${UI.createKpiCard(similar.length, 'Similar Cases')}
          ${UI.createKpiCard(`${conf}%`, 'Confidence')}
        </div>
      </div>
    </div>
  `;

  UI.bindCollapse(body);

  document.getElementById('export-rca')?.addEventListener('click', () => {
    const lines = [
      'Near Zero Command Center — RCA Report',
      `Exported: ${new Date().toLocaleString()}`,
      '',
      `Problem: ${alert.problem || '—'}`,
      `Host: ${alert.host || '—'}`,
      `Technology: ${alert.technology || '—'}`,
      `Severity: ${alert.severity || '—'}`,
      `ServiceNow: ${alert.incidentNumber || '—'}`,
      `Trigger: ${alert.trigger || '—'}`,
      `Event / Problem ID: ${alert.problemId || '—'}`,
      '',
      `Root Cause: ${hasRca ? rca.rootCause : 'In progress'}`,
      `Business Impact: ${rca.impact || '—'}`,
      `Confidence: ${conf}%`,
      '',
      'Recommended Resolution:',
      ...(resolution.length ? resolution.map((s, i) => `  ${i + 1}. ${s}`) : ['  —']),
      '',
      'Validation Checklist:',
      ...(diagnostics.length ? diagnostics.map((s, i) => `  ${i + 1}. ${s}`) : ['  —'])
    ];
    const blob = new Blob([buildRcaPdf(lines)], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nzcc-rca-${alert.problemId || 'report'}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    showNotification('RCA report downloaded as PDF', 'success', 'Export');
  });

  bindRefreshButtons();
}

window.renderRCA = renderRCA;

/** Minimal single-page text PDF for RCA download (no external libs). */
function buildRcaPdf(lines) {
  const esc = (s) => String(s).replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
  const content = ['BT', '/F1 11 Tf', '50 760 Td', '14 TL'];
  lines.forEach((line, i) => {
    const t = esc(String(line).slice(0, 95));
    content.push(i === 0 ? `(${t}) Tj` : `T* (${t}) Tj`);
  });
  content.push('ET');
  const stream = content.join('\n');
  const objs = [];
  objs.push('1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n');
  objs.push('2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n');
  objs.push('3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n');
  objs.push(`4 0 obj<< /Length ${stream.length} >>stream\n${stream}\nendstream\nendobj\n`);
  objs.push('5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n');
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  objs.forEach((o) => {
    offsets.push(pdf.length);
    pdf += o;
  });
  const xref = pdf.length;
  pdf += `xref\n0 ${objs.length + 1}\n`;
  pdf += '0000000000 65535 f \n';
  for (let i = 1; i < offsets.length; i++) {
    pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return pdf;
}
