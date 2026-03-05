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
  .detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .detail-cell{background:rgba(15,23,42,.6);border:1px solid rgba(71,85,105,.3);border-radius:8px;padding:10px}
  .detail-label{font-size:0.65rem;text-transform:uppercase;letter-spacing:.06em;color:#64748b;margin-bottom:3px}
  .detail-value{font-size:0.75rem;color:#e2e8f0;font-family:ui-monospace,monospace;word-break:break-all}
  .step-item{display:flex;gap:8px;align-items:flex-start;font-size:0.75rem;color:#94a3b8;padding:4px 0}
  .step-check{color:#22c55e;flex-shrink:0;margin-top:1px}
</style>
</head>
<body class="min-h-screen">

<!-- TERMINATE OVERLAY -->
<div id="terminate-overlay" class="hidden fixed inset-0 z-[100] bg-black/97 flex items-center justify-center p-6">
  <div class="text-center max-w-lg w-full">
    <div class="text-5xl mb-5">&#x26A0;&#xFE0F;</div>
    <h2 class="text-2xl font-bold text-red-400 mb-3">Infrastructure Termination</h2>
    <p id="terminate-msg" class="text-slate-300 mb-6 leading-relaxed">Deleting all AWS resources... Step Functions, DynamoDB, Lambda functions, SNS, EventBridge, API Gateway.</p>
    <div class="text-6xl font-bold text-red-500 mb-2 font-mono" id="terminate-countdown">35</div>
    <p class="text-xs text-slate-500 mb-8">Estimated seconds remaining</p>
    <div class="glass rounded-xl p-4 text-left space-y-2 text-sm">
      <div class="step-item"><span class="step-check">&#x2713;</span> Stopping Step Functions executions</div>
      <div class="step-item"><span class="step-check">&#x2713;</span> Deleting DynamoDB tables</div>
      <div class="step-item"><span class="step-check">&#x2713;</span> Removing Lambda functions</div>
      <div class="step-item"><span class="step-check">&#x2713;</span> Deleting SNS topic &amp; subscriptions</div>
      <div class="step-item"><span class="step-check">&#x2713;</span> Removing EventBridge rules</div>
      <div class="step-item"><span class="step-check">&#x2713;</span> Deleting CloudWatch log groups</div>
      <div class="step-item"><span class="step-check">&#x2713;</span> Removing Secrets Manager secret</div>
      <div class="step-item"><span class="step-check">&#x2713;</span> Deleting API Gateway &amp; this dashboard</div>
    </div>
    <p class="text-xs text-slate-600 mt-6">After completion, this page will no longer be accessible.</p>
  </div>
</div>

<!-- HEADER -->
<header class="glass sticky top-0 z-40 px-6 py-3 flex items-center justify-between border-b border-slate-700">
  <div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-lg">&#x1F6E1;</div>
    <div>
      <h1 class="font-bold text-base text-white leading-none">Security Automation</h1>
      <p class="text-xs text-slate-400 leading-none mt-0.5">AI-powered threat detection &amp; remediation</p>
    </div>
  </div>
  <div class="flex items-center gap-3">
    <span class="text-xs text-slate-500" id="last-updated">Loading...</span>
    <!-- Pipeline status + control -->
    <div class="flex items-center gap-2" title="Controls real AWS Security Hub event processing via EventBridge. Simulation Lab always works regardless of this setting.">
      <span id="pipeline-dot" class="w-2 h-2 rounded-full bg-slate-500"></span>
      <span id="pipeline-label" class="text-xs text-slate-400">Pipeline</span>
      <button id="pipeline-btn" onclick="togglePipeline()" class="text-xs px-2 py-1 rounded glass border border-slate-600 hover:border-slate-400 transition-colors"></button>
    </div>
    <!-- AI Analysis toggle -->
    <div class="flex items-center gap-2" title="When OFF: AI API calls are skipped entirely — uses keyword-based routing. Saves tokens during testing.">
      <span class="text-xs text-slate-400">AI</span>
      <button id="ai-analysis-toggle" onclick="toggleAIAnalysis()" class="relative w-10 h-5 rounded-full transition-colors bg-green-700" title="Toggle AI analysis. OFF = no API calls, uses keyword fallback.">
        <span id="ai-analysis-knob" class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform translate-x-5"></span>
      </button>
    </div>
    <!-- Auto-Remediation toggle -->
    <div class="flex items-center gap-2" title="When OFF: all findings require manual admin approval — ideal for demos">
      <span class="text-xs text-slate-400">Auto-Fix</span>
      <button id="auto-rem-toggle" onclick="toggleAutoRemediation()" class="relative w-10 h-5 rounded-full transition-colors bg-green-700" title="Toggle auto-remediation. OFF = all findings routed to admin approval.">
        <span id="auto-rem-knob" class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform translate-x-5"></span>
      </button>
    </div>
    <!-- Email toggle -->
    <div class="flex items-center gap-2">
      <span class="text-xs text-slate-400">Email</span>
      <button id="email-toggle" onclick="toggleEmail()" class="relative w-10 h-5 rounded-full transition-colors bg-slate-700" title="Toggle email alerts">
        <span id="toggle-knob" class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform"></span>
      </button>
    </div>
    <!-- AI Config button -->
    <button onclick="openAIModal()" class="glass px-3 py-1.5 rounded-lg text-xs text-indigo-300 hover:text-indigo-100 border border-indigo-800 hover:border-indigo-600 transition-colors flex items-center gap-1" title="Configure AI provider and model">
      &#x1F916; AI
    </button>
    <button onclick="loadAll()" class="glass px-3 py-1.5 rounded-lg text-xs text-slate-300 hover:text-white border border-transparent hover:border-slate-500 transition-colors flex items-center gap-1">
      <span id="refresh-icon">&#8635;</span> Refresh
    </button>
    <button onclick="clearAllFindings()" class="glass px-3 py-1.5 rounded-lg text-xs text-orange-400 hover:text-orange-200 border border-orange-900 hover:border-orange-700 transition-colors" title="Delete all findings from DynamoDB (demo reset)">
      &#x1F5D1; Clear All
    </button>
    <button onclick="terminateInfrastructure()" class="glass px-3 py-1.5 rounded-lg text-xs text-red-500 hover:text-red-300 border border-red-900 hover:border-red-700 transition-colors" title="Permanently delete all AWS infrastructure">
      &#x26D4; Terminate
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
  <div class="glass rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto" onclick="event.stopPropagation()">

    <!-- Modal Header -->
    <div class="flex items-start justify-between p-5 border-b border-slate-700">
      <div class="flex-1 min-w-0 pr-4">
        <div class="flex items-center gap-2 mb-1 flex-wrap">
          <span id="modal-sev-badge" class="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider"></span>
          <span id="modal-status-badge" class="px-2 py-0.5 rounded text-xs font-semibold"></span>
          <span id="modal-source-badge" class="px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-300"></span>
        </div>
        <h2 id="modal-title" class="text-base font-bold text-white leading-snug"></h2>
      </div>
      <button onclick="closeModal()" class="text-slate-400 hover:text-white p-1 flex-shrink-0">&#10005;</button>
    </div>

    <div class="p-5 space-y-5">

      <!-- Technical Details Grid -->
      <div>
        <p class="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-2">&#x1F4CB; Technical Details</p>
        <div class="detail-grid">
          <div class="detail-cell">
            <div class="detail-label">Resource Type</div>
            <div class="detail-value" id="modal-resource-type">—</div>
          </div>
          <div class="detail-cell">
            <div class="detail-label">Resource ARN / ID</div>
            <div class="detail-value truncate" id="modal-resource-id" title=""></div>
            <a id="modal-console-link" href="#" target="_blank" rel="noopener" class="hidden text-xs text-indigo-400 hover:text-indigo-200 mt-1 inline-flex items-center gap-1">&#x1F517; Open in AWS Console</a>
          </div>
          <div class="detail-cell">
            <div class="detail-label">AWS Account ID</div>
            <div class="detail-value" id="modal-account-id">—</div>
          </div>
          <div class="detail-cell">
            <div class="detail-label">AWS Region</div>
            <div class="detail-value" id="modal-region">—</div>
          </div>
          <div class="detail-cell">
            <div class="detail-label">Detected At</div>
            <div class="detail-value" id="modal-created-at">—</div>
          </div>
          <div class="detail-cell">
            <div class="detail-label">Last Updated</div>
            <div class="detail-value" id="modal-updated-at">—</div>
          </div>
          <div class="detail-cell col-span-2" style="grid-column:span 2">
            <div class="detail-label">Finding ID</div>
            <div class="detail-value" id="modal-finding-id">—</div>
          </div>
        </div>
      </div>

      <!-- Description -->
      <div>
        <p class="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-2">&#x1F4DD; Description</p>
        <p id="modal-description" class="text-sm text-slate-200 leading-relaxed bg-slate-900/50 rounded-lg p-3"></p>
      </div>

      <!-- AI Analysis -->
      <div>
        <div class="flex items-center gap-2 mb-2">
          <p class="text-xs text-indigo-400 uppercase tracking-widest font-semibold">&#x1F916; AI Analysis</p>
          <span id="modal-risk-badge" class="text-xs px-2 py-0.5 rounded hidden"></span>
          <span id="modal-auto-badge" class="text-xs px-2 py-0.5 rounded hidden"></span>
        </div>
        <div class="bg-slate-900 rounded-lg p-3">
          <p id="modal-analysis" class="text-sm text-slate-200 leading-relaxed"></p>
        </div>
        <div id="modal-escalation" class="hidden mt-2 text-xs text-orange-400 bg-orange-900/20 border border-orange-800 rounded p-2"></div>
      </div>

      <!-- Recommended Actions -->
      <div id="modal-rec-section">
        <p class="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-2">&#x1F527; Recommended Actions</p>
        <div id="modal-actions-list" class="space-y-2"></div>
      </div>

      <!-- Remediation Result (shown when not pending) -->
      <div id="modal-remediation-section" class="hidden">
        <p class="text-xs text-green-400 uppercase tracking-widest font-semibold mb-2">&#x2705; Remediation Details</p>
        <div class="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
          <div class="flex items-center gap-2 mb-3">
            <span class="text-xs text-slate-400">Method:</span>
            <code id="modal-remediation-method" class="text-xs text-cyan-400"></code>
          </div>
          <div id="modal-remediation-steps" class="space-y-1"></div>
          <div class="mt-3 pt-3 border-t border-slate-700 flex items-center gap-2">
            <span class="text-xs text-slate-400">Post-remediation status:</span>
            <span id="modal-post-status" class="text-xs px-2 py-0.5 rounded font-semibold"></span>
          </div>
        </div>
      </div>

      <!-- Admin Decision (pending only) -->
      <div id="modal-approval-section" class="hidden">
        <p class="text-xs text-orange-400 uppercase tracking-widest font-semibold mb-2">&#x26A0;&#xFE0F; Admin Decision Required</p>
        <div id="modal-approve-buttons" class="space-y-2 mb-2"></div>
        <div class="flex gap-2">
          <button onclick="doAction('reject')" class="btn-reject flex-1 py-2 rounded-lg text-xs font-medium transition-colors">&#x274C; Reject (False Positive)</button>
          <button onclick="doAction('manual')" class="btn-manual flex-1 py-2 rounded-lg text-xs font-medium transition-colors">&#x1F527; I'll Fix Manually</button>
        </div>
      </div>

      <!-- AI Remediation Runbook -->
      <div class="pt-4 border-t border-slate-700">
        <div class="flex items-center justify-between mb-3">
          <p class="text-xs text-indigo-400 uppercase tracking-widest font-semibold">&#x1F916; AI Remediation Runbook</p>
          <button id="modal-gen-runbook-btn" onclick="generateRunbook()"
            class="text-xs px-3 py-1.5 rounded-lg bg-indigo-900/60 hover:bg-indigo-800 text-indigo-300 border border-indigo-800 hover:border-indigo-600 transition-colors flex items-center gap-1.5">
            &#x2728; Generate Runbook
          </button>
        </div>
        <div id="modal-runbook-loading" class="hidden text-xs text-indigo-400 flex items-center gap-2 py-2">
          <svg class="spin w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
          Calling AI to generate remediation runbook...
        </div>
        <div id="modal-runbook-content" class="hidden space-y-3">
          <!-- Summary row -->
          <div class="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
            <div class="flex items-center gap-3 mb-2 flex-wrap">
              <span id="runbook-risk-badge" class="text-xs px-2 py-0.5 rounded font-semibold"></span>
              <span id="runbook-summary" class="text-xs text-slate-200 flex-1"></span>
            </div>
            <p class="text-xs text-slate-500"><span class="text-slate-400">Impact: </span><span id="runbook-impact"></span></p>
            <!-- Steps -->
            <div id="runbook-steps" class="mt-3 space-y-2"></div>
            <!-- Rollback accordion -->
            <details class="mt-3">
              <summary class="text-xs text-slate-500 cursor-pointer hover:text-slate-300 select-none">&#x21A9; View rollback plan</summary>
              <div id="runbook-rollback" class="mt-2 pl-3 border-l border-slate-700 space-y-1"></div>
            </details>
            <!-- Warnings -->
            <div id="runbook-warnings" class="hidden mt-2 space-y-1"></div>
          </div>
          <!-- Action row -->
          <div class="flex gap-2">
            <button id="runbook-apply-btn" onclick="applyRunbook()"
              class="flex-1 py-2 rounded-lg text-xs font-semibold bg-emerald-900 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 transition-colors">
              &#x2713; Apply Remediation
            </button>
            <button id="runbook-undo-btn" onclick="undoRunbook()"
              class="hidden px-4 py-2 rounded-lg text-xs font-semibold bg-orange-900 hover:bg-orange-800 text-orange-200 border border-orange-700 transition-colors">
              &#x21A9; Undo
            </button>
          </div>
          <!-- Execution logs -->
          <div id="runbook-logs-section" class="hidden">
            <details open>
              <summary class="text-xs text-slate-500 cursor-pointer hover:text-slate-300 select-none">Execution Logs</summary>
              <div id="runbook-logs" class="mt-2 bg-black/60 rounded-lg p-3 text-xs font-mono space-y-0.5 max-h-48 overflow-y-auto"></div>
            </details>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="pt-3 border-t border-slate-700 flex items-center justify-between gap-3">
        <button onclick="resendEmail()" id="modal-email-btn" class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">&#x2709; Resend email alert</button>
        <span class="text-xs text-slate-500" id="modal-footer-time"></span>
      </div>

    </div>
  </div>
</div>

<script>
// ── STATE ──────────────────────────────────────────────────────────────────────
let allFindings = [];
let metaInfo = {account_id: '', region: ''};
let currentTab = 'all';
let currentFinding = null;
let emailEnabled = false;
let autoRemediationEnabled = true;
let aiAnalysisEnabled = true;
let pipelineState = 'UNKNOWN';
let activeSim = null;
let aiSessionKey = '';  // Cached API key for current browser session

const API_BASE = window.location.origin + (window.location.pathname.startsWith('/prod') ? '/prod' : '');

// ── REMEDIATION DETAILS LOOKUP ─────────────────────────────────────────────────
const REMEDIATION_DETAILS = {
  's3_block_public_access': {
    method: 'boto3: s3.put_bucket_public_access_block()',
    steps: [
      'Validated bucket existence and exclusion tags (AutoRemediationExclude, PublicAccess)',
      'Applied Block Public Access: BlockPublicAcls=True, IgnorePublicAcls=True, BlockPublicPolicy=True, RestrictPublicBuckets=True',
      'Set bucket ACL to private (object ownership permitting)',
      'Verified all four Block Public Access settings are enabled',
      'Updated AWS Security Hub finding status to RESOLVED',
    ],
  },
  'iam_key_disabled': {
    method: 'boto3: iam.update_access_key(Status="Inactive")',
    steps: [
      'Listed all active IAM access keys for the user',
      'Set each active key to Status=Inactive (preserves key for audit trail)',
      'Applied deny-all inline policy as secondary hardening measure',
      'Logged remediation with finding correlation ID',
    ],
  },
  'sg_ssh_restricted': {
    method: 'boto3: ec2.revoke_security_group_ingress()',
    steps: [
      'Identified security group with unrestricted SSH ingress (TCP port 22 from 0.0.0.0/0)',
      'Revoked inbound rule: Protocol=TCP, Port=22, Source=0.0.0.0/0',
      'Verified no remaining unrestricted 0.0.0.0/0 ingress rules for port 22',
      'Updated Security Hub finding status to RESOLVED',
    ],
  },
  'sg_all_traffic_restricted': {
    method: 'boto3: ec2.revoke_security_group_ingress()',
    steps: [
      'Identified security group allowing all inbound traffic from 0.0.0.0/0',
      'Revoked all-traffic ingress rule: Protocol=All, Source=0.0.0.0/0',
      'Verified all unrestricted ingress rules removed',
      'Updated Security Hub finding status to RESOLVED',
    ],
  },
  'sg_rdp_restricted': {
    method: 'boto3: ec2.revoke_security_group_ingress()',
    steps: [
      'Identified security group with unrestricted RDP ingress (TCP port 3389 from 0.0.0.0/0)',
      'Revoked inbound rule: Protocol=TCP, Port=3389, Source=0.0.0.0/0',
      'Verified no remaining unrestricted RDP ingress rules',
      'Updated Security Hub finding status to RESOLVED',
    ],
  },
  'approve': {
    method: 'Admin decision via dashboard',
    steps: [
      'Administrator reviewed AI analysis and recommended actions',
      'Admin approved remediation action via dashboard',
      'Step Functions task token signalled with APPROVED decision',
      'Remediation Lambda executed the approved action',
    ],
  },
  'reject': {
    method: 'Admin decision — false positive',
    steps: [
      'Administrator reviewed AI analysis',
      'Admin rejected finding as false positive',
      'Finding marked as rejected — no remediation performed',
    ],
  },
  'manual': {
    method: 'Manual remediation flagged',
    steps: [
      'Administrator flagged finding for manual handling',
      'No automated remediation performed',
      'Manual review and fix required by security team',
    ],
  },
};

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
    metaInfo = data.meta || {account_id: '', region: ''};
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
  return allFindings.filter(f => (MAP[currentTab]||[]).includes((f.status||'').toUpperCase()));
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
    <tr class="border-b border-slate-800 row-hover transition-colors" data-fid="${esc(f.finding_id)}" onclick="openModal(this.dataset.fid)">
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
  const fid = esc(f.finding_id);
  const actions = safeParse(f.recommended_actions,[]);
  const appLabel = actions.length>0 ? esc((actions[0].description||'Approve').substring(0,25)) : 'Approve';
  const appAid = actions.length>0 ? (actions[0].action_id||1) : 1;
  return `<div class="flex flex-wrap gap-1">
    <button data-fid="${fid}" data-aid="${appAid}" onclick="quickApprove(this.dataset.fid,this.dataset.aid)" class="btn-approve px-2 py-1 rounded text-xs font-medium transition-colors">${appLabel}</button>
    <button data-fid="${fid}" onclick="quickReject(this.dataset.fid)" class="btn-reject px-2 py-1 rounded text-xs transition-colors">Reject</button>
  </div>`;
}

// ── SETTINGS ───────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const res = await fetch(API_BASE+'/dashboard/api/settings');
    const data = await res.json();
    emailEnabled = data.email_notifications==='true';
    autoRemediationEnabled = data.auto_remediation!=='false';
    aiAnalysisEnabled = data.ai_analysis_enabled!=='false';
    updateEmailUI(); updateAutoRemUI(); updateAIAnalysisUI();
  } catch(e){}
}

function updateEmailUI() {
  const btn=document.getElementById('email-toggle'), knob=document.getElementById('toggle-knob');
  if(emailEnabled){ btn.style.background='#4f46e5'; knob.style.transform='translateX(20px)'; }
  else{ btn.style.background='#374151'; knob.style.transform='translateX(0)'; }
}

function updateAutoRemUI() {
  const btn=document.getElementById('auto-rem-toggle'), knob=document.getElementById('auto-rem-knob');
  if(autoRemediationEnabled){ btn.style.background='#15803d'; knob.style.transform='translateX(20px)'; }
  else{ btn.style.background='#7f1d1d'; knob.style.transform='translateX(0)'; }
}

async function toggleEmail() {
  emailEnabled=!emailEnabled; updateEmailUI();
  try {
    await fetch(API_BASE+'/dashboard/api/settings',{
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email_notifications:emailEnabled}),
    });
  } catch(e){ emailEnabled=!emailEnabled; updateEmailUI(); }
}

