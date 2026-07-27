/* =========================================================
   NZCC — API Layer & Global State
   ========================================================= */

const API = {
  async call(endpoint, params = {}) {
    const base = window.NZCC_CONFIG?.API_BASE || '/api';
    try {
      const url = new URL(String(base).replace(/\/$/, '') + endpoint, window.location.origin);
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.set(key, value);
        }
      });
      const response = await fetch(url.toString(), {
        headers: { Accept: 'application/json' },
        cache: 'no-store'
      });
      if (!response.ok) {
        return { error: `Request failed (${response.status})`, unavailable: true };
      }
      const data = await response.json();
      if (data && data.error) {
        return { ...data, unavailable: true };
      }
      return data;
    } catch (error) {
      return { error: error.message || 'Connection failed', unavailable: true };
    }
  },

  dashboard: () => API.call('/dashboard'),
  alerts: () => API.call('/alerts'),
  alertDetails: (id) => API.call(`/alert-details/${encodeURIComponent(id)}`),
  rca: (id) => API.call(`/rca/${encodeURIComponent(id)}`),
  metrics: (host) => API.call('/metrics', { host }),
  logs: (host) => API.call('/logs', { host }),
  knowledge: () => API.call('/knowledge'),
  search: (query) => API.call('/search', { query }),
  servicenow: () => API.call('/servicenow'),
  analytics: () => API.call('/analytics'),
  systemStatus: () => API.call('/system-status')
};

const STATE = {
  activeView: 'dashboard',
  alerts: [],
  knowledge: [],
  metrics: [],
  logs: [],
  incidents: [],
  dashboard: null,
  rca: null,
  selectedAlert: null,
  alertDetails: null,
  analytics: null,
  systemStatus: null,
  lastUpdated: null,
  connected: true,
  loading: false,
  pollingInterval: Number(localStorage.getItem('nzcc_polling')) || (window.NZCC_CONFIG?.DEFAULT_POLLING_INTERVAL || 30),
  theme: localStorage.getItem('nzcc_theme') || (window.NZCC_CONFIG?.DEFAULT_THEME || 'dark'),
  demoMode: localStorage.getItem('nzcc_demo') === '1',
  notifications: localStorage.getItem('nzcc_notifications') !== '0',
  currentInvestigationMetrics: [],
  currentInvestigationLogs: [],
  currentInvestigationIncidents: [],
  chatHistory: [],
  sortAlerts: { key: 'createdAt', dir: 'desc' },
  searchQuery: ''
};

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function formatTimeFull(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(Number(seconds))) return '—';
  const s = Math.max(0, Math.floor(Number(seconds)));
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
}

function formatConfidence(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  const pct = n <= 1 ? Math.round(n * 100) : Math.round(n);
  return `${pct}%`;
}

function confidencePercent(value) {
  const n = Number(value) || 0;
  return n <= 1 ? Math.round(n * 100) : Math.round(n);
}

function severityClass(severity) {
  const s = String(severity || 'information').toLowerCase();
  if (s === 'critical') return 'critical';
  if (s === 'high') return 'high';
  if (s === 'average' || s === 'warning' || s === 'warning') return 'average';
  return 'information';
}

function getSeverityBadge(severity) {
  return `badge-${severityClass(severity)}`;
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value == null || value === '') return [];
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [String(value)];
    } catch {
      return [value];
    }
  }
  return [String(value)];
}

function isUnavailable(payload) {
  return !payload || payload.unavailable || payload.error;
}

function hasData(list) {
  return Array.isArray(list) && list.length > 0;
}

function setActiveView(viewName) {
  STATE.activeView = viewName;
  document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
  document.getElementById(`view-${viewName}`)?.classList.add('active');
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.view === viewName);
  });
  const title = window.NZCC_CONFIG?.PAGE_TITLES?.[viewName] || viewName;
  const titleEl = document.getElementById('page-title');
  if (titleEl) titleEl.textContent = title;
  updateStatusBar();
}

