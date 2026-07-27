/* =========================================================
   NZCC — Analytics
   ========================================================= */

async function renderAnalytics() {
  const view = document.getElementById('view-analytics');
  if (!view) return;

  const a = STATE.analytics;
  const d = STATE.dashboard;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Analytics</h1>
        <p class="muted">Executive reporting across investigation performance and learning</p>
      </div>
      <button id="refresh-analytics" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
    </div>

    <div id="analytics-kpi" class="kpi-grid"></div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><h3>Alert Distribution Trend</h3></div>
        <div id="analytics-trend" class="chart-container"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Technology Distribution</h3></div>
        <div id="analytics-tech"></div>
      </div>
    </div>

    <div class="grid-row two-col">
      <div class="card">
        <div class="card-header"><h3>Most Common Root Causes</h3></div>
        <div id="analytics-causes"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Most Frequent Technologies</h3></div>
        <div id="analytics-freq"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3>Monthly Report Snapshot</h3><span class="muted">Feature planned for expanded reporting APIs</span></div>
      ${showPlaceholder('Coming Soon', 'Monthly executive PDF reports will be available as analytics exports come online.')}
      <div class="pulse-list" style="margin-top:12px">
        <div class="pulse-item"><span>Historical RCA Reuse</span><strong>${escapeHtml(String(d?.historicalReuse != null ? d.historicalReuse + '%' : '—'))}</strong></div>
        <div class="pulse-item"><span>Knowledge Growth</span><strong>${escapeHtml(a?.knowledgeGrowth || d?.knowledgeGrowth || '—')}</strong></div>
        <div class="pulse-item"><span>Average RCA Time</span><strong>${escapeHtml(a?.avgRcaTime || d?.avgRcaTime || '—')}</strong></div>
        <div class="pulse-item"><span>Average Resolution Time</span><strong>${escapeHtml(a?.avgResolutionTime || '—')}</strong></div>
      </div>
    </div>
  `;

  if (!a || isUnavailable(a)) {
    document.getElementById('analytics-kpi').innerHTML =
      showPlaceholder('Waiting for Backend', 'Analytics KPIs will populate when reporting endpoints return data.');
  } else {
    document.getElementById('analytics-kpi').innerHTML = [
      UI.createKpiCard(a.avgRcaTime || '—', 'Average RCA Time'),
      UI.createKpiCard(a.avgResolutionTime || '—', 'Average Resolution Time'),
      UI.createKpiCard(d?.historicalReuse != null ? `${d.historicalReuse}%` : '—', 'Historical RCA Reuse', '', 'success'),
      UI.createKpiCard(a.knowledgeGrowth || '—', 'Knowledge Growth', '', 'info'),
      UI.createKpiCard(a.mostCommonTechnologies || '—', 'Top Technologies')
    ].join('');
  }

  UI.renderChart('analytics-trend', 'trend', d?.alertTrend || []);
  UI.renderChart('analytics-tech', 'bar', d?.technologyDistribution || []);

  const causes = (a?.topRootCauses || STATE.knowledge.map((k) => k.rootCause).filter(Boolean)).slice(0, 6);
  document.getElementById('analytics-causes').innerHTML = causes.length
    ? `<div class="activity-list">${causes.map((c, i) => `
        <div class="activity-item" style="cursor:default">
          <div class="activity-icon">${i + 1}</div>
          <div class="activity-body"><strong>${escapeHtml(String(c))}</strong><span>Observed root cause</span></div>
        </div>`).join('')}</div>`
    : showEmpty('Root cause rankings appear as investigations accumulate.', 'No Root Cause Data', 'fa-lightbulb');

  const techCounts = {};
  STATE.knowledge.forEach((k) => {
    if (!k.technology) return;
    techCounts[k.technology] = (techCounts[k.technology] || 0) + 1;
  });
  const ranked = Object.entries(techCounts).sort((x, y) => y[1] - x[1]).slice(0, 6);
  const max = ranked[0]?.[1] || 1;
  document.getElementById('analytics-freq').innerHTML = ranked.length
    ? `<div class="host-rank">${ranked.map(([tech, count]) => `
        <div class="host-rank-item">
          <span class="host-rank-name">${escapeHtml(tech)}</span>
          <div class="host-rank-bar"><div class="host-rank-fill" style="width:${Math.round((count / max) * 100)}%"></div></div>
          <span class="host-rank-count">${count}</span>
        </div>`).join('')}</div>`
    : showEmpty('Technology frequency will appear from the knowledge repository.', 'No Technology Data', 'fa-layer-group');

  bindRefreshButtons();
}

window.renderAnalytics = renderAnalytics;