async function toggleAutoRemediation() {
  const next = !autoRemediationEnabled;
  const msg = next
    ? 'Enable auto-remediation? Category A findings will be fixed automatically.'
    : 'Disable auto-remediation? ALL findings will require manual admin approval — useful for demos.';
  if(!confirm(msg)) return;
  autoRemediationEnabled = next; updateAutoRemUI();
  try {
    const res = await fetch(API_BASE+'/dashboard/api/settings',{
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({auto_remediation:autoRemediationEnabled}),
    });
    if(res.ok){
      showToast(autoRemediationEnabled ? 'Auto-remediation enabled' : 'Auto-remediation disabled — all findings will route to approval', 'success');
    } else { autoRemediationEnabled=!autoRemediationEnabled; updateAutoRemUI(); }
  } catch(e){ autoRemediationEnabled=!autoRemediationEnabled; updateAutoRemUI(); }
}

function updateAIAnalysisUI() {
  const btn=document.getElementById('ai-analysis-toggle'), knob=document.getElementById('ai-analysis-knob');
  if(aiAnalysisEnabled){ btn.style.background='#15803d'; knob.style.transform='translateX(20px)'; }
  else{ btn.style.background='#7f1d1d'; knob.style.transform='translateX(0)'; }
}

async function toggleAIAnalysis() {
  const next = !aiAnalysisEnabled;
  const msg = next
    ? 'Enable AI analysis? Findings will be analyzed by the AI provider (uses API tokens).'
    : 'Disable AI analysis? Findings will use keyword-based routing only — no API tokens consumed. Ideal for testing.';
  if(!confirm(msg)) return;
  aiAnalysisEnabled = next; updateAIAnalysisUI();
  try {
    const res = await fetch(API_BASE+'/dashboard/api/settings',{
      method:'PUT', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ai_analysis_enabled:aiAnalysisEnabled}),
    });
    if(res.ok){
      showToast(aiAnalysisEnabled ? 'AI analysis enabled' : 'AI analysis disabled — keyword-based fallback active', 'success');
    } else { aiAnalysisEnabled=!aiAnalysisEnabled; updateAIAnalysisUI(); }
  } catch(e){ aiAnalysisEnabled=!aiAnalysisEnabled; updateAIAnalysisUI(); }
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
  const msg = action==='shutdown'
    ? 'Shutdown the pipeline? New findings will NOT be processed until restarted.'
    : 'Start the pipeline? It will begin processing Security Hub findings.';
  if(!confirm(msg)) return;
  try {
    const res = await fetch(API_BASE+'/dashboard/api/control',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action}),
    });
    const data = await res.json();
    if(res.ok){ pipelineState=data.pipeline; updatePipelineUI(); showToast(action==='shutdown'?'Pipeline stopped':'Pipeline started','success'); }
    else showToast(data.error||'Failed','error');
  } catch(e){ showToast('Network error','error'); }
}