function updateStatusPill(message, status = 'live') {
  const pill = document.getElementById('backend-status');
  if (pill) {
    pill.textContent = message;
    pill.className = `status-pill ${status}`;
  }
  const sidebar = document.getElementById('sidebar-status');
  if (sidebar) sidebar.textContent = message;
  const dot = document.getElementById('sidebar-dot');
  if (dot) dot.className = `status-dot ${status === 'live' ? 'live' : status === 'warning' ? 'warning' : 'error'}`;
}

function updateLastUpdated() {
  STATE.lastUpdated = new Date().toISOString();
  const elem = document.getElementById('last-updated');
  if (elem) elem.textContent = `Updated ${formatTime(STATE.lastUpdated)}`;
}

function updateStatusBar() {
  const selected = document.getElementById('status-selected');
  if (selected) {
    selected.textContent = STATE.selectedAlert
      ? `${STATE.selectedAlert.host || 'Host'} · ${STATE.selectedAlert.problem || 'Investigation'}`
      : 'No investigation selected';
  }
  const counts = document.getElementById('status-counts');
  if (counts) {
    counts.textContent = `${STATE.alerts.length} alerts · ${STATE.knowledge.length} knowledge`;
  }
  const badge = document.getElementById('nav-alert-count');
  if (badge) {
    const critical = STATE.alerts.filter((a) => String(a.severity || '').toLowerCase() === 'critical').length;
    badge.textContent = String(STATE.alerts.length);
    badge.hidden = STATE.alerts.length === 0;
    if (critical > 0) badge.style.background = 'var(--critical-soft)';
  }
}

function setRefreshing(on) {
  const el = document.getElementById('refresh-indicator');
  if (el) el.classList.toggle('refreshing', !!on);
  const label = document.getElementById('refresh-label');
  if (label) label.textContent = on ? 'Syncing' : 'Live';
}

function showNotification(message, type = 'info', title = '') {
  if (!STATE.notifications && type !== 'error') return;
  const region = document.getElementById('toast-region');
  if (!region) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `${title ? `<strong>${escapeHtml(title)}</strong>` : ''}<span>${escapeHtml(message)}</span>`;
  region.appendChild(toast);
  const dot = document.getElementById('notify-dot');
  if (dot) dot.hidden = false;
  setTimeout(() => toast.remove(), 4200);
}

function showEmpty(message, title = 'No Data Available', icon = 'fa-inbox') {
  return `
    <div class="empty-state">
      <i class="fas ${icon}"></i>
      <h4>${escapeHtml(title)}</h4>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function showPlaceholder(title, message) {
  return `
    <div class="placeholder-banner">
      <i class="fas fa-hourglass-half"></i>
      <div>
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(message)}</span>
      </div>
    </div>
  `;
}

function showSkeletonGrid(count = 5) {
  return `<div class="kpi-grid">${Array.from({ length: count }).map(() => '<div class="skeleton-card"></div>').join('')}</div>`;
}

window.API = API;
window.STATE = STATE;
window.escapeHtml = escapeHtml;
window.formatTime = formatTime;
window.formatTimeFull = formatTimeFull;
window.formatDuration = formatDuration;
window.formatConfidence = formatConfidence;
window.confidencePercent = confidencePercent;
window.severityClass = severityClass;
window.getSeverityBadge = getSeverityBadge;
window.asArray = asArray;
window.isUnavailable = isUnavailable;
window.hasData = hasData;
window.setActiveView = setActiveView;
window.updateStatusPill = updateStatusPill;
window.updateLastUpdated = updateLastUpdated;
window.updateStatusBar = updateStatusBar;
window.setRefreshing = setRefreshing;
window.showNotification = showNotification;
window.showEmpty = showEmpty;
window.showPlaceholder = showPlaceholder;
window.showSkeletonGrid = showSkeletonGrid;
