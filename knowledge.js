/* =========================================================
   NZCC — Knowledge Repository
   ========================================================= */

async function renderKnowledge() {
  const view = document.getElementById('view-knowledge');
  if (!view) return;

  view.innerHTML = `
    <div class="page-header">
      <div>
        <h1>Knowledge Repository</h1>
        <p class="muted">Stored investigations powering historical incident intelligence</p>
      </div>
      <button id="refresh-knowledge" class="btn-secondary" type="button"><i class="fas fa-sync-alt"></i> Refresh</button>
    </div>

    <div class="card">
      <div class="card-header">
        <div><h3>Indexed Investigations</h3><span class="muted" id="knowledge-count"></span></div>
        <div class="filters-compact">
          <input type="search" id="knowledge-search" placeholder="Search problem or root cause…" />
          <select id="knowledge-tech"><option value="">All Technologies</option></select>
          <select id="knowledge-severity"><option value="">All Severities</option></select>
          <input type="date" id="knowledge-date" />
          <select id="knowledge-confidence">
            <option value="">All Confidence</option>
            <option value="0.7">70%+</option>
            <option value="0.85">85%+</option>
            <option value="0.95">95%+</option>
          </select>
        </div>
      </div>
      <div class="table-wrapper">
        <table id="knowledge-table">
          <thead>
            <tr>
              <th>Problem</th>
              <th>Technology</th>
              <th>Severity</th>
              <th>Root Cause</th>
              <th>Occurrences</th>
              <th>Similarity</th>
              <th>Confidence</th>
              <th>Last Seen</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="knowledge-empty"></div>
    </div>
  `;

  const techs = [...new Set(STATE.knowledge.map((k) => k.technology).filter(Boolean))].sort();
  const sevs = [...new Set(STATE.knowledge.map((k) => k.severity).filter(Boolean))].sort();
  document.getElementById('knowledge-tech').innerHTML = '<option value="">All Technologies</option>' +
    techs.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
  document.getElementById('knowledge-severity').innerHTML = '<option value="">All Severities</option>' +
    sevs.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');

  ['knowledge-search', 'knowledge-tech', 'knowledge-severity', 'knowledge-date', 'knowledge-confidence'].forEach((id) => {
    const el = document.getElementById(id);
    el?.addEventListener('input', paintKnowledge);
    el?.addEventListener('change', paintKnowledge);
  });

  paintKnowledge();
  bindRefreshButtons();
}

function paintKnowledge() {
  const tbody = document.querySelector('#knowledge-table tbody');
  const empty = document.getElementById('knowledge-empty');
  const count = document.getElementById('knowledge-count');
  if (!tbody) return;

  if (!hasData(STATE.knowledge)) {
    tbody.innerHTML = '';
    if (empty) {
      empty.innerHTML = showEmpty(
        'Knowledge Repository connected. Waiting for indexed investigations.',
        'Waiting for Indexed Investigations',
        'fa-book-open'
      );
    }
    if (count) count.textContent = '0 entries';
    return;
  }

  const search = (document.getElementById('knowledge-search')?.value || '').toLowerCase();
  const tech = document.getElementById('knowledge-tech')?.value || '';
  const sev = document.getElementById('knowledge-severity')?.value || '';
  const date = document.getElementById('knowledge-date')?.value || '';
  const confMin = Number(document.getElementById('knowledge-confidence')?.value || 0);

  const filtered = STATE.knowledge.filter((k) => {
    const blob = `${k.problem || ''} ${k.rootCause || ''} ${k.host || ''}`.toLowerCase();
    const matchSearch = !search || blob.includes(search);
    const matchTech = !tech || k.technology === tech;
    const matchSev = !sev || k.severity === sev;
    const matchConf = !confMin || Number(k.confidence || 0) >= confMin;
    let matchDate = true;
    if (date && k.lastSeen) {
      matchDate = String(k.lastSeen).slice(0, 10) === date;
    } else if (date) {
      matchDate = false;
    }
    return matchSearch && matchTech && matchSev && matchConf && matchDate;
  });

  if (count) count.textContent = `${filtered.length} of ${STATE.knowledge.length} entries`;

  if (!filtered.length) {
    tbody.innerHTML = '';
    if (empty) empty.innerHTML = showEmpty('Try adjusting filters to find stored investigations.', 'No Matching Entries', 'fa-filter');
    return;
  }

  if (empty) empty.innerHTML = '';
  tbody.innerHTML = filtered.map((item) => {
    const conf = confidencePercent(item.confidence);
    return `
      <tr data-problem="${escapeHtml(item.problem || '')}" data-host="${escapeHtml(item.host || '')}">
        <td>${escapeHtml(item.problem || '—')}</td>
        <td>${escapeHtml(item.technology || '—')}</td>
        <td>${UI.createBadge(item.severity || 'Information', severityClass(item.severity))}</td>
        <td>${escapeHtml(item.rootCause || '—')}</td>
        <td>${escapeHtml(String(item.occurrences || 1))}</td>
        <td>${conf}%</td>
        <td>
          <div class="progress-bar" style="height:6px;margin:0 0 4px;min-width:80px">
            <div class="progress-fill" style="width:${conf}%"></div>
          </div>
          ${conf}%
        </td>
        <td>${escapeHtml(formatTime(item.lastSeen))}</td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('tr').forEach((tr) => {
    tr.addEventListener('click', async () => {
      const problem = tr.dataset.problem;
      const host = tr.dataset.host;
      const match = STATE.alerts.find((a) => a.problem === problem && (!host || a.host === host))
        || STATE.alerts.find((a) => a.problem === problem)
        || STATE.alerts.find((a) => a.host === host);
      if (match) {
        await selectAlert(match.problemId, { view: 'rca' });
      } else {
        // Synthesize selection from knowledge for RCA view
        const k = STATE.knowledge.find((x) => x.problem === problem && x.host === host) || STATE.knowledge.find((x) => x.problem === problem);
        if (!k) return;
        STATE.selectedAlert = {
          problemId: String(k.problem || problem),
          problem: k.problem,
          host: k.host,
          technology: k.technology,
          severity: k.severity,
          trigger: '—',
          status: 'Open',
          incidentNumber: '—',
          createdAt: k.lastSeen
        };
        STATE.rca = {
          rootCause: k.rootCause,
          confidence: k.confidence,
          impact: 'Retrieved from Knowledge Repository',
          reasoning: [],
          recommendedResolution: [],
          nextDiagnostics: []
        };
        setActiveView('rca');
        await renderCurrentView();
        showNotification('Opened investigation from Knowledge Repository', 'success', 'Knowledge');
      }
    });
  });
}

window.renderKnowledge = renderKnowledge;