// ── TERMINATE ──────────────────────────────────────────────────────────────────
async function terminateInfrastructure() {
  const input = prompt(
    '\u26a0\ufe0f DANGER: Terminate All AWS Infrastructure\n\n' +
    'This will permanently delete:\n' +
    '  \u2022 All Lambda functions\n  \u2022 DynamoDB tables\n  \u2022 API Gateway (this page)\n' +
    '  \u2022 SNS topics, EventBridge rules, CloudWatch logs\n  \u2022 Secrets Manager secrets\n\n' +
    'This action CANNOT be undone.\n\nType "terminate" to confirm:'
  );
  if (input === null) return;
  if (input !== 'terminate') { alert('Cancelled. You must type exactly "terminate" to proceed.'); return; }

  document.getElementById('terminate-overlay').classList.remove('hidden');
  try {
    const res = await fetch(API_BASE+'/dashboard/api/control',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action:'terminate'}),
    });
    const data = await res.json();
    if(!res.ok){
      document.getElementById('terminate-overlay').classList.add('hidden');
      showToast(data.error||'Termination failed','error');
      return;
    }
    startTerminationCountdown();
  } catch(e){
    document.getElementById('terminate-overlay').classList.add('hidden');
    showToast('Network error — termination may have started anyway','error');
  }
}

