/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   KiranaMate — MerchantMind AI
   Live Dashboard · app.js
   Connects to REAL backend APIs — no demo scripts.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

const API = (window.location && window.location.origin && window.location.origin.startsWith('http')) ? window.location.origin : 'http://127.0.0.1:8000';

/* ── Trace Node Definitions for each agent ────────── */
const AGENT_NODES = {
  campaign: {
    label: 'Campaign Executor', badgeClass: 'campaign',
    nodes: [
      { step: '01', label: 'Parse\nGoal'     },
      { step: '02', label: 'Inventory\nQuery' },
      { step: '03', label: 'Discount\nCalc'   },
      { step: '04', label: 'Creative\nGen'    },
      { step: '05', label: 'Merchant\nApprove' },
      { step: '06', label: 'Campaign\nLaunch'  },
    ]
  },
  monitor: {
    label: 'Sales Monitor', badgeClass: 'monitor',
    nodes: [
      { step: '01', label: 'Data\nIngest'    },
      { step: '02', label: 'Baseline\nCompare' },
      { step: '03', label: 'Anomaly\nDetect'  },
      { step: '04', label: 'Alert\nDraft'     },
      { step: '05', label: 'WhatsApp\nNotify'  },
      { step: '06', label: 'Memory\nUpdate'   },
    ]
  },
  report: {
    label: 'Health Report', badgeClass: 'report',
    nodes: [
      { step: '01', label: 'Schedule\nTrigger' },
      { step: '02', label: 'Data\nAggregate'   },
      { step: '03', label: 'Health\nScore'     },
      { step: '04', label: 'PDF\nGenerate'     },
      { step: '05', label: 'Audio\nSummary'    },
      { step: '06', label: 'WhatsApp\nDeliver' },
    ]
  }
};

/* ── Dashboard Class ──────────────────────────────── */
class KiranateDashboard {
  constructor() {
    this.polling   = null;
    this.running   = false;
    this.timerRef  = null;
    this.timerSec  = 0;
    this.impact    = { recovered: 0, customers: 0, anomalies: 0, reports: 0 };
    this.lastTraceEventId = 0;
    this.currentAgentKey = 'campaign';
    this._lastLogMsg = null;
    this._lastWAMsg  = null;
  }

