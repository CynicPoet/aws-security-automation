DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Security Automation Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body{background:#0f172a;color:#e2e8f0;font-family:system-ui,sans-serif}
  .glass{background:rgba(30,41,59,.85);border:1px solid rgba(100,116,139,.25);backdrop-filter:blur(8px)}
  .badge-critical{background:#7f1d1d;color:#fca5a5}.badge-high{background:#7c2d12;color:#fdba74}
  .badge-medium{background:#713f12;color:#fde68a}.badge-low{background:#164e63;color:#67e8f9}
  .badge-info{background:#1e3a5f;color:#93c5fd}
  .s-pending{background:#312e81;color:#a5b4fc}.s-approved{background:#14532d;color:#86efac}
  .s-rejected{background:#450a0a;color:#fca5a5}.s-resolved{background:#14532d;color:#86efac}
  .s-auto{background:#0c4a6e;color:#7dd3fc}.s-failed{background:#450a0a;color:#fca5a5}
  .s-manual{background:#3b1f6e;color:#d8b4fe}.s-suppressed{background:#1e293b;color:#94a3b8}
  .row-hover:hover{background:rgba(51,65,85,.5);cursor:pointer}
  .tab-active{border-bottom:2px solid #6366f1;color:#a5b4fc}
  .tab-inactive{color:#94a3b8;border-bottom:2px solid transparent}
  .tab-inactive:hover{color:#cbd5e1}
  .btn-approve{background:#166534;color:#bbf7d0}.btn-approve:hover{background:#15803d}
  .btn-reject{background:#7f1d1d;color:#fecaca}.btn-reject:hover{background:#991b1b}
  .btn-manual{background:#3b0764;color:#e9d5ff}.btn-manual:hover{background:#4c1d95}
  .btn-sim-a{background:#0c4a6e;color:#7dd3fc;border:1px solid #0369a1}
  .btn-sim-a:hover{background:#0369a1}
  .btn-sim-b{background:#4c1d95;color:#ddd6fe;border:1px solid #7c3aed}
  .btn-sim-b:hover{background:#6d28d9}
  .btn-danger{background:#7f1d1d;color:#fca5a5;border:1px solid #991b1b}
  .btn-danger:hover{background:#991b1b}
  .btn-safe{background:#14532d;color:#86efac;border:1px solid #15803d}
  .btn-safe:hover{background:#15803d}
  .modal-overlay{background:rgba(0,0,0,.7);backdrop-filter:blur(4px)}
  .pulse{animation:pulse 2s cubic-bezier(.4,0,.6,1) infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
  .spin{animation:spin 1s linear infinite}
  @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
  pre{white-space:pre-wrap;word-break:break-all}
  ::-webkit-scrollbar{width:6px;height:6px}
  ::-webkit-scrollbar-track{background:#1e293b}
  ::-webkit-scrollbar-thumb{background:#475569;border-radius:3px}
</style>
</head>
<body class="min-h-screen">

<!-- HEADER -->
<header class="glass sticky top-0 z-40 px-6 py-3 flex items-center justify-between border-b border-slate-700">
  <div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-lg">&#x1F6E1;</div>
    <div>
      <h1 class="font-bold text-base text-white leading-none">Security Automation</h1>
      <p class="text-xs text-slate-400 leading-none mt-0.5">AI-powered threat detection &amp; remediation</p>
    </div>
  </div>
  <div class="flex items-center gap-4">
    <span class="text-xs text-slate-500" id="last-updated">Loading...</span>
    <!-- Pipeline status + control -->
    <div class="flex items-center gap-2">
      <span id="pipeline-dot" class="w-2 h-2 rounded-full bg-slate-500"></span>
      <span id="pipeline-label" class="text-xs text-slate-400">Pipeline</span>
      <button id="pipeline-btn" onclick="togglePipeline()" class="text-xs px-2 py-1 rounded glass border border-slate-600 hover:border-slate-400 transition-colors"></button>
    </div>
    <!-- Email toggle -->
    <div class="flex items-center gap-2">
      <span class="text-xs text-slate-400">Email</span>
      <button id="email-toggle" onclick="toggleEmail()" class="relative w-10 h-5 rounded-full transition-colors bg-slate-700" title="Toggle email alerts">
        <span id="toggle-knob" class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform"></span>
      </button>
    </div>
    <button onclick="loadAll()" class="glass px-3 py-1.5 rounded-lg text-xs text-slate-300 hover:text-white border border-transparent hover:border-slate-500 transition-colors flex items-center gap-1">
      <span id="refresh-icon">&#8635;</span> Refresh
    </button>
  </div>
</header>

<main class="max-w-7xl mx-auto px-6 py-5">

  <!-- STATS -->
  <div class="grid grid-cols-5 gap-3 mb-5">
    <div class="glass rounded-xl p-4"><p class="text-xs text-slate-400 uppercase tracking-wide">Total</p><p class="text-2xl font-bold text-white mt-1" id="stat-total">-</p></div>
    <div class="glass rounded-xl p-4"><p class="text-xs text-orange-400 uppercase tracking-wide">Pending</p><p class="text-2xl font-bold text-orange-300 mt-1" id="stat-pending">-</p></div>
    <div class="glass rounded-xl p-4"><p class="text-xs text-blue-400 uppercase tracking-wide">Auto-Fixed</p><p class="text-2xl font-bold text-blue-300 mt-1" id="stat-auto">-</p></div>
    <div class="glass rounded-xl p-4"><p class="text-xs text-green-400 uppercase tracking-wide">Resolved</p><p class="text-2xl font-bold text-green-300 mt-1" id="stat-resolved">-</p></div>
    <div class="glass rounded-xl p-4"><p class="text-xs text-slate-400 uppercase tracking-wide">Suppressed</p><p class="text-2xl font-bold text-slate-300 mt-1" id="stat-suppressed">-</p></div>
  </div>

  <!-- SIMULATION LAB -->
  <div class="glass rounded-xl p-5 mb-5">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="font-semibold text-white text-sm">&#x1F9EA; Simulation Lab</h2>
        <p class="text-xs text-slate-400 mt-0.5">Trigger real misconfigurations — watch the system detect &amp; remediate</p>
      </div>
      <div id="sim-status" class="hidden text-xs px-3 py-1.5 rounded-lg glass border border-indigo-500 text-indigo-300"></div>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <!-- Category A -->
      <div>
        <p class="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">Category A — Auto Remediated</p>
        <div class="space-y-2">
          <div class="glass rounded-lg p-3 flex items-center justify-between">
            <div><p class="text-xs font-medium text-slate-200">A1: S3 Bucket — Public Access</p><p class="text-xs text-slate-500 mt-0.5">HIGH · Auto-fixed: block public access</p></div>
            <button onclick="runSim('A1')" class="btn-sim-a text-xs px-3 py-1.5 rounded-lg font-medium transition-colors">Run</button>
          </div>
          <div class="glass rounded-lg p-3 flex items-center justify-between">
            <div><p class="text-xs font-medium text-slate-200">A2: Security Group — SSH Open</p><p class="text-xs text-slate-500 mt-0.5">HIGH · Auto-fixed: revoke port 22</p></div>
            <button onclick="runSim('A2')" class="btn-sim-a text-xs px-3 py-1.5 rounded-lg font-medium transition-colors">Run</button>
          </div>
          <div class="glass rounded-lg p-3 flex items-center justify-between">
            <div><p class="text-xs font-medium text-slate-200">A3: Security Group — All Traffic</p><p class="text-xs text-slate-500 mt-0.5">CRITICAL · Auto-fixed: revoke all rules</p></div>
            <button onclick="runSim('A3')" class="btn-sim-a text-xs px-3 py-1.5 rounded-lg font-medium transition-colors">Run</button>
          </div>
        </div>
      </div>
      <!-- Category B -->
      <div>
        <p class="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-2">Category B — Admin Approval Required</p>
        <div class="space-y-2">
          <div class="glass rounded-lg p-3 flex items-center justify-between">
            <div><p class="text-xs font-medium text-slate-200">B1: IAM CI-Pipeline User</p><p class="text-xs text-slate-500 mt-0.5">HIGH · Role=CI-Pipeline → admin review</p></div>
            <button onclick="runSim('B1')" class="btn-sim-b text-xs px-3 py-1.5 rounded-lg font-medium transition-colors">Run</button>
          </div>
          <div class="glass rounded-lg p-3 flex items-center justify-between">
            <div><p class="text-xs font-medium text-slate-200">B2: Production SG — RDP Open</p><p class="text-xs text-slate-500 mt-0.5">CRITICAL · Prod tag → admin required</p></div>
            <button onclick="runSim('B2')" class="btn-sim-b text-xs px-3 py-1.5 rounded-lg font-medium transition-colors">Run</button>
          </div>
        </div>
        <p class="text-xs text-slate-500 mt-3 leading-relaxed">Category B findings appear as <span class="text-orange-400">Pending Approval</span>. Click the finding to review AI analysis, then approve or reject.</p>
      </div>
    </div>
    <!-- Active simulation cleanup -->
    <div id="sim-cleanup-row" class="hidden mt-3 pt-3 border-t border-slate-700 flex items-center gap-3">
      <p class="text-xs text-slate-400 flex-1" id="sim-cleanup-msg"></p>
      <button onclick="cleanupSim()" class="text-xs px-3 py-1.5 rounded-lg glass border border-red-800 text-red-400 hover:border-red-600 transition-colors">&#x1F5D1; Cleanup Resource</button>
    </div>
  </div>

  <!-- FILTER TABS -->
  <div class="flex gap-1 mb-4 border-b border-slate-700">
    <button onclick="setTab('all')"       id="tab-all"       class="px-4 py-2 text-sm font-medium tab-active  transition-colors">All</button>
    <button onclick="setTab('pending')"   id="tab-pending"   class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Pending</button>
    <button onclick="setTab('auto')"      id="tab-auto"      class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Auto-Remediated</button>
    <button onclick="setTab('resolved')"  id="tab-resolved"  class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Resolved</button>
    <button onclick="setTab('suppressed')" id="tab-suppressed" class="px-4 py-2 text-sm font-medium tab-inactive transition-colors">Suppressed</button>
  </div>

  <!-- FINDINGS TABLE -->
  <div class="glass rounded-xl overflow-hidden">
    <div id="loading" class="flex items-center justify-center py-16 text-slate-400">
      <svg class="spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>Loading findings...
    </div>
    <div id="empty" class="hidden flex items-center justify-center py-16 text-slate-500 text-center">
      <div><div class="text-4xl mb-3">&#x1F4CB;</div><p class="font-medium">No findings in this category</p><p class="text-xs mt-1">Use the Simulation Lab above to generate findings</p></div>
    </div>
    <table id="findings-table" class="hidden w-full text-sm">
      <thead><tr class="border-b border-slate-700 text-left">
        <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-24">Severity</th>
        <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Resource</th>
        <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Finding</th>
        <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-28">Status</th>
        <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-32">Time</th>
        <th class="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide w-56">Actions</th>
      </tr></thead>
      <tbody id="findings-body"></tbody>
    </table>
  </div>

  <div class="flex items-center justify-end mt-3 gap-2 text-xs text-slate-500">
    <span class="pulse w-1.5 h-1.5 rounded-full bg-green-500 inline-block"></span>Auto-refreshes every 30s
  </div>
</main>

<!-- FINDING DETAIL MODAL -->
<div id="modal" class="hidden fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4" onclick="closeModal(event)">
  <div class="glass rounded-2xl w-full max-w-2xl max-h-[88vh] overflow-y-auto" onclick="event.stopPropagation()">
    <div class="flex items-start justify-between p-5 border-b border-slate-700">
      <div>
        <p id="modal-severity" class="text-xs font-semibold uppercase tracking-widest mb-1"></p>
        <h2 id="modal-title" class="text-base font-bold text-white"></h2>
        <p id="modal-resource" class="text-xs text-slate-400 mt-1"></p>
      </div>
      <button onclick="closeModal()" class="text-slate-400 hover:text-white p-1">&#10005;</button>
    </div>
    <div class="p-5 space-y-4">
      <div>
        <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Description</p>
        <p id="modal-description" class="text-sm text-slate-200 leading-relaxed"></p>
      </div>
      <div>
        <p class="text-xs text-indigo-400 uppercase tracking-wide mb-1">&#x1F916; AI Analysis</p>
        <div class="bg-slate-900 rounded-lg p-3"><p id="modal-analysis" class="text-sm text-slate-200 leading-relaxed"></p></div>
      </div>
      <div id="modal-actions-section">
        <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Recommended Actions</p>
        <div id="modal-actions-list" class="space-y-2"></div>
      </div>
      <div id="modal-approval-section" class="hidden">
        <p class="text-xs text-orange-400 uppercase tracking-wide mb-2">&#x26A0;&#xFE0F; Admin Decision Required</p>
        <div id="modal-approve-buttons" class="space-y-2"></div>
        <div class="flex gap-2 mt-2">
          <button onclick="doAction('reject')" class="btn-reject flex-1 py-2 rounded-lg text-xs font-medium transition-colors">Reject (False Positive)</button>
          <button onclick="doAction('manual')" class="btn-manual flex-1 py-2 rounded-lg text-xs font-medium transition-colors">I'll Fix Manually</button>
        </div>
      </div>
      <!-- Email resend -->
      <div id="modal-email-section" class="hidden pt-2 border-t border-slate-700">
        <button onclick="resendEmail()" class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">&#x2709; Resend email alert</button>
      </div>
      <div class="pt-2 border-t border-slate-700 text-xs text-slate-500 flex justify-between">
        <span>ID: <code id="modal-id" class="text-slate-400 text-xs"></code></span>
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
let pipelineState = 'UNKNOWN';
let activeSim = null; // { resource_info, resource_type, finding_id }

const API_BASE = window.location.origin + (window.location.pathname.startsWith('/prod') ? '/prod' : '');

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => { loadAll(); setInterval(loadAll, 30000); });

async function loadAll() {
  document.getElementById('refresh-icon').innerHTML = '<svg class="spin w-4 h-4 inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>';
  await Promise.all([loadFindings(), loadSettings(), loadPipelineStatus()]);
  document.getElementById('refresh-icon').innerHTML = '&#8635;';
  document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// ── FINDINGS ───────────────────────────────────────────────────────────────────
async function loadFindings() {
  try {
    const res = await fetch(API_BASE + '/dashboard/api/findings');
    const data = await res.json();
    allFindings = data.findings || [];
    updateStats(); renderTable();
  } catch(e) { console.error(e); }
}

function updateStats() {
  let total=allFindings.length, pending=0, auto=0, resolved=0, suppressed=0;
  allFindings.forEach(f => {
    const s = (f.status||'').toUpperCase();
    if(s==='PENDING_APPROVAL') pending++;
    else if(s==='AUTO_REMEDIATED') auto++;
    else if(['RESOLVED','APPROVED'].includes(s)) resolved++;
    else if(['SUPPRESSED','FALSE_POSITIVE','REJECTED'].includes(s)) suppressed++;
  });
  document.getElementById('stat-total').textContent     = total;
  document.getElementById('stat-pending').textContent   = pending;
  document.getElementById('stat-auto').textContent      = auto;
  document.getElementById('stat-resolved').textContent  = resolved;
  document.getElementById('stat-suppressed').textContent= suppressed;
}

function filteredFindings() {
  if(currentTab==='all') return allFindings;
  const MAP = {
    pending:['PENDING_APPROVAL'], auto:['AUTO_REMEDIATED'],
    resolved:['RESOLVED','APPROVED'], suppressed:['SUPPRESSED','FALSE_POSITIVE','REJECTED'],
  };
  const allowed = (MAP[currentTab]||[]);
  return allFindings.filter(f => allowed.includes((f.status||'').toUpperCase()));
}

function renderTable() {
  const findings=filteredFindings();
  document.getElementById('loading').classList.add('hidden');
  if(findings.length===0){
    document.getElementById('empty').classList.remove('hidden');
    document.getElementById('findings-table').classList.add('hidden'); return;
  }
  document.getElementById('empty').classList.add('hidden');
  document.getElementById('findings-table').classList.remove('hidden');
  document.getElementById('findings-body').innerHTML = findings.map(f => `
    <tr class="border-b border-slate-800 row-hover transition-colors" onclick="openModal(${JSON.stringify(f.finding_id)})">
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded text-xs font-semibold ${sevClass(f.severity)}">${esc(f.severity||'N/A')}</span></td>
      <td class="px-4 py-3">
        <p class="text-xs text-slate-400">${esc(f.resource_type||'')}</p>
        <p class="font-mono text-xs text-slate-200 truncate max-w-xs" title="${esc(f.resource_id||'')}">${esc(shortId(f.resource_id))}</p>
      </td>
      <td class="px-4 py-3">
        <p class="text-slate-200 text-sm font-medium">${esc(f.title||f.finding_id||'')}</p>
        <p class="text-slate-400 text-xs mt-0.5 truncate max-w-sm">${esc(f.description||'')}</p>
      </td>
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded text-xs font-semibold ${statClass(f.status)}">${statLabel(f.status)}</span></td>
      <td class="px-4 py-3 text-xs text-slate-400">${fmtTime(f.created_at)}</td>
      <td class="px-4 py-3" onclick="event.stopPropagation()">${actionBtns(f)}</td>
    </tr>`).join('');
}

function actionBtns(f) {
  const s = (f.status||'').toUpperCase();
  if(s!=='PENDING_APPROVAL') return '<span class="text-xs text-slate-600">—</span>';
  const actions = safeParse(f.recommended_actions,[]);
  let btns = actions.slice(0,2).map(a =>
    `<button onclick="quickApprove(${JSON.stringify(f.finding_id)},${a.action_id})" class="btn-approve px-2 py-1 rounded text-xs font-medium transition-colors">${esc((a.description||'Approve').substring(0,30))}</button>`
  ).join('');
  btns += `<button onclick="quickReject(${JSON.stringify(f.finding_id)})" class="btn-reject px-2 py-1 rounded text-xs transition-colors">Reject</button>`;
  return `<div class="flex flex-wrap gap-1">${btns}</div>`;
}

// ── SETTINGS ───────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const res = await fetch(API_BASE+'/dashboard/api/settings');
    const data = await res.json();
    emailEnabled = data.value==='true'; updateToggleUI();
  } catch(e){}
}

function updateToggleUI() {
  const btn=document.getElementById('email-toggle'), knob=document.getElementById('toggle-knob');
  if(emailEnabled){ btn.style.background='#4f46e5'; knob.style.transform='translateX(20px)'; }
  else{ btn.style.background='#374151'; knob.style.transform='translateX(0)'; }
}

async function toggleEmail() {
  emailEnabled=!emailEnabled; updateToggleUI();
  try {
    await fetch(API_BASE+'/dashboard/api/settings',{
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email_notifications:emailEnabled}),
    });
  } catch(e){ emailEnabled=!emailEnabled; updateToggleUI(); }
}

// ── PIPELINE ───────────────────────────────────────────────────────────────────
async function loadPipelineStatus() {
  try {
    const res = await fetch(API_BASE+'/dashboard/api/control');
    const data = await res.json();
    pipelineState = data.pipeline||'UNKNOWN'; updatePipelineUI();
  } catch(e){}
}

function updatePipelineUI() {
  const dot=document.getElementById('pipeline-dot');
  const lbl=document.getElementById('pipeline-label');
  const btn=document.getElementById('pipeline-btn');
  if(pipelineState==='ENABLED'){
    dot.className='w-2 h-2 rounded-full bg-green-500';
    lbl.textContent='Pipeline Active';
    btn.textContent='Shutdown'; btn.className='text-xs px-2 py-1 rounded glass border border-red-800 text-red-400 hover:border-red-600 transition-colors';
  } else if(pipelineState==='DISABLED'){
    dot.className='w-2 h-2 rounded-full bg-red-500';
    lbl.textContent='Pipeline Stopped';
    btn.textContent='Start Pipeline'; btn.className='text-xs px-2 py-1 rounded glass border border-green-800 text-green-400 hover:border-green-600 transition-colors';
  } else {
    dot.className='w-2 h-2 rounded-full bg-slate-500';
    lbl.textContent='Pipeline'; btn.textContent='...';
  }
}

async function togglePipeline() {
  const action = pipelineState==='ENABLED' ? 'shutdown' : 'start';
  const confirm_msg = action==='shutdown'
    ? 'Shutdown the pipeline? New findings will NOT be processed until you restart.'
    : 'Start the pipeline? It will begin processing Security Hub findings.';
  if(!confirm(confirm_msg)) return;
  try {
    const res = await fetch(API_BASE+'/dashboard/api/control',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action}),
    });
    const data = await res.json();
    if(res.ok){ pipelineState=data.pipeline; updatePipelineUI(); showToast(action==='shutdown'?'Pipeline stopped — no new findings will be processed':'Pipeline started','success'); }
    else showToast(data.error||'Failed','error');
  } catch(e){ showToast('Network error','error'); }
}

// ── SIMULATION ─────────────────────────────────────────────────────────────────
async function runSim(caseId) {
  const simStatus = document.getElementById('sim-status');
  simStatus.className='text-xs px-3 py-1.5 rounded-lg glass border border-yellow-600 text-yellow-300';
  simStatus.textContent=`Starting case ${caseId}...`;
  simStatus.classList.remove('hidden');
  try {
    const res = await fetch(API_BASE+'/dashboard/api/simulate',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({case_id:caseId}),
    });
    const data = await res.json();
    if(res.ok){
      activeSim = { resource_info:data.sim_resource_info, resource_type:data.sim_resource_type, finding_id:data.finding_id };
      simStatus.className='text-xs px-3 py-1.5 rounded-lg glass border border-green-600 text-green-300';
      simStatus.textContent=`Case ${caseId} running — check findings in ~60s`;
      const cleanRow=document.getElementById('sim-cleanup-row');
      document.getElementById('sim-cleanup-msg').textContent=`Active: ${data.sim_resource_id}`;
      cleanRow.classList.remove('hidden');
      showToast(data.message,'success');
      setTimeout(loadFindings, 5000);
    } else {
      simStatus.className='text-xs px-3 py-1.5 rounded-lg glass border border-red-600 text-red-300';
      simStatus.textContent=`Error: ${data.error||'Failed'}`;
      showToast(data.error||'Simulation failed','error');
    }
  } catch(e){ simStatus.textContent='Network error'; showToast('Network error','error'); }
}

async function cleanupSim() {
  if(!activeSim){ showToast('No active simulation to clean up','error'); return; }
  try {
    const res = await fetch(API_BASE+'/dashboard/api/simulate',{
      method:'DELETE', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({sim_resource_type:activeSim.resource_type, sim_resource_info:activeSim.resource_info}),
    });
    const data = await res.json();
    if(res.ok){
      activeSim=null;
      document.getElementById('sim-cleanup-row').classList.add('hidden');
      document.getElementById('sim-status').classList.add('hidden');
      showToast('Simulation resource deleted','success');
    } else showToast(data.error||'Cleanup failed','error');
  } catch(e){ showToast('Network error','error'); }
}

// ── TABS ───────────────────────────────────────────────────────────────────────
function setTab(tab) {
  currentTab=tab;
  ['all','pending','auto','resolved','suppressed'].forEach(t=>{
    document.getElementById('tab-'+t).className='px-4 py-2 text-sm font-medium transition-colors '+(t===tab?'tab-active':'tab-inactive');
  });
  renderTable();
}

// ── MODAL ──────────────────────────────────────────────────────────────────────
function openModal(findingId) {
  const f = allFindings.find(x=>x.finding_id===findingId);
  if(!f) return;
  currentFinding=f;
  document.getElementById('modal-severity').textContent=f.severity||'';
  document.getElementById('modal-severity').className='text-xs font-semibold uppercase tracking-widest mb-1 '+sevText(f.severity);
  document.getElementById('modal-title').textContent=f.title||f.finding_id;
  document.getElementById('modal-resource').textContent=(f.resource_type||'')+'  —  '+(f.resource_id||'');
  document.getElementById('modal-description').textContent=f.description||'No description.';
  document.getElementById('modal-id').textContent=f.finding_id;
  document.getElementById('modal-time').textContent=fmtTime(f.created_at);
  const ai=safeParse(f.ai_analysis,{});
  document.getElementById('modal-analysis').textContent=ai.analysis||f.ai_analysis||'No AI analysis available.';
  const actions=safeParse(f.recommended_actions,[]);
  document.getElementById('modal-actions-list').innerHTML=actions.map(a=>
    `<div class="flex items-start gap-2 text-sm"><span class="mt-0.5 w-5 h-5 rounded-full bg-slate-700 flex-shrink-0 flex items-center justify-center text-xs">${a.action_id||'?'}</span><span class="text-slate-200">${esc(a.description||'')}</span></div>`
  ).join('')||'<p class="text-xs text-slate-500">No specific actions listed.</p>';
  const appSec=document.getElementById('modal-approval-section');
  if((f.status||'').toUpperCase()==='PENDING_APPROVAL'){
    appSec.classList.remove('hidden');
    document.getElementById('modal-approve-buttons').innerHTML=actions.map(a=>
      `<button onclick="doAction('approve',${a.action_id})" class="btn-approve w-full py-2 rounded-lg text-xs font-medium transition-colors text-left px-3">&#x2713; Approve: ${esc(a.description||'Action '+a.action_id)}</button>`
    ).join('');
  } else appSec.classList.add('hidden');
  // Show email resend always
  document.getElementById('modal-email-section').classList.remove('hidden');
  document.getElementById('modal').classList.remove('hidden');
  document.body.style.overflow='hidden';
}

function closeModal(event) {
  if(event&&event.target!==document.getElementById('modal')) return;
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow='';
  currentFinding=null;
}

// ── ACTIONS ────────────────────────────────────────────────────────────────────
async function doAction(action, actionId) {
  if(!currentFinding) return;
  await submitAction(currentFinding.finding_id, action, actionId);
  closeModal();
}
async function quickApprove(findingId, actionId) { await submitAction(findingId,'approve',actionId); }
async function quickReject(findingId) { await submitAction(findingId,'reject',null); }

async function submitAction(findingId, action, actionId) {
  try {
    const body={finding_id:findingId, action};
    if(actionId!=null) body.action_id=actionId;
    const res = await fetch(API_BASE+'/dashboard/api/action',{
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body),
    });
    const data = await res.json();
    if(res.ok){ showToast('Action submitted: '+action,'success'); await loadFindings(); }
    else showToast(data.error||'Action failed','error');
  } catch(e){ showToast('Network error: '+e.message,'error'); }
}

async function resendEmail() {
  if(!currentFinding) return;
  try {
    const res = await fetch(API_BASE+'/dashboard/api/email',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({finding_id:currentFinding.finding_id}),
    });
    const data = await res.json();
    showToast(res.ok?'Email sent successfully':data.error||'Failed to send email', res.ok?'success':'error');
  } catch(e){ showToast('Network error','error'); }
}

// ── TOAST ──────────────────────────────────────────────────────────────────────
function showToast(msg, type) {
  const t=document.createElement('div');
  t.className=`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg border text-xs font-medium shadow-xl transition-opacity `+(type==='success'?'bg-green-900 border-green-700 text-green-200':'bg-red-900 border-red-700 text-red-200');
  t.textContent=msg; document.body.appendChild(t);
  setTimeout(()=>{ t.style.opacity='0'; setTimeout(()=>t.remove(),500); },3500);
}

// ── UTILS ──────────────────────────────────────────────────────────────────────
function sevClass(s){return{CRITICAL:'badge-critical',HIGH:'badge-high',MEDIUM:'badge-medium',LOW:'badge-low'}[(s||'').toUpperCase()]||'badge-info'}
function sevText(s){return{CRITICAL:'text-red-400',HIGH:'text-orange-400',MEDIUM:'text-yellow-400',LOW:'text-cyan-400'}[(s||'').toUpperCase()]||'text-slate-400'}
function statClass(s){return{PENDING_APPROVAL:'s-pending',AUTO_REMEDIATED:'s-auto',RESOLVED:'s-resolved',APPROVED:'s-approved',REJECTED:'s-rejected',SUPPRESSED:'s-suppressed',FALSE_POSITIVE:'s-suppressed',FAILED:'s-failed',MANUAL_REVIEW:'s-manual'}[(s||'').toUpperCase()]||'s-suppressed'}
function statLabel(s){return{PENDING_APPROVAL:'Pending',AUTO_REMEDIATED:'Auto-Fixed',RESOLVED:'Resolved',APPROVED:'Approved',REJECTED:'Rejected',SUPPRESSED:'Suppressed',FALSE_POSITIVE:'False Positive',FAILED:'Failed',MANUAL_REVIEW:'Manual Review'}[(s||'').toUpperCase()]||(s||'Unknown')}
function shortId(id){if(!id) return ''; const p=id.split('/'); return p[p.length-1]||id}
function fmtTime(iso){
  if(!iso) return '-';
  try{const d=new Date(iso),diff=Math.floor((Date.now()-d)/1000);
    if(diff<60)return diff+'s ago';if(diff<3600)return Math.floor(diff/60)+'m ago';
    if(diff<86400)return Math.floor(diff/3600)+'h ago';return d.toLocaleDateString();}
  catch{return iso}
}
function safeParse(v,fb){if(!v)return fb;if(typeof v==='object')return v;try{return JSON.parse(v)}catch{return fb}}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
</script>
</body>
</html>"""