function startTerminationCountdown() {
  let s = 35;
  const countEl = document.getElementById('terminate-countdown');
  const msgEl = document.getElementById('terminate-msg');
  const timer = setInterval(() => {
    s--;
    countEl.textContent = Math.max(0, s);
    if(s <= 0){
      clearInterval(timer);
      msgEl.innerHTML = '<span class="text-green-400 font-semibold">\u2713 Infrastructure terminated.</span> All AWS resources have been deleted. This dashboard is no longer hosted on AWS.';
      countEl.textContent = '\u2713';
      countEl.className = 'text-6xl font-bold text-green-500 mb-2 font-mono';
    }
  }, 1000);
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
      document.getElementById('sim-cleanup-msg').textContent=`Active: ${data.sim_resource_id}`;
      document.getElementById('sim-cleanup-row').classList.remove('hidden');
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
function getConsoleUrl(resourceType, resourceId, region) {
  if(!resourceId) return null;
  const r = region || 'us-east-1';
  const base = `https://${r}.console.aws.amazon.com`;
  const t = (resourceType||'').toLowerCase();
  // S3: arn:aws:s3:::bucket-name
  if(t.includes('s3bucket')) {
    const bucket = resourceId.replace(/^arn:aws:s3:::/, '').split('/')[0];
    return `https://s3.console.aws.amazon.com/s3/buckets/${bucket}?region=${r}`;
  }
  // EC2 Security Group: arn:aws:ec2:region:account:security-group/sg-xxxxx
  if(t.includes('securitygroup')) {
    const sgId = resourceId.split('/').pop();
    return `${base}/ec2/v2/home?region=${r}#SecurityGroups:group-id=${sgId}`;
  }
  // IAM User: arn:aws:iam::account:user/username
  if(t.includes('iamuser') || t.includes('iam')) {
    const username = resourceId.split('/').pop();
    return `https://us-east-1.console.aws.amazon.com/iam/home?region=${r}#/users/details/${username}`;
  }
  return null;
}

function parseArn(arn) {
  if(!arn || !arn.startsWith('arn:')) return {service:'',region:'',account:'',resource:''};
  const p = arn.split(':');
  return { service:p[2]||'', region:p[3]||'', account:p[4]||'', resource:p.slice(5).join(':')||'' };
}

function openModal(findingId) {
  const f = allFindings.find(x=>x.finding_id===findingId);
  if(!f) return;
  currentFinding=f;

  const arn = parseArn(f.resource_id||'');
  const isSimulation = (f.finding_id||'').startsWith('sim-');
  const status = (f.status||'').toUpperCase();

  // Severity badge
  const sevEl = document.getElementById('modal-sev-badge');
  sevEl.textContent = f.severity||'N/A';
  sevEl.className = 'px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ' + sevClass(f.severity);

  // Status badge
  const stEl = document.getElementById('modal-status-badge');
  stEl.textContent = statLabel(f.status);
  stEl.className = 'px-2 py-0.5 rounded text-xs font-semibold ' + statClass(f.status);

  // Source badge
  const srcEl = document.getElementById('modal-source-badge');
  srcEl.textContent = isSimulation ? '\uD83E\uDDEA Simulation Lab' : '\u2601\uFE0F AWS Security Hub';

  document.getElementById('modal-title').textContent = f.title||f.finding_id||'';

  // Technical details
  document.getElementById('modal-resource-type').textContent = f.resource_type||'—';
  const ridEl = document.getElementById('modal-resource-id');
  ridEl.textContent = f.resource_id||'—';
  ridEl.title = f.resource_id||'';

  // AWS Console deep-link
  const consoleRegion = arn.region || metaInfo.region || 'us-east-1';
  const consoleUrl = getConsoleUrl(f.resource_type, f.resource_id, consoleRegion);
  const linkEl = document.getElementById('modal-console-link');
  if(consoleUrl){ linkEl.href=consoleUrl; linkEl.classList.remove('hidden'); }
  else { linkEl.classList.add('hidden'); }

  // Account ID: try ARN, else fall back to metaInfo
  document.getElementById('modal-account-id').textContent = arn.account || metaInfo.account_id || '—';

  // Region: try ARN, else metaInfo
  document.getElementById('modal-region').textContent = arn.region || metaInfo.region || '—';

  document.getElementById('modal-finding-id').textContent = f.finding_id||'—';
  document.getElementById('modal-created-at').textContent = fmtTimeFull(f.created_at);
  document.getElementById('modal-updated-at').textContent = fmtTimeFull(f.updated_at);

  // Description
  document.getElementById('modal-description').textContent = f.description||'No description.';

  // AI Analysis
  const ai = safeParse(f.ai_analysis, {});
  const analysisText = ai.analysis || (typeof f.ai_analysis === 'string' ? f.ai_analysis : '') || 'No AI analysis available.';
  document.getElementById('modal-analysis').textContent = analysisText;

  // Risk level badge
  const riskEl = document.getElementById('modal-risk-badge');
  if(ai.risk_level) {
    riskEl.textContent = 'Risk: ' + ai.risk_level;
    riskEl.className = 'text-xs px-2 py-0.5 rounded ' + sevClass(ai.risk_level);
    riskEl.classList.remove('hidden');
  } else { riskEl.classList.add('hidden'); }

  // Auto-remediate badge
  const autoEl = document.getElementById('modal-auto-badge');
  if(ai.safe_to_auto_remediate !== undefined) {
    autoEl.textContent = ai.safe_to_auto_remediate ? 'Auto-remediate: Yes' : 'Auto-remediate: No (escalated)';
    autoEl.className = 'text-xs px-2 py-0.5 rounded ' + (ai.safe_to_auto_remediate ? 'bg-green-900 text-green-300' : 'bg-orange-900 text-orange-300');
    autoEl.classList.remove('hidden');
  } else { autoEl.classList.add('hidden'); }

  // Escalation reason
  const escalEl = document.getElementById('modal-escalation');
  if(ai.escalation_reason) {
    escalEl.textContent = '\u26a0\ufe0f Escalated: ' + ai.escalation_reason;
    escalEl.classList.remove('hidden');
  } else { escalEl.classList.add('hidden'); }

  // Recommended actions
  const actions = safeParse(f.recommended_actions, []);
  document.getElementById('modal-actions-list').innerHTML = actions.map(a =>
    `<div class="flex items-start gap-2 text-sm"><span class="mt-0.5 w-6 h-6 rounded-full bg-slate-700 flex-shrink-0 flex items-center justify-center text-xs font-bold text-slate-300">${a.action_id||'?'}</span><span class="text-slate-200 leading-relaxed">${esc(a.description||'')}</span></div>`
  ).join('') || '<p class="text-xs text-slate-500">No specific actions listed.</p>';

  // Remediation details section
  const remSec = document.getElementById('modal-remediation-section');
  const actionTaken = f.action_taken||'';
  if(status !== 'PENDING_APPROVAL' && actionTaken) {
    const det = REMEDIATION_DETAILS[actionTaken] || {
      method: actionTaken,
      steps: [actionTaken + ' completed'],
    };
    document.getElementById('modal-remediation-method').textContent = det.method;
    document.getElementById('modal-remediation-steps').innerHTML = det.steps.map(s =>
      `<div class="step-item"><span class="step-check">\u2713</span><span>${esc(s)}</span></div>`
    ).join('');
    const psEl = document.getElementById('modal-post-status');
    psEl.textContent = statLabel(f.status);
    psEl.className = 'text-xs px-2 py-0.5 rounded font-semibold ' + statClass(f.status);
    remSec.classList.remove('hidden');
  } else {
    remSec.classList.add('hidden');
  }

  // Admin approval section
  const appSec = document.getElementById('modal-approval-section');
  if(status === 'PENDING_APPROVAL') {
    appSec.classList.remove('hidden');
    const appBtns = actions.map(a =>
      `<button data-fid="${esc(f.finding_id)}" data-aid="${a.action_id}" onclick="doAction('approve',this.dataset.aid)" class="btn-approve w-full py-2 rounded-lg text-xs font-medium transition-colors text-left px-3">\u2713 Approve: ${esc(a.description||'Action '+a.action_id)}</button>`
    ).join('') || `<button onclick="doAction('approve',1)" class="btn-approve w-full py-2 rounded-lg text-xs font-medium transition-colors text-left px-3">\u2713 Approve Remediation</button>`;
    document.getElementById('modal-approve-buttons').innerHTML = appBtns;
  } else { appSec.classList.add('hidden'); }

  // Footer
  document.getElementById('modal-footer-time').textContent = 'Detected ' + fmtTime(f.created_at);

  // Runbook section — reset to initial state; restore if already applied/ready
  _resetRunbookUI();
  const runbookStr = f.runbook;
  const runbookStatus = (f.runbook_status||'').toUpperCase();
  if(runbookStr && runbookStatus && runbookStatus !== 'UNDONE') {
    try {
      const rb = typeof runbookStr === 'string' ? JSON.parse(runbookStr) : runbookStr;
      renderRunbook(rb, '', '');
      document.getElementById('modal-runbook-content').classList.remove('hidden');
      document.getElementById('modal-gen-runbook-btn').textContent = '\u21BB Regenerate';
      if(runbookStatus === 'RUNBOOK_APPLIED') {
        document.getElementById('runbook-apply-btn').disabled = true;
        document.getElementById('runbook-apply-btn').textContent = '\u2713 Applied';
        document.getElementById('runbook-apply-btn').className = 'flex-1 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed';
        document.getElementById('runbook-undo-btn').classList.remove('hidden');
      }
      if(runbookStatus === 'RUNBOOK_FAILED') {
        document.getElementById('runbook-apply-btn').textContent = '\u21BB Retry Apply';
      }
      const logsStr = f.runbook_logs;
      if(logsStr) {
        try {
          const logs = typeof logsStr === 'string' ? JSON.parse(logsStr) : logsStr;
          if(logs && logs.length) renderRunbookLogs(logs, runbookStatus === 'RUNBOOK_APPLIED');
        } catch(e) {}
      }
    } catch(e) {}
  }

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
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow='';
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

async function clearAllFindings() {
  if(!confirm('Delete ALL findings from the dashboard? This cannot be undone.')) return;
  try {
    const res = await fetch(API_BASE+'/dashboard/api/findings',{method:'DELETE'});
    const data = await res.json();
    if(res.ok){ showToast(`Cleared ${data.deleted} finding(s)`,'success'); await loadFindings(); }
    else showToast(data.error||'Clear failed','error');
  } catch(e){ showToast('Network error','error'); }
}

async function resendEmail() {
  if(!currentFinding) return;
  try {
    const res = await fetch(API_BASE+'/dashboard/api/email',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({finding_id:currentFinding.finding_id}),
    });
    const data = await res.json();
    showToast(res.ok?'Email sent':data.error||'Failed', res.ok?'success':'error');
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
function fmtTimeFull(iso){
  if(!iso) return '—';
  try{
    const d=new Date(iso);
    return d.toLocaleString('en-US',{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZoneName:'short'});
  } catch{return iso}
}
function safeParse(v,fb){if(!v)return fb;if(typeof v==='object')return v;try{return JSON.parse(v)}catch{return fb}}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}

// ── RUNBOOK ─────────────────────────────────────────────────────────────────────
function _resetRunbookUI() {
  document.getElementById('modal-runbook-content').classList.add('hidden');
  document.getElementById('modal-runbook-loading').classList.add('hidden');
  const genBtn = document.getElementById('modal-gen-runbook-btn');
  genBtn.disabled = false; genBtn.textContent = '\u2728 Generate Runbook';
  const applyBtn = document.getElementById('runbook-apply-btn');
  applyBtn.disabled = false; applyBtn.textContent = '\u2713 Apply Remediation';
  applyBtn.className = 'flex-1 py-2 rounded-lg text-xs font-semibold bg-emerald-900 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 transition-colors';
  applyBtn.classList.remove('hidden');
  document.getElementById('runbook-undo-btn').classList.add('hidden');
  document.getElementById('runbook-logs-section').classList.add('hidden');
}

async function generateRunbook() {
  if(!currentFinding) return;
  const genBtn = document.getElementById('modal-gen-runbook-btn');
  const loading = document.getElementById('modal-runbook-loading');
  const content = document.getElementById('modal-runbook-content');
  genBtn.disabled = true; genBtn.textContent = 'Generating\u2026';
  loading.classList.remove('hidden'); content.classList.add('hidden');
  document.getElementById('runbook-logs-section').classList.add('hidden');
  try {
    const res = await fetch(API_BASE+'/dashboard/api/ai-runbook', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({finding_id:currentFinding.finding_id}),
    });
    const data = await res.json();
    if(!res.ok) {
      showToast(data.error||'Runbook generation failed','error');
    } else {
      renderRunbook(data.runbook, data.provider, data.model);
      content.classList.remove('hidden');
      genBtn.textContent = '\u21BB Regenerate';
    }
  } catch(e) { showToast('Network error: '+e.message,'error'); }
  finally { loading.classList.add('hidden'); genBtn.disabled = false; }
}

function renderRunbook(runbook, provider, model) {
  const risk = (runbook.risk_level||'LOW').toUpperCase();
  const riskEl = document.getElementById('runbook-risk-badge');
  riskEl.textContent = risk;
  riskEl.className = 'text-xs px-2 py-0.5 rounded font-semibold ' +
    ({LOW:'badge-low',MEDIUM:'badge-medium',HIGH:'badge-high',CRITICAL:'badge-critical'}[risk]||'badge-info');
  document.getElementById('runbook-summary').textContent = runbook.summary||'';
  document.getElementById('runbook-impact').textContent = runbook.estimated_impact||'';

  document.getElementById('runbook-steps').innerHTML = (runbook.steps||[]).map(s=>`
    <div class="bg-slate-800/70 rounded-lg p-3">
      <div class="flex items-center gap-2 mb-1">
        <span class="w-5 h-5 rounded-full bg-indigo-900 border border-indigo-700 text-indigo-300 text-xs flex items-center justify-center flex-shrink-0">${s.n||''}</span>
        <span class="text-xs font-semibold text-slate-200">${esc(s.title||'')}</span>
      </div>
      <p class="text-xs text-slate-400 ml-7 mt-0.5">${esc(s.action||'')}</p>
      ${s.api_call?`<code class="block text-xs text-cyan-400/90 font-mono ml-7 mt-1 break-all">${esc(s.api_call)}</code>`:''}
      ${s.expected?`<p class="text-xs text-emerald-400/70 ml-7 mt-0.5">\u2192 ${esc(s.expected)}</p>`:''}
    </div>`).join('');

  document.getElementById('runbook-rollback').innerHTML = (runbook.rollback||[]).map(s=>
    `<div class="py-1 text-xs"><span class="text-slate-500">${s.n}.</span> <span class="text-slate-300">${esc(s.action||'')}</span>${s.api_call?`<code class="block text-cyan-400/70 font-mono mt-0.5 ml-3">${esc(s.api_call)}</code>`:''}</div>`
  ).join('');

  const warns = runbook.warnings||[];
  const warnEl = document.getElementById('runbook-warnings');
  if(warns.length) {
    warnEl.classList.remove('hidden');
    warnEl.innerHTML = warns.map(w=>`<p class="text-xs text-yellow-400/80">\u26A0 ${esc(w)}</p>`).join('');
  } else { warnEl.classList.add('hidden'); }

  // Reset action buttons to default
  const applyBtn = document.getElementById('runbook-apply-btn');
  applyBtn.disabled = false; applyBtn.textContent = '\u2713 Apply Remediation';
  applyBtn.className = 'flex-1 py-2 rounded-lg text-xs font-semibold bg-emerald-900 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 transition-colors';
  applyBtn.classList.remove('hidden');
  document.getElementById('runbook-undo-btn').classList.add('hidden');
}

async function applyRunbook() {
  if(!currentFinding) return;
  const rt = currentFinding.resource_type||'';
  const rid = (currentFinding.resource_id||'').split('/').pop() || currentFinding.resource_id;
  if(!confirm(`Apply AI remediation to ${rt} — ${rid}?\n\nThis makes LIVE changes to your AWS resources.`)) return;
  const btn = document.getElementById('runbook-apply-btn');
  btn.disabled = true;
  btn.innerHTML = '<svg class="spin w-3 h-3 inline mr-1" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg> Applying\u2026';
  try {
    const res = await fetch(API_BASE+'/dashboard/api/apply-runbook', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({finding_id:currentFinding.finding_id}),
    });
    const data = await res.json();
    renderRunbookLogs(data.logs||[], data.success);
    if(data.success) {
      btn.textContent = '\u2713 Applied'; btn.disabled = true;
      btn.className = 'flex-1 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed';
      if(data.can_undo) document.getElementById('runbook-undo-btn').classList.remove('hidden');
      showToast('Remediation applied successfully','success');
      await loadFindings();
    } else {
      btn.disabled = false; btn.textContent = '\u21BB Retry Apply';
      btn.className = 'flex-1 py-2 rounded-lg text-xs font-semibold bg-red-900 hover:bg-red-800 text-red-200 border border-red-700 transition-colors';
      showToast('Remediation failed — see logs below','error');
    }
  } catch(e) { showToast('Network error: '+e.message,'error'); btn.disabled=false; btn.textContent='\u2713 Apply Remediation'; }
}