  async init() {
    // Set intro message time
    const timeEl = document.getElementById('wa-intro-time');
    if (timeEl) timeEl.textContent = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });

    // Wire event listeners
    document.getElementById('btn-campaign'     ).addEventListener('click', () => this.runCampaignLive());
    document.getElementById('btn-monitor'      ).addEventListener('click', () => this.runMonitorLive());
    document.getElementById('btn-report'       ).addEventListener('click', () => this.runReportLive());
    document.getElementById('refresh-btn'      ).addEventListener('click', () => this.manualRefresh());
    document.getElementById('impact-reset-btn' ).addEventListener('click', () => this.resetImpact());

    // Allow Enter key on campaign input
    document.getElementById('campaign-goal-input').addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !this.running) this.runCampaignLive();
    });

    // Initial fetch + polling
    await this.fetchDashboard();
    this.polling = setInterval(() => this.fetchDashboard(), 9000);

    // Real-time trace & WhatsApp sync with backend
    this.initTraceStream();

    // ScrollSpy, dynamic tab sliding indicator & scroll completion line
    this.initScrollSpyAndProgress();
  }

  /* ── Data ──────────────────────────────────────────── */
  async fetchDashboard() {
    try {
      const res  = await fetch(`${API}/merchant/dashboard`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.updateUI(data);
      this.setApiStatus('connected');
      this._setChip('ind-db',  'chip-db',  'green', 'Connected');
      this._setChip('ind-api', 'chip-api', 'green', 'Connected');
      this._setChip('ind-wa',  'chip-wa',  'green', 'Connected');
    } catch {
      this.setApiStatus('error');
      this._setChip('ind-db',  'chip-db',  '', 'Offline');
      this._setChip('ind-api', 'chip-api', '', 'Offline');
      this._setChip('ind-wa',  'chip-wa',  'orange', 'Unknown');
    }
  }

  async manualRefresh() {
    const btn = document.getElementById('refresh-btn');
    btn.classList.add('spinning');
    await this.fetchDashboard();
    setTimeout(() => btn.classList.remove('spinning'), 700);
  }

  updateUI(data) {
    if (!data) return;
    const ts = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
    document.getElementById('data-freshness').textContent = `Updated ${ts}`;

    const rev   = data.revenue || {};
    const today = rev.today || 0;
    const yest  = rev.yesterday || 0;
    const txns  = rev.transactions || 0;
    const aov   = rev.aov || (txns > 0 ? Math.round(today / txns) : 0);
    const delta = yest > 0 ? ((today - yest) / yest * 100).toFixed(1) : 0;

    document.getElementById('today-revenue').textContent = `₹${this.fmt(today)}`;
    document.getElementById('txn-count'    ).textContent = txns;
    document.getElementById('avg-order'    ).textContent = `₹${this.fmt(aov)}`;

    const dEl = document.getElementById('revenue-delta');
    dEl.textContent = `${Number(delta) >= 0 ? '↑' : '↓'} ${Math.abs(delta)}% vs yesterday`;
    dEl.className   = `revenue-delta ${Number(delta) >= 0 ? 'positive' : 'negative'}`;

    this.renderCatBars(data.categories || []);

    const anomalies = data.anomalies || [];
    const aBox      = document.getElementById('anomaly-alert');
    if (anomalies.length > 0) {
      aBox.style.display = 'flex';
      const a = anomalies[0];
      document.getElementById('anomaly-desc'    ).textContent = a.description || `${a.category}: ${a.deviation_pct?.toFixed(0)}% deviation`;
      document.getElementById('anomaly-severity').textContent = a.severity || 'WARNING';
    } else {
      aBox.style.display = 'none';
    }

    const khata = data.khata || {};
    document.getElementById('khata-count' ).textContent = khata.pending_count ?? '—';
    document.getElementById('khata-amount').textContent = `₹${this.fmt(khata.pending_total || 0)}`;
    document.getElementById('campaign-count').textContent = (data.recent_campaigns || []).length;
  }

  renderCatBars(cats) {
    const cont = document.getElementById('category-bars');
    if (!cats.length) { cont.innerHTML = '<div class="cat-placeholder">No category data yet</div>'; return; }

    const maxRev  = Math.max(...cats.map(c => c.revenue), 1);
    const clsMap  = { dairy:'dairy', snacks:'snacks', staples:'staples', beverages:'beverages', personal_care:'personal_care', misc:'misc' };

    cont.innerHTML = cats.slice(0, 5).map(c => {
      const pct = Math.round((c.revenue / maxRev) * 100);
      const cls = clsMap[c.category] || 'other';
      return `<div class="cat-bar-row">
        <div class="cat-bar-label">${this.cap(c.category)}</div>
        <div class="cat-bar-track"><div class="cat-bar-fill ${cls}" style="width:0" data-w="${pct}%"></div></div>
        <div class="cat-bar-value">₹${this.fmt(c.revenue)}</div>
      </div>`;
    }).join('');

    requestAnimationFrame(() => {
      cont.querySelectorAll('.cat-bar-fill').forEach(el => {
        setTimeout(() => { el.style.width = el.dataset.w; }, 80);
      });
    });
  }

  /* ── Live Action Runners ────────────────────────────── */

  async runCampaignLive() {
    if (this.running) return;
    const goalInput = document.getElementById('campaign-goal-input');
    const goal = goalInput.value.trim();
    if (!goal) {
      goalInput.focus();
      goalInput.style.borderColor = 'var(--red)';
      setTimeout(() => { goalInput.style.borderColor = ''; }, 1500);
      return;
    }

    this.running = true;
    const agentKey = 'campaign';
    this.startAgentRun(agentKey);

    // Show the goal in the activity feed
    this.addWAMsg('sent', `Target: ${goal}`);
    this.addWAMsg('system-msg', 'Executing Campaign Executor pipeline...');
    this.addLog('info', `POST /campaign/text → goal: "${goal.substring(0, 60)}..."`);

    try {
      const res = await fetch(`${API}/campaign/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Process trace log from the real response
      const trace = data.trace || [];
      await this.animateTraceFromLogs(agentKey, trace);

      // Show results in activity feed
      this.addWAMsg('received', `Campaign status: ${data.status || 'completed'}`);
      if (data.thread_id) {
        this.addWAMsg('received', `Thread: ${data.thread_id}`);
      }
      if (data.message) {
        this.addWAMsg('received', data.message);
      }

      // Show trace log entries
      for (const entry of trace.slice(-5)) {
        this.addLog('info', typeof entry === 'string' ? entry : JSON.stringify(entry));
      }

      this.addLog('success', `Campaign agent completed — status: ${data.status}`);
      this.addWAMsg('success-msg', 'Campaign pipeline completed successfully.');

      // Update impact with real data
      this.addImpact({ customers: 1 });
      this.finishAgentRun(agentKey, 'done');

    } catch (err) {
      this.addLog('error', `Campaign failed: ${err.message}`);
      this.addWAMsg('error-msg', `Error: ${err.message}`);
      this.finishAgentRun(agentKey, 'error');
    }
  }

  async runMonitorLive() {
    if (this.running) return;
    this.running = true;
    const agentKey = 'monitor';
    this.startAgentRun(agentKey);

    this.addWAMsg('system-msg', 'Running Sales Monitor cycle...');
    this.addLog('info', 'POST /demo/trigger-monitor → Checking hourly sales metrics');

    try {
      const res = await fetch(`${API}/demo/trigger-monitor`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const trace     = data.trace || [];
      const anomalies = data.anomalies || [];
      const alerts    = data.alerts || [];
      const reminders = data.reminders || [];

      await this.animateTraceFromLogs(agentKey, trace);

      // Show anomalies in feed
      if (anomalies.length > 0) {
        for (const a of anomalies) {
          const desc = typeof a === 'string' ? a : (a.description || `${a.category}: ${a.deviation_pct?.toFixed?.(0) || '?'}% deviation`);
          this.addWAMsg('received', `ANOMALY DETECTED: ${desc}`);
          this.addLog('warning', desc);
        }
      } else {
        this.addWAMsg('received', 'Sales check passed. All categories within normal baseline.');
        this.addLog('info', 'No anomalies detected');
      }

      // Show alerts sent
      if (alerts.length > 0) {
        this.addWAMsg('received', `${alerts.length} merchant alert(s) dispatched via WhatsApp.`);
      }

      // Show reminders sent
      if (reminders.length > 0) {
        this.addWAMsg('received', `${reminders.length} Khata recovery notice(s) dispatched.`);
      }

      // Trace log entries
      for (const entry of trace.slice(-5)) {
        this.addLog('info', typeof entry === 'string' ? entry : JSON.stringify(entry));
      }

      this.addLog('success', `Sales Monitor completed — ${anomalies.length} anomalies, ${alerts.length} alerts`);
      this.addWAMsg('success-msg', 'Sales Monitor cycle completed.');

      this.addImpact({ anomalies: anomalies.length || 0 });
      this.finishAgentRun(agentKey, 'done');

      // Refresh dashboard to show new anomalies
      await this.fetchDashboard();

    } catch (err) {
      this.addLog('error', `Monitor failed: ${err.message}`);
      this.addWAMsg('error-msg', `Error: ${err.message}`);
      this.finishAgentRun(agentKey, 'error');
    }
  }

  async runReportLive() {
    if (this.running) return;
    this.running = true;
    const agentKey = 'report';
    this.startAgentRun(agentKey);

    this.addWAMsg('system-msg', 'Compiling Weekly Health Report...');
    this.addLog('info', 'POST /demo/trigger-report → Generating weekly health report');

    try {
      const res = await fetch(`${API}/demo/trigger-report`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const trace = data.trace || [];
      await this.animateTraceFromLogs(agentKey, trace);

      // Show health score
      if (data.health_score !== undefined && data.health_score !== null) {
        this.addWAMsg('received', `Store Health Score: ${data.health_score}/100`);
        this.addLog('success', `Health Score: ${data.health_score}/100`);
      }

      // Revenue trend
      if (data.revenue_trend) {
        this.addWAMsg('received', `Revenue Trend: ${data.revenue_trend}`);
      }

      // Recommendation
      if (data.recommendation) {
        this.addWAMsg('received', `Store Recommendation:\n${data.recommendation.substring(0, 200)}`);
      }

      // Report preview
      if (data.report_preview) {
        this.addWAMsg('received', `Report Summary:\n${data.report_preview.substring(0, 220)}...`);
      }

      // Interactive PDF Document Card
      const pdfUrl = data.pdf_url || '/report/download';
      const pdfHtml = `
        <div class="wa-pdf-card" onclick="window.open('${pdfUrl}', '_blank')">
          <span class="wa-pdf-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
          </span>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:600;font-size:11.5px;color:#111b21;">KiranaMate_Weekly_Report.pdf</div>
            <div style="font-size:9.5px;color:#667781;">Score: ${data.health_score || 55}/100 &bull; ReportLab PDF</div>
          </div>
          <a href="${pdfUrl}" target="_blank" class="nav-pill-link" style="padding:3px 8px;font-size:10px;background:#ffffff;border:1px solid #c1c1c1;color:#111b21;">View</a>
        </div>
      `;
      this.addWAMsgHtml('received', pdfHtml);

      // Trace log entries
      for (const entry of trace.slice(-5)) {
        this.addLog('info', typeof entry === 'string' ? entry : JSON.stringify(entry));
      }

      this.addLog('success', `Health Report & PDF compiled — score: ${data.health_score || 'N/A'}`);
      this.addWAMsg('success-msg', 'Health Report & PDF delivered to merchant.');

      this.addImpact({ reports: 1 });
      this.finishAgentRun(agentKey, 'done');

      // Refresh dashboard
      await this.fetchDashboard();

    } catch (err) {
      this.addLog('error', `Report failed: ${err.message}`);
      this.addWAMsg('error-msg', `Error: ${err.message}`);
      this.finishAgentRun(agentKey, 'error');
    }
  }

  /* ── Agent Run Lifecycle ────────────────────────────── */

  startAgentRun(agentKey) {
    const agent = AGENT_NODES[agentKey];
    this.setBtnsDisabled(true, agentKey);
    this.clearTraceLog();
    this.startTimer();

    const badge = document.getElementById('trace-badge');
    badge.textContent = `${agent.label} — Processing...`;
    badge.className   = `trace-badge ${agent.badgeClass} processing`;

    // Update WhatsApp status
    document.getElementById('wa-agent-status').textContent = 'processing...';

    this.buildNodes(agent.nodes);
    // Activate first node to show "working"
    const firstNode = document.getElementById('tn-0');
    if (firstNode) firstNode.className = 'trace-node active';
  }

  finishAgentRun(agentKey, finalState) {
    this.stopTimer();
    this.running = false;
    this.setBtnsDisabled(false, null);

    const badge = document.getElementById('trace-badge');
    const agent = AGENT_NODES[agentKey];

    if (finalState === 'done') {
      badge.textContent = `${agent.label} — Complete`;
      badge.className   = 'trace-badge done';
      // Mark all nodes as done
      const cont = document.getElementById('trace-nodes');
      cont.querySelectorAll('.trace-node').forEach(n => n.className = 'trace-node done');
      cont.querySelectorAll('.trace-connector').forEach(c => c.classList.add('filled'));
    } else {
      badge.textContent = `${agent.label} — Error`;
      badge.className   = 'trace-badge error';
    }

    document.getElementById('wa-agent-status').textContent = 'online';
  }

  /* ── Trace Animation from Real Logs ────────────────── */

  async animateTraceFromLogs(agentKey, traceLogs) {
    const agent = AGENT_NODES[agentKey];
    const nodeCount = agent.nodes.length;

    // Distribute trace logs across nodes for animation
    const logsPerNode = Math.max(1, Math.ceil(traceLogs.length / nodeCount));

    for (let i = 0; i < nodeCount; i++) {
      const node = document.getElementById(`tn-${i}`);
      if (node) node.className = 'trace-node active';

      // Show associated trace logs for this node
      const startIdx = i * logsPerNode;
      const endIdx   = Math.min(startIdx + logsPerNode, traceLogs.length);
      for (let j = startIdx; j < endIdx; j++) {
        const entry = traceLogs[j];
        const msg = typeof entry === 'string' ? entry : JSON.stringify(entry);
        this.addLog('info', msg);
        await this.sleep(200);
      }

      // If no logs for this node, just pause briefly
      if (startIdx >= traceLogs.length) {
        await this.sleep(300);
      }

      if (node) node.className = 'trace-node done';
      const conn = document.getElementById(`tc-${i}`);
      if (conn) conn.classList.add('filled');
      await this.sleep(100);
    }
  }

  /* ── Real-time Trace & WhatsApp Synchronization ───── */

  initTraceStream() {
    // 1. Server-Sent Events (SSE) for instant push
    if (window.EventSource) {
      try {
        const sse = new EventSource(`${API}/api/trace/stream`);
        sse.onmessage = (e) => {
          try {
            const evt = JSON.parse(e.data);
            this.handleTraceEvent(evt);
          } catch (err) {
            console.error('SSE parse error:', err);
          }
        };
        sse.onerror = () => {
          // EventSource will automatically attempt reconnection
        };
      } catch (err) {
        console.warn('EventSource init error:', err);
      }
    }

    // 2. High-reliability polling fallback every 1.5s
    setInterval(() => this.pollTraceEvents(), 1500);
  }

  async pollTraceEvents() {
    try {
      const res = await fetch(`${API}/api/trace/events?since_id=${this.lastTraceEventId}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.events && data.events.length > 0) {
        for (const evt of data.events) {
          if (evt.id > this.lastTraceEventId) {
            this.handleTraceEvent(evt);
          }
        }
      }
    } catch (e) {
      // ignore offline/transient errors
    }
  }

  handleTraceEvent(evt) {
    if (!evt || !evt.type) return;
    if (evt.id) {
      if (evt.id <= this.lastTraceEventId) return;
      this.lastTraceEventId = evt.id;
    }

    const { type, data } = evt;

    if (type === 'agent_start') {
      const agentKey = data.agent_key || 'campaign';
      this.currentAgentKey = agentKey;
      if (!this.running) {
        this.startAgentRun(agentKey);
      }
      this.addLog('info', `[START] ${data.title || 'Agent started'}`);
    }
    else if (type === 'node_step') {
      const agentKey = data.agent_key || this.currentAgentKey || 'campaign';
      if (!this.running) {
        this.startAgentRun(agentKey);
      }
      const nodeIdx = data.node_index;
      if (nodeIdx !== undefined && nodeIdx !== null) {
        // Mark all preceding nodes as completed
        for (let i = 0; i < nodeIdx; i++) {
          const prevNode = document.getElementById(`tn-${i}`);
          if (prevNode) prevNode.className = 'trace-node done';
          const prevConn = document.getElementById(`tc-${i}`);
          if (prevConn) prevConn.classList.add('filled');
        }
        // Activate current node
        const currNode = document.getElementById(`tn-${nodeIdx}`);
        if (currNode) currNode.className = 'trace-node active';
      }
      // Stream log line to Trace window
      this.addLog(data.color === 'red' ? 'error' : 'info', `[${data.node}] ${data.message}`);
    }
    else if (type === 'agent_finish') {
      const agentKey = data.agent_key || this.currentAgentKey || 'campaign';
      this.finishAgentRun(agentKey, data.status === 'error' ? 'error' : 'done');
      if (data.summary) {
        if (data.summary.anomalies !== undefined) {
          this.addImpact({ anomalies: data.summary.anomalies });
        }
        if (data.summary.health_score !== undefined) {
          this.addImpact({ reports: 1 });
        }
      }
      // Auto-refresh dashboard figures
      this.fetchDashboard();
    }
    else if (type === 'wa_message') {
      const role = data.role || 'received';
      const text = data.text || '';
      const extra = data.extra || {};

      if (extra.pdf_url) {
        const score = extra.health_score || 55;
        const pdfHtml = `
          <div class="wa-pdf-card" onclick="window.open('${extra.pdf_url}', '_blank')">
            <span class="wa-pdf-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
            </span>
            <div style="flex:1;min-width:0;">
              <div style="font-weight:600;font-size:11.5px;color:#111b21;">KiranaMate_Weekly_Report.pdf</div>
              <div style="font-size:9.5px;color:#667781;">Score: ${score}/100 &bull; ReportLab PDF</div>
            </div>
            <a href="${extra.pdf_url}" target="_blank" class="nav-pill-link" style="padding:3px 8px;font-size:10px;background:#ffffff;border:1px solid #c1c1c1;color:#111b21;">View</a>
          </div>
        `;
        this.addWAMsgHtml(role, pdfHtml);
      } else {
        this.addWAMsg(role, text);
      }
    }
  }

  /* ── Trace ─────────────────────────────────────────── */
  buildNodes(nodes) {
    const cont = document.getElementById('trace-nodes');
    cont.innerHTML = '';
    nodes.forEach((n, i) => {
      const el = document.createElement('div');
      el.className = 'trace-node'; el.id = `tn-${i}`;
      el.innerHTML = `<div class="trace-node-step">${n.step || String(i + 1).padStart(2, '0')}</div>
        <div class="trace-node-label">${n.label}</div>
        <div class="trace-node-check">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>`;
      cont.appendChild(el);
      if (i < nodes.length - 1) {
        const conn = document.createElement('div');
        conn.className = 'trace-connector'; conn.id = `tc-${i}`;
        conn.innerHTML = '<div class="trace-connector-fill"></div>';
        cont.appendChild(conn);
      }
    });
  }

  addLog(type, msg) {
    if (this._lastLogMsg === msg) return;
    this._lastLogMsg = msg;
    setTimeout(() => { if (this._lastLogMsg === msg) this._lastLogMsg = null; }, 1000);

    const log = document.getElementById('trace-log');
    const ts  = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
    const line = document.createElement('div');
    line.className = `trace-log-line ${type}`;
    // Truncate very long messages
    const displayMsg = msg.length > 120 ? msg.substring(0, 120) + '…' : msg;
    line.innerHTML = `<span class="log-ts">${ts}</span><span>${this.escapeHtml(displayMsg)}</span>`;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }

  clearTraceLog() { document.getElementById('trace-log').innerHTML = ''; }

  /* ── Timer ─────────────────────────────────────────── */
  startTimer() {
    this.timerSec = 0;
    const el = document.getElementById('trace-timer');
    this.timerRef = setInterval(() => {
      this.timerSec++;
      const m = String(Math.floor(this.timerSec / 60)).padStart(2, '0');
      const s = String(this.timerSec % 60).padStart(2, '0');
      el.textContent = `${m}:${s}`;
    }, 1000);
  }
  stopTimer() { clearInterval(this.timerRef); }

  /* ── WhatsApp Activity Feed ────────────────────────── */

  addWAMsg(type, text) {
    const key = `${type}:${text}`;
    if (this._lastWAMsg === key) return;
    this._lastWAMsg = key;
    setTimeout(() => { if (this._lastWAMsg === key) this._lastWAMsg = null; }, 1500);

    const cont = document.getElementById('wa-messages');
    const el   = document.createElement('div');
    const ts   = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });

    el.className = `wa-msg ${type}`;

    // Format text with newlines
    const formattedText = this.escapeHtml(text).replace(/\n/g, '<br>');

    if (type === 'system-msg' || type === 'error-msg' || type === 'success-msg') {
      el.innerHTML = formattedText;
    } else {
      el.innerHTML = `${formattedText}<div class="wa-msg-time">${ts}</div>`;
    }

    cont.appendChild(el);
    cont.scrollTop = cont.scrollHeight;
  }

  addWAMsgHtml(type, html) {
    const cont = document.getElementById('wa-messages');
    const el   = document.createElement('div');
    const ts   = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });

    el.className = `wa-msg ${type}`;
    el.innerHTML = `${html}<div class="wa-msg-time">${ts}</div>`;

    cont.appendChild(el);
    cont.scrollTop = cont.scrollHeight;
  }

  /* ── Impact ────────────────────────────────────────── */
  addImpact({ recovered = 0, customers = 0, anomalies = 0, reports = 0 }) {
    const prev = { ...this.impact };
    this.impact.recovered += recovered;
    this.impact.customers += customers;
    this.impact.anomalies += anomalies;
    this.impact.reports   += reports;

    if (recovered > 0)  this.animateCounter('impact-recovered', prev.recovered, this.impact.recovered, v => `₹${this.fmt(v)}`);
    if (customers > 0)  this.animateCounter('impact-customers', prev.customers, this.impact.customers, v => `${v}`);
    this.animateCounter('impact-units',     prev.anomalies,  this.impact.anomalies,  v => `${v}`);
    this.animateCounter('impact-time',      prev.reports,    this.impact.reports,     v => `${v}`);
  }

  resetImpact() {
    this.impact = { recovered: 0, customers: 0, anomalies: 0, reports: 0 };
    document.getElementById('impact-recovered').textContent = '₹0';
    document.getElementById('impact-customers').textContent = '0';
    document.getElementById('impact-units'    ).textContent = '0';
    document.getElementById('impact-time'     ).textContent = '0';
  }

  animateCounter(id, from, to, fmt) {
    const el  = document.getElementById(id);
    const dur = 1400;
    const t0  = performance.now();
    const tick = now => {
      const p = Math.min((now - t0) / dur, 1);
      const e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(Math.round(from + (to - from) * e));
      if (p < 1) requestAnimationFrame(tick);
      else {
        el.textContent = fmt(to);
        el.style.animation = 'countFlash .35s ease';
        setTimeout(() => { el.style.animation = ''; }, 350);
      }
    };
    requestAnimationFrame(tick);
  }

  /* ── Helpers ───────────────────────────────────────── */
  setBtnsDisabled(dis, activeKey) {
    const map = { campaign: 'btn-campaign', monitor: 'btn-monitor', report: 'btn-report' };
    Object.entries(map).forEach(([k, id]) => {
      const btn = document.getElementById(id);
      btn.disabled = dis;
      if (dis && k === activeKey) btn.classList.add('running');
      else btn.classList.remove('running');
    });
    // Also disable the campaign input
    const input = document.getElementById('campaign-goal-input');
    if (input) input.disabled = dis;
  }

  setApiStatus(state) {
    const el = document.getElementById('api-status');
    el.className = `api-status ${state}`;
    el.querySelector('.status-text').textContent = state === 'connected' ? 'API Connected' : 'API Offline';
  }

  _setChip(indId, chipId, color, label) {
    const ind = document.getElementById(indId), chip = document.getElementById(chipId);
    if (!ind || !chip) return;
    ind.className  = `status-indicator ${color}${color === 'green' ? ' pulse' : ''}`;
    chip.className = `status-chip ${color}`;
    chip.textContent = label;
  }

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  fmt(n) {
    if (n >= 100000) return (n / 100000).toFixed(1) + 'L';
    if (n >= 1000)   return (n / 1000).toFixed(1) + 'K';
    return Math.round(n).toString();
  }

  /* ── ScrollSpy & Dynamic Section Tabs ──────────────────── */
  initScrollSpyAndProgress() {
    const tabs = Array.from(document.querySelectorAll('.nav-tab'));

    const sectionMap = [
      { id: 'overview', tab: tabs.find(t => t.getAttribute('data-target') === 'overview') },
      { id: 'agents',   tab: tabs.find(t => t.getAttribute('data-target') === 'agents') },
      { id: 'ledger',   tab: tabs.find(t => t.getAttribute('data-target') === 'ledger') },
    ].filter(item => item.tab);

    const setActiveTab = (targetTab) => {
      if (!targetTab) return;
      tabs.forEach(t => t.classList.remove('active'));
      targetTab.classList.add('active');
    };

    // Smooth scroll on tab click
    tabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = tab.getAttribute('data-target');
        const el = document.getElementById(targetId);
        if (el) {
          const headerHeight = 78;
          const targetY = el.getBoundingClientRect().top + window.pageYOffset - headerHeight;
          window.scrollTo({ top: Math.max(0, targetY), behavior: 'smooth' });
          setActiveTab(tab);
          if (history.replaceState) {
            history.replaceState(null, null, `#${targetId}`);
          }
        }
      });
    });

    // Scroll listener for ScrollSpy
    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollY = window.pageYOffset || document.documentElement.scrollTop;
          const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
          const scrollPct = Math.min(100, Math.max(0, (scrollY / maxScroll) * 100));

          // ScrollSpy: determine which section is currently active
          const threshold = window.innerHeight * 0.35;
          let currentActiveTab = sectionMap[0]?.tab;

          for (const item of sectionMap) {
            const el = document.getElementById(item.id);
            if (el) {
              const top = el.getBoundingClientRect().top;
              if (top <= threshold) {
                currentActiveTab = item.tab;
              }
            }
          }

          // If scrolled near the bottom, highlight the last tab
          if (scrollPct > 85 && sectionMap.length > 0) {
            currentActiveTab = sectionMap[sectionMap.length - 1].tab;
          }

          if (currentActiveTab) {
            setActiveTab(currentActiveTab);
          }

          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', onScroll, { passive: true });

    // Initial positioning based on hash or active tab
    setTimeout(() => {
      const initialHash = window.location.hash.replace('#', '');
      const match = sectionMap.find(s => s.id === initialHash);
      const active = match ? match.tab : (document.querySelector('.nav-tab.active') || tabs[0]);
      setActiveTab(active);
      onScroll();
    }, 120);
  }

  cap(s) { return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
  sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
}

/* ── Boot ─────────────────────────────────────────────── */
const dashboard = new KiranateDashboard();
document.addEventListener('DOMContentLoaded', () => {
  dashboard.init().catch(err => {
    console.error('Dashboard init error:', err);
    dashboard.setApiStatus('error');
  });
});
