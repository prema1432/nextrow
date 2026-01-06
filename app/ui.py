UI_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Adobe Analytics Website Scanner</title>
  <style>
    body{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial; margin:24px; color:#111827; background:#f8fafc;}
    h1{font-size:20px; margin:0 0 12px;}
    .card{border:1px solid #e5e7eb; border-radius:12px; padding:16px; margin:12px 0;}
    label{display:block; font-size:12px; color:#374151; margin-bottom:6px;}
    input{width:100%; padding:12px 14px; border:1px solid #d1d5db; border-radius:10px; font-size:14px; background:#fff; transition:border .2s ease, box-shadow .2s ease;}
    input:focus{border-color:#4f46e5; box-shadow:0 0 0 3px rgba(79,70,229,.2); outline:none;}
    .row{display:grid; grid-template-columns: 1fr 160px 160px 140px; gap:12px; align-items:start;}
    .exampleBar{display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:8px;}
    .row > div{display:flex; flex-direction:column;}
    .btn{display:inline-flex; align-items:center; justify-content:center; gap:6px; padding:8px 10px; border-radius:10px; border:1px solid #d1d5db; background:#111827; color:#fff; cursor:pointer; font-size:13px; line-height:1; text-decoration:none;}
    .btn.primary{background:linear-gradient(135deg,#6366f1,#a855f7); border:none; box-shadow:0 12px 24px rgba(99,102,241,.25); font-weight:600; letter-spacing:.02em; text-transform:uppercase;}
    .btn.primary:hover{box-shadow:0 16px 30px rgba(99,102,241,.35); transform:translateY(-1px);}
    .btn.secondary{background:#fff; color:#111827;}
    .btn.danger{background:#b91c1c; border-color:#b91c1c;}
    .btn.icon{padding:8px 10px; width:38px;}
    .btn.disabled{opacity:.55; cursor:not-allowed; pointer-events:none;}
    table{width:100%; border-collapse:collapse; font-size:13px;}
    th,td{border-bottom:1px solid #e5e7eb; padding:10px 8px; text-align:left; vertical-align:top;}
    th{font-size:12px; color:#374151;}
    .muted{color:#6b7280; font-size:12px;}
    .actions{display:flex; gap:8px; flex-wrap:wrap; align-items:center;}
    .pill{display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; border:1px solid #e5e7eb;}
    .overlay{position:fixed; inset:0; background:rgba(17,24,39,.55); display:none; align-items:center; justify-content:center; padding:16px;}
    .modal{width:min(1100px, 96vw); max-height:88vh; background:#fff; border-radius:12px; border:1px solid #e5e7eb; overflow:hidden; display:flex; flex-direction:column;}
    .modalHeader{display:flex; justify-content:space-between; align-items:center; padding:12px 14px; border-bottom:1px solid #e5e7eb;}
    .modalTitle{font-weight:600; font-size:14px;}
    .modalBody{padding:12px 14px; overflow:auto;}
    pre{white-space:pre-wrap; word-break:break-word; font-size:12px; line-height:1.45; margin:0;}
    svg{display:block;}
    @media (max-width: 860px){
      .row{grid-template-columns: 1fr;}
    }
  </style>
</head>
<body>
  <h1>Adobe Analytics Website Scanner</h1>
  <div class=\"muted\">Run scans, track status, delete scans, and download Excel reports.</div>

  <div class=\"card\">
    <div class=\"row\">
      <div>
        <label>Start URL</label>
        <input id=\"startUrl\" value=\"\" placeholder=\"https://www.skyrizi.com/\" />
        <div class=\"exampleBar\">
          <button class=\"btn secondary\" type=\"button\" id=\"exampleSkyrizi\">Example: SkyRIZI</button>
          <button class=\"btn secondary\" type=\"button\" id=\"exampleHomeDepot\">Example: HomeDepot</button>
        </div>
      </div>
      <div>
        <label>Max Pages</label>
        <input id=\"maxPages\" type=\"number\" min=\"1\" value=\"10\" />
      </div>
      <div>
        <label>Max Clicks/Page</label>
        <input id=\"maxClicks\" type=\"number\" min=\"0\" value=\"3\" />
      </div>
      <div>
        <button id=\"startBtn\">Start Scan</button>
      </div>
    </div>
    <div style=\"margin-top:10px\" class=\"muted\" id=\"startMsg\"></div>
  </div>

  <div class=\"card\">
    <div style=\"display:flex; justify-content:space-between; align-items:center; gap:12px;\">
      <div>
        <div style=\"font-weight:600\">Scans</div>
        <div class=\"muted\">Refresh to see latest status.</div>
      </div>
      <div class=\"actions\">
        <button class=\"btn danger\" id=\"deleteAllBtn\">Delete All</button>
        <button class=\"btn secondary\" id=\"refreshBtn\">Refresh</button>
      </div>
    </div>
    <div style=\"margin-top:12px; overflow:auto;\">
      <table>
        <thead>
          <tr>
            <th>Scan ID</th>
            <th>Start URL</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Start Time</th>
            <th>End Time</th>
            <th>Duration (s)</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id=\"scanRows\"></tbody>
      </table>
    </div>
  </div>

  <div class=\"overlay\" id=\"overlay\" role=\"dialog\" aria-modal=\"true\">
    <div class=\"modal\">
      <div class=\"modalHeader\">
        <div class=\"modalTitle\" id=\"modalTitle\">JSON Data</div>
        <div class=\"actions\">
          <button class=\"btn secondary\" id=\"copyBtn\">Copy</button>
          <button class=\"btn secondary\" id=\"closeBtn\">Close</button>
        </div>
      </div>
      <div class=\"modalBody\">
        <pre id=\"jsonPre\"></pre>
      </div>
    </div>
  </div>

<script>
  const el = (id) => document.getElementById(id);

  async function api(path, opts = {}) {
    const res = await fetch(path, opts);
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (!res.ok) {
      const msg = (data && data.detail) ? data.detail : (typeof data === 'string' ? data : 'Request failed');
      throw new Error(msg);
    }
    return data;
  }

  function statusPill(status) {
    return `<span class=\"pill\">${status || ''}</span>`;
  }

  function fmtTs(ts) {
    if (!ts) return '';
    try {
      return new Date(ts * 1000).toLocaleString();
    } catch {
      return '';
    }
  }

  const eyeSvg = `
    <svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">
      <path d=\"M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>
      <path d=\"M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>
    </svg>`;

  function renderRows(scans) {
    const rows = scans.map(s => {
      const scanId = s._id || '';
      const startUrl = s.start_url || '';
      const status = s.status || '';
      const progress = `${s.pages_scanned || 0}/${s.total_pages || 0}`;
      const startedAt = fmtTs(s.started_at);
      const completedAt = fmtTs(s.completed_at);
      const duration = (s.duration_seconds !== null && s.duration_seconds !== undefined) ? String(s.duration_seconds) : '';

      const canDownload = status === 'completed';
      const dlFull = canDownload ? `<a class=\"btn secondary\" href=\"/report/${scanId}\" target=\"_blank\" rel=\"noopener\">Full XLSX</a>` : `<span class=\"btn secondary disabled\">Full XLSX</span>`;
      const dlSimple = canDownload ? `<a class=\"btn secondary\" href=\"/report/${scanId}/simple\" target=\"_blank\" rel=\"noopener\">Simple XLSX</a>` : `<span class=\"btn secondary disabled\">Simple XLSX</span>`;
      const viewJson = canDownload ? `<button class=\"btn secondary icon\" title=\"View JSON\" data-view=\"${scanId}\">${eyeSvg}</button>` : `<span class=\"btn secondary icon disabled\">${eyeSvg}</span>`;
      const retryBtn = (status === 'running' || status === 'queued') ? `<span class=\"btn secondary disabled\">Retry</span>` : `<button class=\"btn secondary\" data-retry=\"${scanId}\">Retry</button>`;

      return `
        <tr>
          <td style=\"font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas;\">${scanId}</td>
          <td style=\"max-width:360px; word-break:break-word;\">${startUrl}</td>
          <td>${statusPill(status)}</td>
          <td>${progress}</td>
          <td class=\"muted\">${startedAt}</td>
          <td class=\"muted\">${completedAt}</td>
          <td>${duration}</td>
          <td>
            <div class=\"actions\">
              ${viewJson}
              ${retryBtn}
              ${dlSimple}
              ${dlFull}
              <button class=\"btn danger\" data-del=\"${scanId}\">Delete</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    el('scanRows').innerHTML = rows || `<tr><td colspan=\"8\" class=\"muted\">No scans yet</td></tr>`;

    document.querySelectorAll('button[data-del]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-del');
        if (!id) return;
        if (!confirm(`Delete scan ${id}? This will remove scan/pages/report from DB.`)) return;
        btn.disabled = true;
        try {
          await api(`/scan/${id}`, { method: 'DELETE' });
          await loadScans();
        } catch (e) {
          alert(e.message);
        } finally {
          btn.disabled = false;
        }
      });
    });

    document.querySelectorAll('button[data-view]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-view');
        if (!id) return;
        btn.disabled = true;
        try {
          const data = await api(`/report/${id}/data`);
          openModal(`Report JSON - ${id}`, data);
        } catch (e) {
          alert(e.message);
        } finally {
          btn.disabled = false;
        }
      });
    });

    document.querySelectorAll('button[data-retry]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-retry');
        if (!id) return;
        if (!confirm(`Retry scan ${id}? This will create a new scan with the same inputs.`)) return;
        btn.disabled = true;
        try {
          const out = await api(`/scan/${id}/retry`, { method: 'POST' });
          el('startMsg').textContent = `Retry started: ${out.scan_id}`;
          setTimeout(() => { el('startMsg').textContent = ''; }, 2500);
          await loadScans();
        } catch (e) {
          alert(e.message);
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function openModal(title, jsonObj) {
    el('modalTitle').textContent = title || 'JSON Data';
    el('jsonPre').textContent = JSON.stringify(jsonObj, null, 2);
    el('overlay').style.display = 'flex';
  }

  function closeModal() {
    el('overlay').style.display = 'none';
    el('jsonPre').textContent = '';
  }

  async function loadScans() {
    const data = await api('/scans?limit=50');
    renderRows(data.scans || []);
  }

  el('refreshBtn').addEventListener('click', async () => {
    try { await loadScans(); } catch (e) { alert(e.message); }
  });

  el('deleteAllBtn').addEventListener('click', async () => {
    if (!confirm('Delete ALL scans, pages and reports? This cannot be undone.')) return;
    el('deleteAllBtn').disabled = true;
    try {
      await api('/scans', { method: 'DELETE' });
      await loadScans();
    } catch (e) {
      alert(e.message);
    } finally {
      el('deleteAllBtn').disabled = false;
    }
  });

  el('startBtn').addEventListener('click', async () => {
    el('startBtn').disabled = true;
    el('startMsg').textContent = '';
    try {
      const start_url = el('startUrl').value.trim();
      const max_pages = parseInt(el('maxPages').value, 10);
      const max_clicks_per_page = parseInt(el('maxClicks').value, 10);
      const qs = new URLSearchParams({ start_url, max_pages, max_clicks_per_page });
      const out = await api(`/scan?${qs.toString()}`, { method: 'POST' });
      el('startMsg').textContent = `Scan started: ${out.scan_id}`;
      el('startUrl').value = '';
      el('startUrl').focus();
      setTimeout(() => { el('startMsg').textContent = ''; }, 2500);
      await loadScans();
    } catch (e) {
      el('startMsg').textContent = e.message;
    } finally {
      el('startBtn').disabled = false;
    }
  });

  el('closeBtn').addEventListener('click', closeModal);

  el('exampleSkyrizi').addEventListener('click', () => {
    el('startUrl').value = 'https://www.skyrizi.com/';
    el('startUrl').focus();
  });
  el('exampleHomeDepot').addEventListener('click', () => {
    el('startUrl').value = 'https://www.homedepot.ca/';
    el('startUrl').focus();
  });
  el('overlay').addEventListener('click', (evt) => {
    if (evt.target && evt.target.id === 'overlay') closeModal();
  });
  document.addEventListener('keydown', (evt) => {
    if (evt.key === 'Escape') closeModal();
  });
  el('copyBtn').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(el('jsonPre').textContent || '');
    } catch (e) {
      alert('Copy failed');
    }
  });

  loadScans().catch(() => {});
</script>
</body>
</html>"""