async function undoRunbook() {
  if(!currentFinding) return;
  if(!confirm('Undo the applied remediation?\nThis will RESTORE the original misconfigured state.')) return;
  const btn = document.getElementById('runbook-undo-btn');
  btn.disabled = true; btn.textContent = 'Undoing\u2026';
  try {
    const res = await fetch(API_BASE+'/dashboard/api/undo-runbook', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({finding_id:currentFinding.finding_id}),
    });
    const data = await res.json();
    renderRunbookLogs(data.logs||[], data.success);
    if(data.success) {
      btn.classList.add('hidden');
      const applyBtn = document.getElementById('runbook-apply-btn');
      applyBtn.disabled = false; applyBtn.textContent = '\u2713 Apply Remediation';
      applyBtn.className = 'flex-1 py-2 rounded-lg text-xs font-semibold bg-emerald-900 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 transition-colors';
      showToast('Remediation undone — original state restored','success');
      await loadFindings();
    } else { btn.disabled=false; btn.textContent='\u21A9 Undo'; showToast('Undo failed — see logs below','error'); }
  } catch(e) { showToast('Network error: '+e.message,'error'); btn.disabled=false; btn.textContent='\u21A9 Undo'; }
}

function renderRunbookLogs(logs, success) {
  const section = document.getElementById('runbook-logs-section');
  const el = document.getElementById('runbook-logs');
  section.classList.remove('hidden');
  el.innerHTML = logs.map(l => {
    const cls = (l.includes('\u2713')||l.includes('Verified')) ? 'text-emerald-400' :
                (l.includes('\u2717')||l.startsWith('ERROR')||l.startsWith('EXCEPTION')) ? 'text-red-400' :
                l.includes('WARNING') ? 'text-yellow-400' : 'text-slate-400';
    return `<div class="${cls}">${esc(l)}</div>`;
  }).join('');
  el.scrollTop = el.scrollHeight;
}

