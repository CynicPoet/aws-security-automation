DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Security Automation Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body { background: #0f172a; color: #e2e8f0; font-family: 'Inter', system-ui, sans-serif; }
  .glass { background: rgba(30,41,59,0.85); border: 1px solid rgba(100,116,139,0.25); backdrop-filter: blur(8px); }
  .badge-critical { background: #7f1d1d; color: #fca5a5; }
  .badge-high     { background: #7c2d12; color: #fdba74; }
  .badge-medium   { background: #713f12; color: #fde68a; }
  .badge-low      { background: #164e63; color: #67e8f9; }
  .badge-info     { background: #1e3a5f; color: #93c5fd; }
  .status-pending   { background: #312e81; color: #a5b4fc; }
  .status-approved  { background: #14532d; color: #86efac; }
  .status-rejected  { background: #450a0a; color: #fca5a5; }
  .status-resolved  { background: #14532d; color: #86efac; }
  .status-suppressed{ background: #1e293b; color: #94a3b8; }
  .status-auto      { background: #0c4a6e; color: #7dd3fc; }
  .status-failed    { background: #450a0a; color: #fca5a5; }
  .status-manual    { background: #3b1f6e; color: #d8b4fe; }
  .row-hover:hover { background: rgba(51,65,85,0.5); cursor: pointer; }
  .tab-active { border-bottom: 2px solid #6366f1; color: #a5b4fc; }
  .tab-inactive { color: #94a3b8; border-bottom: 2px solid transparent; }
  .tab-inactive:hover { color: #cbd5e1; }
  .toggle-on  { background: #4f46e5; }
  .toggle-off { background: #374151; }
  .btn-approve { background: #166534; color: #bbf7d0; }
  .btn-approve:hover { background: #15803d; }
  .btn-reject  { background: #7f1d1d; color: #fecaca; }
  .btn-reject:hover  { background: #991b1b; }
  .btn-manual  { background: #3b0764; color: #e9d5ff; }
  .btn-manual:hover  { background: #4c1d95; }
  .modal-overlay { background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); }
  pre { white-space: pre-wrap; word-break: break-all; }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #1e293b; }
  ::-webkit-scrollbar-thumb { background: #475569; border-radius: 3px; }
  .pulse { animation: pulse 2s cubic-bezier(0.4,0,0.6,1) infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
  .spin { animation: spin 1s linear infinite; }
  @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
</style>
</head>
<body class="min-h-screen">

<!-- HEADER -->
<header class="glass sticky top-0 z-40 px-6 py-4 flex items-center justify-between border-b border-slate-700">
  <div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-lg">&#x1F6E1;</div>
    <div>
      <h1 class="font-bold text-lg text-white leading-none">Security Automation</h1>
      <p class="text-xs text-slate-400 leading-none mt-0.5">AI-powered threat detection &amp; remediation</p>
    </div>
  </div>
  <div class="flex items-center gap-6">
    <!-- Last updated -->
    <span class="text-xs text-slate-500" id="last-updated">Loading...</span>
    <!-- Email toggle -->
    <div class="flex items-center gap-2">
      <span class="text-sm text-slate-400">Email alerts</span>
      <button id="email-toggle" onclick="toggleEmail()" class="relative w-11 h-6 rounded-full transition-colors toggle-off" title="Toggle email notifications">
        <span id="toggle-knob" class="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"></span>
      </button>
    </div>
    <!-- Refresh button -->
    <button onclick="loadAll()" class="glass px-3 py-1.5 rounded-lg text-sm text-slate-300 hover:text-white hover:border-slate-500 transition-colors flex items-center gap-1.5">
      <span id="refresh-icon">&#8635;</span> Refresh
    </button>
  </div>
</header>

<!-- MAIN -->
<main class="max-w-7xl mx-auto px-6 py-6">

  <!-- STATS ROW -->
  <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
    <div class="glass rounded-xl p-4">
      <p class="text-xs text-slate-400 uppercase tracking-wide">Total</p>
      <p class="text-3xl font-bold text-white mt-1" id="stat-total">-</p>
    </div>
    <div class="glass rounded-xl p-4">
      <p class="text-xs text-orange-400 uppercase tracking-wide">Pending Approval</p>
      <p class="text-3xl font-bold text-orange-300 mt-1" id="stat-pending">-</p>
    </div>
    <div class="glass rounded-xl p-4">
      <p class="text-xs text-blue-400 uppercase tracking-wide">Auto-Remediated</p>
      <p class="text-3xl font-bold text-blue-300 mt-1" id="stat-auto">-</p>
    </div>
    <div class="glass rounded-xl p-4">
      <p class="text-xs text-green-400 uppercase tracking-wide">Resolved</p>
      <p class="text-3xl font-bold text-green-300 mt-1" id="stat-resolved">-</p>
    </div>
    <div class="glass rounded-xl p-4">
      <p class="text-xs text-slate-400 uppercase tracking-wide">Suppressed (FP)</p>
      <p class="text-3xl font-bold text-slate-300 mt-1" id="stat-suppressed">-</p>
    </div>
  </div>

  <!-- FILTER TABS -->
  <div class="flex gap-1 mb-4 border-b border-slate-700">
    <button onclick="setTab('all')"           id="tab-all"           class="px-4 py-2 text-sm font-medium tab-active transition-colors">All</button>
    <button onclick="setTab('pending')"       id="tab-pending"       class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Pending</button>
    <button onclick="setTab('auto')"          id="tab-auto"          class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Auto-Remediated</button>
    <button onclick="setTab('resolved')"      id="tab-resolved"      class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Resolved</button>
    <button onclick="setTab('suppressed')"    id="tab-suppressed"    class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Suppressed</button>
  </div>

  <!-- FINDINGS TABLE -->
  <div class="glass rounded-xl overflow-hidden">
    <div id="loading" class="flex items-center justify-center py-16 text-slate-400">
      <svg class="spin w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
      Loading findings...
    </div>
    <div id="empty" class="hidden flex items-center justify-center py-16 text-slate-500">
      <div class="text-center">
        <div class="text-4xl mb-3">&#x1F4CB;</div>
        <p class="font-medium">No findings in this category</p>
        <p class="text-sm mt-1">Deploy simulation resources to generate findings</p>
      </div>
    </div>
    <table id="findings-table" class="hidden w-full text-sm">
      <thead>
        <tr class="border-b border-slate-700 text-left">
          <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-24">Severity</th>
          <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Resource</th>
          <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Finding</th>
          <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-28">Status</th>
          <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-36">Time</th>
          <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-56">Actions</th>
        </tr>
      </thead>
      <tbody id="findings-body">
      </tbody>
    </table>
  </div>

  <!-- AUTO-REFRESH INDICATOR -->
  <div class="flex items-center justify-end mt-3 gap-2 text-xs text-slate-500">
    <span class="pulse w-1.5 h-1.5 rounded-full bg-green-500 inline-block"></span>
    Auto-refreshes every 30 seconds
  </div>
</main>

<!-- FINDING DETAIL MODAL -->
<div id="modal" class="hidden fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4" onclick="closeModal(event)">
  <div class="glass rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto" onclick="event.stopPropagation()">
    <div class="flex items-start justify-between p-6 border-b border-slate-700">
      <div>
        <p id="modal-severity" class="text-xs font-semibold uppercase tracking-widest mb-1"></p>
        <h2 id="modal-title" class="text-lg font-bold text-white"></h2>
        <p id="modal-resource" class="text-sm text-slate-400 mt-1"></p>
      </div>
      <button onclick="closeModal()" class="text-slate-400 hover:text-white p-1 rounded transition-colors">&#10005;</button>
    </div>
    <div class="p-6 space-y-4">
      <div>
        <p class="text-xs text-slate-400 uppercase tracking-wide mb-2">Finding Description</p>
        <p id="modal-description" class="text-sm text-slate-200 leading-relaxed"></p>
      </div>
      <div>
        <p class="text-xs text-indigo-400 uppercase tracking-wide mb-2">&#x1F916; AI Analysis</p>
        <div class="bg-slate-900 rounded-lg p-4">
          <p id="modal-analysis" class="text-sm text-slate-200 leading-relaxed"></p>
        </div>
      </div>
      <div id="modal-actions-section">
        <p class="text-xs text-slate-400 uppercase tracking-wide mb-2">Recommended Actions</p>
        <div id="modal-actions-list" class="space-y-2"></div>
      </div>
      <div id="modal-approval-section" class="hidden">
        <p class="text-xs text-orange-400 uppercase tracking-wide mb-3">&#x26A0;&#xFE0F; Admin Decision Required</p>
        <div id="modal-approve-buttons" class="space-y-2"></div>
        <div class="flex gap-2 mt-3">
          <button onclick="doAction('reject')" class="btn-reject flex-1 py-2 rounded-lg text-sm font-medium transition-colors">Reject (False Positive)</button>
          <button onclick="doAction('manual')" class="btn-manual flex-1 py-2 rounded-lg text-sm font-medium transition-colors">I'll Fix Manually</button>
        </div>
      </div>
      <div class="pt-2 border-t border-slate-700 text-xs text-slate-500 flex justify-between">
        <span>Finding ID: <code id="modal-id" class="text-slate-300"></code></span>
        <span id="modal-time"></span>
      </div>
    </div>
  </div>
</div>

<script>
// ── STATE ──────────────────────────────────────────────────────────────────────
let allFindings = [];
let currentTab = 'all';
let currentFinding = null;
let emailEnabled = false;

// Detect API base URL from current page URL
const API_BASE = window.location.origin + (window.location.pathname.startsWith('/prod') ? '/prod' : '');

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadAll();
  setInterval(loadAll, 30000);
});

async function loadAll() {
  document.getElementById('refresh-icon').innerHTML = '<svg class="spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>';
  await Promise.all([loadFindings(), loadSettings()]);
  document.getElementById('refresh-icon').innerHTML = '&#8635;';
  document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// ── FINDINGS ───────────────────────────────────────────────────────────────────
async function loadFindings() {
  try {
    const res = await fetch(API_BASE + '/dashboard/api/findings');
    const data = await res.json();
    allFindings = data.findings || [];
    updateStats();
    renderTable();
  } catch (e) {
    console.error('Failed to load findings:', e);
  }
}

function updateStats() {
  const counts = { total: allFindings.length, pending: 0, auto: 0, resolved: 0, suppressed: 0 };
  allFindings.forEach(f => {
    const s = (f.status || '').toLowerCase();
    if (s === 'pending_approval') counts.pending++;
    else if (s === 'auto_remediated') counts.auto++;
    else if (['resolved', 'approved'].includes(s)) counts.resolved++;
    else if (['suppressed', 'false_positive'].includes(s)) counts.suppressed++;
  });
  document.getElementById('stat-total').textContent     = counts.total;
  document.getElementById('stat-pending').textContent   = counts.pending;
  document.getElementById('stat-auto').textContent      = counts.auto;
  document.getElementById('stat-resolved').textContent  = counts.resolved;
  document.getElementById('stat-suppressed').textContent= counts.suppressed;
}

function filteredFindings() {
  if (currentTab === 'all') return allFindings;
  const STATUS_MAP = {
    pending:    ['pending_approval'],
    auto:       ['auto_remediated'],
    resolved:   ['resolved', 'approved'],
    suppressed: ['suppressed', 'false_positive', 'rejected'],
  };
  const allowed = STATUS_MAP[currentTab] || [];
  return allFindings.filter(f => allowed.includes((f.status || '').toLowerCase()));
}

function renderTable() {
  const findings = filteredFindings();
  const loading = document.getElementById('loading');
  const empty   = document.getElementById('empty');
  const table   = document.getElementById('findings-table');
  const tbody   = document.getElementById('findings-body');

  loading.classList.add('hidden');

  if (findings.length === 0) {
    empty.classList.remove('hidden');
    table.classList.add('hidden');
    return;
  }

  empty.classList.add('hidden');
  table.classList.remove('hidden');

  tbody.innerHTML = findings.map(f => `
    <tr class="border-b border-slate-800 row-hover transition-colors" onclick="openModal('${escHtml(f.finding_id)}')">
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded text-xs font-semibold ${severityClass(f.severity)}">${escHtml(f.severity||'N/A')}</span></td>
      <td class="px-4 py-3">
        <p class="text-xs text-slate-400">${escHtml(f.resource_type||'')}</p>
        <p class="font-mono text-xs text-slate-200 truncate max-w-xs" title="${escHtml(f.resource_id||'')}">${escHtml(f.resource_id||'')}</p>
      </td>
      <td class="px-4 py-3">
        <p class="text-slate-200 font-medium text-sm">${escHtml(f.title||f.finding_id||'')}</p>
        <p class="text-slate-400 text-xs mt-0.5 truncate max-w-sm">${escHtml(f.description||'')}</p>
      </td>
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded text-xs font-semibold ${statusClass(f.status)}">${statusLabel(f.status)}</span></td>
      <td class="px-4 py-3 text-xs text-slate-400">${formatTime(f.created_at)}</td>
      <td class="px-4 py-3" onclick="event.stopPropagation()">
        ${actionButtons(f)}
      </td>
    </tr>
  `).join('');
}

function actionButtons(f) {
  if ((f.status||'').toLowerCase() !== 'pending_approval') {
    return '<span class="text-xs text-slate-600">No action needed</span>';
  }
  const actions = safeParseJSON(f.recommended_actions, []);
  let btns = actions.slice(0, 2).map(a =>
    `<button onclick="quickApprove('${escHtml(f.finding_id)}',${a.action_id})" class="btn-approve px-2 py-1 rounded text-xs font-medium transition-colors whitespace-nowrap">${escHtml(a.description||'Approve')}</button>`
  ).join('');
  btns += `<button onclick="quickReject('${escHtml(f.finding_id)}')" class="btn-reject px-2 py-1 rounded text-xs font-medium transition-colors">Reject</button>`;
  return `<div class="flex flex-wrap gap-1">${btns}</div>`;
}

// ── SETTINGS ───────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const res = await fetch(API_BASE + '/dashboard/api/settings');
    const data = await res.json();
    emailEnabled = data.value === 'true';
    updateToggleUI();
  } catch (e) {}
}

function updateToggleUI() {
  const btn  = document.getElementById('email-toggle');
  const knob = document.getElementById('toggle-knob');
  if (emailEnabled) {
    btn.classList.remove('toggle-off');  btn.classList.add('toggle-on');
    knob.style.transform = 'translateX(20px)';
  } else {
    btn.classList.remove('toggle-on');   btn.classList.add('toggle-off');
    knob.style.transform = 'translateX(0)';
  }
}

async function toggleEmail() {
  emailEnabled = !emailEnabled;
  updateToggleUI();
  try {
    await fetch(API_BASE + '/dashboard/api/settings', {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email_notifications: emailEnabled}),
    });
  } catch (e) { emailEnabled = !emailEnabled; updateToggleUI(); }
}

// ── TABS ───────────────────────────────────────────────────────────────────────
function setTab(tab) {
  currentTab = tab;
  ['all','pending','auto','resolved','suppressed'].forEach(t => {
    const el = document.getElementById('tab-' + t);
    el.classList.toggle('tab-active', t === tab);
    el.classList.toggle('tab-inactive', t !== tab);
  });
  renderTable();
}

// ── MODAL ──────────────────────────────────────────────────────────────────────
function openModal(findingId) {
  const f = allFindings.find(x => x.finding_id === findingId);
  if (!f) return;
  currentFinding = f;

  document.getElementById('modal-severity').textContent  = f.severity || '';
  document.getElementById('modal-severity').className    = 'text-xs font-semibold uppercase tracking-widest mb-1 ' + severityText(f.severity);
  document.getElementById('modal-title').textContent     = f.title || f.finding_id;
  document.getElementById('modal-resource').textContent  = (f.resource_type||'') + ' — ' + (f.resource_id||'');
  document.getElementById('modal-description').textContent = f.description || 'No description available.';
  document.getElementById('modal-id').textContent        = f.finding_id;
  document.getElementById('modal-time').textContent      = formatTime(f.created_at);

  // AI Analysis
  const ai = safeParseJSON(f.ai_analysis, {});
  document.getElementById('modal-analysis').textContent  = ai.analysis || f.ai_analysis || 'No AI analysis available.';

  // Recommended actions
  const actions = safeParseJSON(f.recommended_actions, []);
  document.getElementById('modal-actions-list').innerHTML = actions.map(a =>
    `<div class="flex items-start gap-2 text-sm">
      <span class="mt-0.5 w-5 h-5 rounded-full bg-slate-700 flex-shrink-0 flex items-center justify-center text-xs text-slate-300">${a.action_id||'?'}</span>
      <span class="text-slate-200">${escHtml(a.description||'')}</span>
    </div>`
  ).join('') || '<p class="text-sm text-slate-500">No specific actions listed.</p>';

  // Approval buttons
  const approvalSection = document.getElementById('modal-approval-section');
  if ((f.status||'').toLowerCase() === 'pending_approval') {
    approvalSection.classList.remove('hidden');
    document.getElementById('modal-approve-buttons').innerHTML = actions.map(a =>
      `<button onclick="doAction('approve', ${a.action_id})" class="btn-approve w-full py-2 rounded-lg text-sm font-medium transition-colors text-left px-4">
        &#x2713; Approve: ${escHtml(a.description||'Action ' + a.action_id)}
      </button>`
    ).join('');
  } else {
    approvalSection.classList.add('hidden');
  }

  document.getElementById('modal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal(event) {
  if (event && event.target !== document.getElementById('modal')) return;
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow = '';
  currentFinding = null;
}

// ── ACTIONS ────────────────────────────────────────────────────────────────────
async function doAction(action, actionId) {
  if (!currentFinding) return;
  await submitAction(currentFinding.finding_id, action, actionId);
  closeModal();
}

async function quickApprove(findingId, actionId) {
  await submitAction(findingId, 'approve', actionId);
}

async function quickReject(findingId) {
  await submitAction(findingId, 'reject', null);
}

async function submitAction(findingId, action, actionId) {
  try {
    const body = {action};
    if (actionId !== undefined && actionId !== null) body.action_id = actionId;
    const res = await fetch(`${API_BASE}/dashboard/api/findings/${encodeURIComponent(findingId)}/action`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Action submitted: ' + action, 'success');
      await loadFindings();
    } else {
      showToast(data.error || 'Action failed', 'error');
    }
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
  }
}

// ── TOAST ──────────────────────────────────────────────────────────────────────
function showToast(message, type) {
  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-green-900 border-green-700 text-green-200' : 'bg-red-900 border-red-700 text-red-200';
  toast.className = `fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg border text-sm font-medium shadow-xl ${bg} transition-opacity`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 500); }, 3500);
}

// ── UTILS ──────────────────────────────────────────────────────────────────────
function severityClass(s) {
  const map = {CRITICAL:'badge-critical', HIGH:'badge-high', MEDIUM:'badge-medium', LOW:'badge-low', INFORMATIONAL:'badge-info'};
  return map[(s||'').toUpperCase()] || 'badge-info';
}
function severityText(s) {
  const map = {CRITICAL:'text-red-400', HIGH:'text-orange-400', MEDIUM:'text-yellow-400', LOW:'text-cyan-400'};
  return map[(s||'').toUpperCase()] || 'text-slate-400';
}
function statusClass(s) {
  const map = {PENDING_APPROVAL:'status-pending', AUTO_REMEDIATED:'status-auto', RESOLVED:'status-resolved',
    APPROVED:'status-approved', REJECTED:'status-rejected', SUPPRESSED:'status-suppressed',
    FALSE_POSITIVE:'status-suppressed', FAILED:'status-failed', MANUAL_REVIEW:'status-manual'};
  return map[(s||'').toUpperCase()] || 'status-suppressed';
}
function statusLabel(s) {
  const map = {PENDING_APPROVAL:'Pending', AUTO_REMEDIATED:'Auto-Fixed', RESOLVED:'Resolved',
    APPROVED:'Approved', REJECTED:'Rejected', SUPPRESSED:'Suppressed (FP)',
    FALSE_POSITIVE:'False Positive', FAILED:'Failed', MANUAL_REVIEW:'Manual Review'};
  return map[(s||'').toUpperCase()] || (s||'Unknown');
}
function formatTime(iso) {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    const diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 60) return diff + 's ago';
    if (diff < 3600) return Math.floor(diff/60) + 'm ago';
    if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
    return d.toLocaleDateString();
  } catch { return iso; }
}
function safeParseJSON(val, fallback) {
  if (!val) return fallback;
  if (typeof val === 'object') return val;
  try { return JSON.parse(val); } catch { return fallback; }
}
function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>"""
