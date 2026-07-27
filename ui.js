/* =========================================================
   NZCC — UI Utilities
   ========================================================= */

const UI = {
  renderChart(containerId, type = 'line', data = []) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!hasData(data)) {
      container.innerHTML = showEmpty('Waiting for backend telemetry to populate this chart.', 'No Chart Data', 'fa-chart-area');
      return;
    }

    if (type === 'trend') {
      const values = data.map((d) => Number(d.value) || 0);
      const max = Math.max(...values, 1);
      const points = data.map((item, i) => {
        const x = (i / Math.max(data.length - 1, 1)) * 300;
        const y = 120 - ((Number(item.value) || 0) / max) * 100;
        return `${x},${y}`;
      }).join(' ');
      const area = `0,120 ${points} 300,120`;
      const labels = data.map((item) => `<span class="chart-label">${escapeHtml(item.label || '')}</span>`).join('');
      container.innerHTML = `
        <div class="trend-chart-shell">
          <svg viewBox="0 0 300 140" width="100%" height="160" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="trendFill-${containerId}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#F97316" stop-opacity="0.35"/>
                <stop offset="100%" stop-color="#F97316" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <line x1="0" y1="120" x2="300" y2="120" stroke="rgba(255,255,255,0.12)" />
            <polygon fill="url(#trendFill-${containerId})" points="${area}" />
            <polyline fill="none" stroke="#F97316" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${points}" />
          </svg>
          <div class="chart-label-row">${labels}</div>
        </div>
      `;
      return;
    }

    if (type === 'bar') {
      const max = Math.max(...data.map((d) => d.count || d.value || 0), 1);
      container.innerHTML = `<div class="bar-chart-container">${data.map((item) => {
        const val = item.count || item.value || 0;
        const h = Math.max(4, Math.round((val / max) * 100));
        return `
          <div class="bar-item" title="${escapeHtml(String(item.label || ''))}: ${val}">
            <div class="bar-track"><div class="bar-fill" style="height:${h}%"></div></div>
            <span>${escapeHtml(item.label || '')}</span>
          </div>`;
      }).join('')}</div>`;
      return;
    }

    if (type === 'donut') {
      const colors = ['#EF4444', '#F97316', '#F59E0B', '#3B82F6', '#22C55E'];
      const total = data.reduce((s, d) => s + (d.count || d.value || 0), 0) || 1;
      let offset = 0;
      const stops = data.map((item, i) => {
        const pct = ((item.count || item.value || 0) / total) * 100;
        const start = offset;
        offset += pct;
        return `${colors[i % colors.length]} ${start}% ${offset}%`;
      }).join(', ');
      container.innerHTML = `
        <div class="donut-row">
          <div style="width:120px;height:120px;border-radius:50%;background:conic-gradient(${stops});position:relative;flex-shrink:0;">
            <div style="position:absolute;inset:22px;border-radius:50%;background:var(--card);display:grid;place-items:center;">
              <div style="text-align:center"><strong style="font-size:18px">${total}</strong><div class="muted" style="font-size:10px">Total</div></div>
            </div>
          </div>
          <div class="legend-list">
            ${data.map((item, i) => `
              <div class="legend-item">
                <div class="legend-left"><span class="legend-swatch" style="background:${colors[i % colors.length]}"></span>${escapeHtml(item.label || '')}</div>
                <strong>${item.count || item.value || 0}</strong>
              </div>`).join('')}
          </div>
        </div>`;
    }
  },

  createKpiCard(value, label, hint = '', accent = '') {
    return `
      <div class="kpi-card ${accent ? `accent-${accent}` : ''} anim-count">
        <span class="kpi-label">${escapeHtml(label)}</span>
        <strong class="kpi-value">${escapeHtml(String(value))}</strong>
        ${hint ? `<span class="kpi-hint">${escapeHtml(hint)}</span>` : ''}
      </div>`;
  },

  createMetricCard(name, value, unit = '', health = 'normal') {
    const color = health === 'critical' ? 'var(--critical)' : health === 'warning' ? 'var(--warning)' : 'var(--accent)';
    return `
      <div class="metric-gauge">
        <span class="metric-gauge-label">${escapeHtml(name || 'Metric')}</span>
        <span class="metric-gauge-value" style="color:${color}">${escapeHtml(String(value ?? '—'))}</span>
        <span class="muted">${escapeHtml(unit || '')}</span>
      </div>`;
  },

  createBadge(text, type) {
    const t = type || severityClass(text);
    const map = {
      critical: 'badge-critical',
      high: 'badge-high',
      average: 'badge-average',
      information: 'badge-information',
      success: 'badge-success',
      warning: 'badge-warning',
      info: 'badge-info',
      muted: 'badge-muted'
    };
    return `<span class="badge ${map[t] || 'badge-info'}">${escapeHtml(text || '—')}</span>`;
  },

  createPipelineStep(name, status, detail = '') {
    const icon = status === 'completed' ? '✓' : status === 'processing' ? '●' : '○';
    return `
      <div class="pipeline-step ${status}">
        <span class="dot">${icon}</span>
        <div>
          <strong>${escapeHtml(name)}</strong>
          <div class="muted">${escapeHtml(detail || (status === 'completed' ? 'Complete' : status === 'processing' ? 'In progress' : 'Queued'))}</div>
        </div>
      </div>`;
  },

  createPipelineChip(name, status) {
    return `<div class="pipeline-chip ${status}">${escapeHtml(name)}</div>`;
  },

  createTimelineEntry(title, time, status = 'completed') {
    return `
      <div class="timeline-entry ${status === 'active' ? 'active' : ''}">
        <div class="timeline-dot"></div>
        <div class="timeline-content">
          <div class="timeline-time">${escapeHtml(formatTime(time))}</div>
          <div class="timeline-title">${escapeHtml(title)}</div>
        </div>
      </div>`;
  },

  createIncidentCard(incident) {
    return `
      <div class="incident-card">
        <h4>${escapeHtml(incident.incidentNumber || 'Incident')}</h4>
        <p class="muted">${escapeHtml(incident.problem || '—')}</p>
        <p style="margin-top:8px">${UI.createBadge(incident.priority || 'High', severityClass(incident.priority))}</p>
        <p style="margin-top:6px">${UI.createBadge(incident.status || 'In Progress', 'info')}</p>
        <p class="muted" style="margin-top:8px;font-size:12px">${escapeHtml(incident.assignmentGroup || 'Operations')}</p>
      </div>`;
  },

  createRoadmapCard(item) {
    const status = item.status || 'Planned';
    const color = status === 'Completed' ? 'var(--success)' : status === 'In Progress' ? 'var(--accent)' : 'var(--muted)';
    const cls = status === 'Completed' ? 'success' : status === 'In Progress' ? 'high' : 'muted';
    return `
      <div class="roadmap-card" style="border-color: color-mix(in srgb, ${color} 35%, var(--border))">
        <div class="eyebrow">${escapeHtml(item.phase || '')}</div>
        <h4>${escapeHtml(item.title)}</h4>
        <p class="muted">${escapeHtml(item.description || '')}</p>
        ${UI.createBadge(status, cls)}
      </div>`;
  },

  createHealthIndicator(name, healthy = true) {
    return `
      <div class="health-item">
        <div class="health-indicator">
          <div class="health-dot ${healthy ? '' : 'critical'}"></div>
          <span class="health-text">${escapeHtml(name)}</span>
        </div>
        <span class="muted">${healthy ? 'Connected' : 'Waiting'}</span>
      </div>`;
  },

  createActivityItem(alert) {
    return `
      <div class="activity-item" data-id="${escapeHtml(alert.problemId || '')}">
        <div class="activity-icon"><i class="fas fa-bolt"></i></div>
        <div class="activity-body">
          <strong>${escapeHtml(alert.problem || 'Investigation')}</strong>
          <span>${escapeHtml(alert.host || '—')} · ${escapeHtml(alert.technology || '—')}</span>
        </div>
        <div class="activity-meta">
          ${UI.createBadge(alert.severity || 'Info', severityClass(alert.severity))}
          <div style="margin-top:6px">${escapeHtml(formatTime(alert.createdAt))}</div>
        </div>
      </div>`;
  },

  bindCollapse(root) {
    root?.querySelectorAll('.card.collapsible .card-header').forEach((header) => {
      header.addEventListener('click', () => header.closest('.card')?.classList.toggle('collapsed'));
    });
  },

  derivePipelineStages(alert, rca, metrics, logs, knowledge) {
    const stages = window.NZCC_CONFIG.PIPELINE_STAGES;
    const hasAlert = !!alert;
    const hasSnow = !!(alert?.incidentNumber && alert.incidentNumber !== '—');
    const hasTrigger = !!(alert?.trigger && alert.trigger !== '—');
    const hasTech = !!(alert?.technology);
    const hasMetrics = hasData(metrics);
    const hasLogs = hasData(logs) && !String(logs[0]?.message || '').includes('not currently available') && !String(logs[0]?.message || '').includes('unavailable');
    const hasRca = !!(rca?.rootCause && !String(rca.rootCause).includes('being generated'));
    const hasKnowledge = hasData(knowledge);

    const flags = [
      hasAlert,
      hasAlert,
      hasSnow || hasAlert,
      hasTrigger || hasAlert,
      hasTech || hasAlert,
      hasKnowledge || hasAlert,
      hasMetrics,
      hasLogs,
      hasMetrics || hasLogs || hasRca,
      hasRca,
      hasRca && hasKnowledge
    ];

    let current = flags.findIndex((f) => !f);
    if (current === -1) current = flags.length - 1;

    return stages.map((name, i) => {
      let status = 'waiting';
      if (flags[i]) status = 'completed';
      else if (i === current) status = 'processing';
      return { name, status };
    });
  },

  similarIncidents(alert, knowledge) {
    if (!alert || !hasData(knowledge)) return [];
    return knowledge
      .filter((k) => k.host === alert.host || k.technology === alert.technology || (k.problem && alert.problem && k.problem !== alert.problem))
      .slice(0, 4)
      .map((k) => ({
        problem: k.problem,
        technology: k.technology,
        rootCause: k.rootCause,
        confidence: k.confidence,
        similarity: Math.round((Number(k.confidence) || 0.7) * 100)
      }));
  }
};