// ── AI CONFIG MODAL ────────────────────────────────────────────────────────────
let aiConfig = { provider: 'gemini', model: 'gemini-2.0-flash', has_api_key: false };
let aiModels = [];

const PROVIDER_HINTS = {
  gemini: 'Get a free key at aistudio.google.com \u2014 recommended: gemini-2.0-flash (15 req/min free)',
  claude: 'Get a key at console.anthropic.com \u2014 recommended: haiku-4-5 (~8x cheaper than Sonnet)',
};

async function openAIModal() {
  document.getElementById('ai-modal').classList.remove('hidden');
  document.getElementById('ai-validate-status').textContent = '';
  document.getElementById('ai-key-input').value = '';
  aiModels = [];
  await loadAIConfig();
  // Auto-load models if we have a cached session key or a stored key
  if (aiSessionKey || aiConfig.has_api_key) {
    await validateAndLoadModels();
  }
}

function closeAIModal() {
  document.getElementById('ai-modal').classList.add('hidden');
}

function onProviderChange() {
  const provider = document.getElementById('ai-provider-select').value;
  document.getElementById('ai-provider-hint').textContent = PROVIDER_HINTS[provider] || '';
  aiModels = [];
  renderAIModelDropdown(provider, '', []);
  document.getElementById('ai-validate-status').textContent = '';
}

async function loadAIConfig() {
  try {
    const res = await fetch(API_BASE + '/dashboard/api/ai-config');
    if (!res.ok) return;
    const data = await res.json();
    aiConfig = data;
    document.getElementById('ai-provider-select').value = data.provider || 'gemini';
    document.getElementById('ai-provider-hint').textContent = PROVIDER_HINTS[data.provider] || '';
    document.getElementById('ai-current-display').textContent = (data.provider || 'gemini') + ' / ' + (data.model || '—');
    renderAIModelDropdown(data.provider, data.model, []);
    document.getElementById('ai-key-status').textContent = data.has_api_key ? '\u2705 API key stored' : '\u26A0\uFE0F No key stored yet';
    document.getElementById('ai-key-status').className = 'text-xs ' + (data.has_api_key ? 'text-green-400' : 'text-yellow-400');
    const keyInput = document.getElementById('ai-key-input');
    keyInput.placeholder = (data.has_api_key || aiSessionKey) ? '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (stored \u2014 enter new key to replace)' : 'Paste your API key here...';
  } catch(e) { console.error(e); }
}

function renderAIModelDropdown(provider, selectedModel, models) {
  const sel = document.getElementById('ai-model-select');
  sel.innerHTML = '';
  if (models.length === 0) {
    const opt = document.createElement('option');
    opt.value = selectedModel || '';
    opt.textContent = selectedModel ? selectedModel + '  (current \u2014 validate key to reload list)' : '\u2014 validate key to load available models \u2014';
    sel.appendChild(opt);
    return;
  }
  models.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = m.name || m.id;
    if (m.id === selectedModel) opt.selected = true;
    sel.appendChild(opt);
  });
  aiModels = models;
}