function bindNavigation() {
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.addEventListener('click', async () => {
      const view = link.dataset.view;
      setActiveView(view);
      try {
        await renderCurrentView();
      } catch (e) {
        showNotification('Unable to render this view. Please refresh.', 'warning', 'View Error');
      }
    });
  });
}

function bindSettings() {
  const themeSelect = document.getElementById('theme-select');
  if (themeSelect) {
    themeSelect.value = STATE.theme;
    themeSelect.onchange = (e) => {
      STATE.theme = e.target.value;
      localStorage.setItem('nzcc_theme', STATE.theme);
      document.body.classList.toggle('light-theme', STATE.theme === 'light');
      showNotification(`Theme set to ${STATE.theme}`, 'success', 'Settings');
    };
  }

  const pollingSelect = document.getElementById('polling-select');
  if (pollingSelect) {
    pollingSelect.value = String(STATE.pollingInterval);
    pollingSelect.onchange = (e) => {
      STATE.pollingInterval = Math.max(10, Number(e.target.value) || 30);
      localStorage.setItem('nzcc_polling', String(STATE.pollingInterval));
      startPolling();
      const status = document.getElementById('polling-status');
      if (status) status.textContent = `Auto-refresh every ${STATE.pollingInterval}s`;
      showNotification(`Polling interval set to ${STATE.pollingInterval}s`, 'success', 'Settings');
    };
  }

  const backendUrl = document.getElementById('backend-url');
  if (backendUrl) {
    backendUrl.value = window.NZCC_CONFIG.API_BASE;
    backendUrl.onchange = (e) => {
      window.NZCC_CONFIG.API_BASE = e.target.value || '/api';
      showNotification('Backend URL updated', 'success', 'Settings');
    };
  }

  const demoMode = document.getElementById('demo-mode');
  if (demoMode) {
    demoMode.checked = STATE.demoMode;
    demoMode.onchange = (e) => {
      STATE.demoMode = e.target.checked;
      localStorage.setItem('nzcc_demo', STATE.demoMode ? '1' : '0');
    };
  }

  const notifToggle = document.getElementById('notifications-toggle');
  if (notifToggle) {
    notifToggle.checked = STATE.notifications;
    notifToggle.onchange = (e) => {
      STATE.notifications = e.target.checked;
      localStorage.setItem('nzcc_notifications', STATE.notifications ? '1' : '0');
    };
  }
}

function bindRefreshButtons() {
  ['dashboard', 'investigation', 'alerts', 'rca', 'knowledge', 'metrics', 'logs', 'servicenow', 'analytics'].forEach((view) => {
    const btn = document.getElementById(`refresh-${view}`);
    if (!btn || btn.dataset.bound === '1') return;
    btn.dataset.bound = '1';
    btn.addEventListener('click', async () => {
      btn.classList.add('refreshing');
      await refreshAllData();
      btn.classList.remove('refreshing');
    });
  });
}

function openChartModal(chartId) {
  const modal = document.getElementById('chart-modal');
  const container = document.getElementById(chartId);
  if (!modal || !container) return;
  document.getElementById('modal-chart').innerHTML = container.innerHTML;
  modal.hidden = false;
  modal.classList.add('active');
}

function closeChartModal() {
  const modal = document.getElementById('chart-modal');
  if (!modal) return;
  modal.hidden = true;
  modal.classList.remove('active');
}

window.UI = UI;
window.bindNavigation = bindNavigation;
window.bindSettings = bindSettings;
window.bindRefreshButtons = bindRefreshButtons;
window.openChartModal = openChartModal;
window.closeChartModal = closeChartModal;