async function validateAndLoadModels() {
  const provider  = document.getElementById('ai-provider-select').value;
  const inputKey  = document.getElementById('ai-key-input').value.trim();
  // Use input key, else session-cached key, else nothing (backend uses stored key)
  const apiKey    = inputKey || aiSessionKey;
  const statusEl  = document.getElementById('ai-validate-status');
  const btn       = document.getElementById('ai-validate-btn');

  btn.disabled = true;
  btn.textContent = 'Validating\u2026';
  statusEl.textContent = '';

  try {
    const res = await fetch(API_BASE + '/dashboard/api/ai-models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: apiKey }),  // empty string → backend uses stored key
    });
    const data = await res.json();
    if (!res.ok || !data.valid) {
      statusEl.textContent = data.error || 'Invalid API key';
      statusEl.className = 'text-xs text-red-400';
    } else {
      if (inputKey) aiSessionKey = inputKey;  // Cache validated key for this session
      statusEl.textContent = `\u2705 Key valid \u2014 ${data.models.length} model(s) loaded`;
      statusEl.className = 'text-xs text-green-400';
      renderAIModelDropdown(provider, aiConfig.model, data.models);
    }
  } catch(e) {
    statusEl.textContent = 'Network error: ' + e.message;
    statusEl.className = 'text-xs text-red-400';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Validate & Load';
  }
}

async function saveAIConfig() {
  const provider = document.getElementById('ai-provider-select').value;
  const model    = document.getElementById('ai-model-select').value;
  const apiKey   = document.getElementById('ai-key-input').value.trim();
  const saveBtn  = document.getElementById('ai-save-btn');
  const statusEl = document.getElementById('ai-validate-status');

  if (!model) { statusEl.textContent = 'Select a model first'; statusEl.className='text-xs text-yellow-400'; return; }

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving\u2026';

  const payload = { provider, model };
  if (apiKey) payload.api_key = apiKey;

  try {
    const res = await fetch(API_BASE + '/dashboard/api/ai-config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok) {
      aiConfig.provider = provider;
      aiConfig.model = model;
      if (apiKey) { aiConfig.has_api_key = true; aiSessionKey = apiKey; }
      showToast(`AI config saved: ${provider} / ${model}`, 'success');
      document.getElementById('ai-key-status').textContent = '\u2705 API key stored';
      document.getElementById('ai-key-status').className = 'text-xs text-green-400';
      document.getElementById('ai-key-input').value = '';
      closeAIModal();
    } else {
      statusEl.textContent = data.error || 'Save failed';
      statusEl.className = 'text-xs text-red-400';
    }
  } catch(e) {
    statusEl.textContent = 'Network error: ' + e.message;
    statusEl.className = 'text-xs text-red-400';
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Configuration';
  }
}
</script>

<!-- AI CONFIG MODAL -->
<div id="ai-modal" class="hidden fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4">
  <div class="glass rounded-2xl w-full max-w-lg border border-indigo-800/50 shadow-2xl">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-700">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-900/80 border border-indigo-700 flex items-center justify-center text-lg">&#x1F916;</div>
        <div>
          <h2 class="font-semibold text-white text-sm">AI Provider Configuration</h2>
          <p class="text-xs text-slate-400">Hot-swap without redeploying infrastructure</p>
        </div>
      </div>
      <button onclick="closeAIModal()" class="text-slate-500 hover:text-white transition-colors text-xl leading-none">&times;</button>
    </div>
    <!-- Body -->
    <div class="px-6 py-5 space-y-5">

      <!-- Current config badge -->
      <div class="bg-slate-900/60 border border-slate-700 rounded-lg px-4 py-3 flex items-center gap-3">
        <span class="text-xs text-slate-400">Active:</span>
        <span class="text-xs font-mono text-indigo-300" id="ai-current-display">loading...</span>
        <span class="ml-auto text-xs" id="ai-key-status"></span>
      </div>

      <!-- Provider select -->
      <div>
        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">AI Provider</label>
        <select id="ai-provider-select" onchange="onProviderChange()"
          class="w-full bg-slate-900/80 border border-slate-600 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-slate-200 outline-none transition-colors cursor-pointer">
          <option value="gemini">Google Gemini  (free tier: 15 req/min)</option>
          <option value="claude">Anthropic Claude  (pay-as-you-go)</option>
        </select>
        <p id="ai-provider-hint" class="text-xs text-slate-500 mt-1.5">Get a free Gemini key at aistudio.google.com</p>
      </div>

      <!-- API Key input -->
      <div>
        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">API Key <span class="text-slate-500 normal-case font-normal">(leave blank to keep existing)</span></label>
        <div class="flex gap-2">
          <input type="password" id="ai-key-input" placeholder="Paste your API key here..."
            class="flex-1 bg-slate-900/80 border border-slate-600 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none transition-colors font-mono">
          <button id="ai-validate-btn" onclick="validateAndLoadModels()"
            class="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-800 hover:bg-indigo-700 text-indigo-100 border border-indigo-600 transition-colors whitespace-nowrap">
            Validate &amp; Load
          </button>
        </div>
        <p id="ai-validate-status" class="text-xs mt-2 min-h-[1rem]"></p>
      </div>

      <!-- Model select -->
      <div>
        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Model</label>
        <select id="ai-model-select"
          class="w-full bg-slate-900/80 border border-slate-600 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-slate-200 outline-none transition-colors">
        </select>
        <p class="text-xs text-slate-500 mt-1.5">Haiku (Claude) / 2.0-flash (Gemini) recommended for cost efficiency. Validate key to load all available models.</p>
      </div>

    </div>
    <!-- Footer -->
    <div class="px-6 py-4 border-t border-slate-700 flex items-center justify-between">
      <p class="text-xs text-slate-500">Changes apply to the next AI analysis run.</p>
      <div class="flex gap-3">
        <button onclick="closeAIModal()" class="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white glass border border-slate-600 hover:border-slate-400 transition-colors">Cancel</button>
        <button id="ai-save-btn" onclick="saveAIConfig()"
          class="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 transition-colors">
          Save Configuration
        </button>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""
