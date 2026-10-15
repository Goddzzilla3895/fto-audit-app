
function teamRightsTable() {
  const rows = S.lists.team || [];
  const host = window.location.origin;
  return `
    <div class="tw">
      <table class="t">
        <thead>
          <tr>
            <th style="width:150px">Auditor Name</th>
            <th style="width:170px">Email ID</th>
            <th style="width:110px">Role</th>
            <th style="width:140px">Assigned Aerodrome(s)</th>
            <th style="width:280px">Assigned Section Rights (Click to Toggle)</th>
            <th style="width:100px">Access Link</th>
            <th style="width:35px"></th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r, i) => {
            const directUrl = r.role === 'Lead Auditor' ? `${host}/master` : `${host}/auditor${i}`;
            return `<tr>
              <td><input type="text" data-b="lists.team.${i}.name" value="${esc(r.name)}" placeholder="Full Name"></td>
              <td><input type="text" data-b="lists.team.${i}.email" value="${esc(r.email || '')}" placeholder="auditor@marigoldaviation.com"></td>
              <td>
                <select data-b="lists.team.${i}.role">
                  <option value="Lead Auditor" ${r.role==='Lead Auditor'?'selected':''}>Lead Auditor</option>
                  <option value="Auditor" ${r.role!=='Lead Auditor'?'selected':''}>Auditor</option>
                </select>
              </td>
              <td>
                <select data-b="lists.team.${i}.base">
                  <option value="All Aerodromes" ${(!r.base || r.base==='All Aerodromes')?'selected':''}>All Aerodromes</option>
                  ${(S.lists.locations || []).map(l => `<option value="${esc(l.name)}" ${r.base===l.name?'selected':''}>${esc(l.name)}</option>`).join('')}
                </select>
              </td>
              <td>
                <div style="display:flex;flex-wrap:wrap;gap:4px">
                  ${SECTIONS.map(s => {
                    const isAssigned = (r.name && (S.secs[s.id].auditor || '').trim().toLowerCase() === r.name.trim().toLowerCase());
                    return `<button type="button" class="btn sm ${isAssigned ? 'pri' : ''}" style="padding:2px 6px;font-size:11px" data-toggle-sec="${i}|${s.id}" title="${esc(s.title)}">${s.id} ${isAssigned ? '✓' : ''}</button>`;
                  }).join('')}
                </div>
              </td>
              <td>
                <button type="button" class="btn sm" onclick="navigator.clipboard.writeText('${directUrl}');toast('Copied access link for ${esc(r.name)}');" title="Copy URL">📋 Copy Link</button>
              </td>
              <td><button class="btn sm danger" data-lrm="team.${i}" title="Remove auditor">✕</button></td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
    <div style="display:flex;gap:10px;margin-top:8px;align-items:center">
      <button class="btn sm" data-ladd="team">+ Add team member</button>
      <span class="help">Click section chips to assign section rights to each person.</span>
    </div>
  `;
}

/* ============================================================
   FTO AUDIT TOOL – application logic
   Two editions from one code base:
     MASTER  – lead auditor: set-up, create auditor files, import, integrate, report
     AUDITOR – one per auditor: completes assigned sections, exports a file for the master
   ============================================================ */
const APPV = 2;
const CFG = window.CFG || {mode: 'master'};
const MASTER = CFG.mode !== 'auditor';
const PRISTINE = '<!DOCTYPE html>\n' + document.documentElement.outerHTML; // this tool's own source – used for "Save progress" copies and for creating auditor files
const SAVED_RE = /<script id="saved">[\s\S]*?<\/script>/;
const embedJSON = o => JSON.stringify(o).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
const withSaved = (html, payload) => html.replace(SAVED_RE, () => '<script id="saved">window.SAVED=' + (payload ? embedJSON(payload) : 'null') + ';<\/script>');
let dirty = false;
const $ = s => document.querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = o => JSON.parse(JSON.stringify(o));
const uid = () => 'f' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
const SEC = Object.fromEntries(SECTIONS.map(s => [s.id, s]));
const DEFAULT_SPLIT = {'Auditor 1': ['ORG', 'FO', 'SMS', 'FDM', 'ATS'], 'Auditor 2': ['TRG', 'QA', 'ACC', 'NB'], 'Auditor 3': ['ENG', 'CAM', 'FLT', 'INF']};

function freshState() {
  const st = {v: APPV, meta: {auditingOrg: '', auditedOrg: '', approvalNo: '', from: '', to: '',
    title: 'Operational, Safety and Regulatory Due Diligence Audit',
    type: 'Operational, safety, engineering and quality due diligence audit',
    framework: 'DGCA India FTO requirements, applicable CARs and international best practice',
    status: 'Draft', classification: 'Confidential – Commercial in Confidence',
    distribution: 'Management of the commissioning organisation. Confidential – not for onward distribution without written authorisation.'},
    text: clone(DEFAULT_TEXT), lists: clone(DEFAULT_LISTS), secs: {}, items: {}, files: {}, genAtt: [], imports: [], inputs: {}, me: null};
  SECTIONS.forEach(s => st.secs[s.id] = {on: true, auditor: '', comment: '', att: [], custom: []});
  if (MASTER) {
    st.lists.team = [{name: '', role: 'Lead Auditor'}, {name: '', role: 'Auditor'}, {name: '', role: 'Auditor'}];
  } else {
    st.me = Object.assign({name: '', role: 'Auditor', label: 'Auditor', sections: []}, clone(CFG.me || {}));
    const seed = CFG.seed || {};
    if (seed.meta) Object.assign(st.meta, seed.meta);
    if (seed.lists) Object.entries(seed.lists).forEach(([k, v]) => { if (v && v.length) st.lists[k] = v; });
    if (seed.custom) Object.entries(seed.custom).forEach(([k, v]) => { if (st.secs[k]) st.secs[k].custom = v; });
    applyMe(st);
  }
  return st;
}
function applyMe(st) { // auditor edition: only assigned sections are "on"; section auditor = me
  SECTIONS.forEach(s => { const mine = st.me.sections.includes(s.id); st.secs[s.id].on = mine; if (mine) st.secs[s.id].auditor = st.me.name || st.me.label; });
}
const secAuditors = sid => { const ss = S.secs[sid]; return [...new Set([ss.auditor, ss.auditor2].concat(ss.co || []).filter(Boolean))].join(' & '); };
const meName = () => S.me ? (S.me.name || S.me.label || 'Auditor') : '';
let S = freshState();
let view = 'dash';

/* ---------- item helpers ---------- */
const itemsOf = sid => SEC[sid].items.concat((S.secs[sid] && S.secs[sid].custom) || []);
const itemDef = id => { for (const s of SECTIONS) for (const it of itemsOf(s.id)) if (it[0] === id) return {sec: s, def: it}; return null; };
const rec = id => S.items[id] || (S.items[id] = {att: []});
const findText = (r, d) => r.find || `${r.r ? RES[r.r] : 'Finding'} – ${d[1]}`;
const isFinding = (sec, r) => sec.type === 'check' && r && r.cls;
const META_KEYS = ['att', 'by', 'at', 'mEdit'];
const hasContent = r => r && Object.entries(r).some(([k, v]) => k === 'att' ? v && v.length : (!META_KEYS.includes(k) && v !== '' && v != null));
function refFiles() { const set = new Set(S.genAtt); SECTIONS.forEach(s => (S.secs[s.id].att || []).forEach(i => set.add(i))); Object.values(S.items).forEach(r => (r.att || []).forEach(i => set.add(i))); return set; }
function gcFiles() { const set = refFiles(); Object.keys(S.files).forEach(id => { if (!set.has(id)) delete S.files[id]; }); }

function stats() {
  const out = {tot: 0, done: 0, res: {C: 0, P: 0, NC: 0, NE: 0, NA: 0}, findings: [], bySec: {}, files: 0};
  SECTIONS.forEach(sec => {
    const ss = S.secs[sec.id]; if (!ss.on) return;
    const b = out.bySec[sec.id] = {tot: 0, done: 0, res: {C: 0, P: 0, NC: 0, NE: 0, NA: 0}, f: 0, maxRisk: '', rdy: {}};
    itemsOf(sec.id).forEach(d => {
      const r = S.items[d[0]] || {}; b.tot++;
      if (r.r) { b.done++; if (sec.type === 'check') b.res[r.r]++; else b.rdy[r.r] = (b.rdy[r.r] || 0) + 1; }
      if (isFinding(sec, r)) {
        b.f++; out.findings.push({id: d[0], sec: sec.id, def: d, r});
        const rk = {H: 3, M: 2, L: 1, '': 0}; if ((rk[r.risk] || 0) > (rk[b.maxRisk] || 0)) b.maxRisk = r.risk;
      }
    });
    if (sec.type === 'check') { out.tot += b.tot; out.done += b.done; Object.keys(b.res).forEach(k => out.res[k] += b.res[k]); }
  });
  out.files = refFiles().size;
  return out;
}

/* ---------- persistence (IndexedDB autosave; best effort) ---------- */
const DBKEY = MASTER ? 'master' : 'auditor:' + (CFG.instanceId || 'x');
let dbp = null;
function db() {
  if (dbp) return dbp;
  dbp = new Promise((res, rej) => {
    try { const q = indexedDB.open('fto-audit-tool', 1);
      q.onupgradeneeded = () => q.result.createObjectStore('kv');
      q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error);
    } catch (e) { rej(e); }
  });
  return dbp;
}
let saveT = null; let autoOK = null;
const hhmm = iso => iso ? new Date(iso).toLocaleString([], {day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'}) : '';
function markDirty(v) {
  dirty = v; const el = $('#saveInd'); if (!el) return;
  const fileTxt = S.fileSavedAt ? 'Saved ' + hhmm(S.fileSavedAt) : 'Ready';
  el.innerHTML = dirty ? `<b style="color:#ffd27a">● Saving...</b><br><span style="opacity:.8">Syncing to OneDrive & Excel</span>`
    : `✓ ${fileTxt}<br><span style="opacity:.8">OneDrive & Excel Synced</span>`;
}
async function saveProgress() {
  S.fileSavedAt = new Date().toISOString(); S.edited = S.edited || S.fileSavedAt;
  markDirty(true);
  try {
    const resp = await fetch('/api/save', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({state: S})
    });
    if (resp.ok) {
      const data = await resp.json();
      markDirty(false);
      toast('Saved: All entries and images synced to OneDrive & Excel updated.');
    }
  } catch (e) {
    console.error(e);
    toast('Error syncing to server: ' + e.message);
  }
}
function save() {
  S.edited = new Date().toISOString(); markDirty(true);
  clearTimeout(saveT);
  saveT = setTimeout(async () => {
    try {
      // 1. IndexedDB backup
      try { const d = await withTimeout(db(), 1000); if (d) { const tx = d.transaction('kv', 'readwrite'); tx.objectStore('kv').put(S, DBKEY); } } catch (e) {}
      // 2. Background REST auto-save
      const resp = await fetch('/api/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({state: S})
      });
      if (resp.ok) {
        autoOK = true;
        markDirty(false);
      } else {
        autoOK = false;
      }
    } catch (e) { autoOK = false; markDirty(dirty); }
  }, 500);
}
const withTimeout = (p, ms) => Promise.race([p, new Promise(r => setTimeout(() => r(null), ms))]);
async function load() {
  try {
    const res = await withTimeout(fetch('/api/state'), 3000);
    if (res && res.ok) {
      const data = await res.json();
      if (data.state && Object.keys(data.state).length) return data.state;
    }
  } catch (e) {}
  return withTimeout(load0(), 2000);
}
async function load0() {
  try { const d = await db(); return await new Promise(res => { const q = d.transaction('kv').objectStore('kv').get(DBKEY); q.onsuccess = () => res(q.result); q.onerror = () => res(null); }); }
  catch (e) { return null; }
}
function normalise(st) {
  const f = freshState();
  st = Object.assign(f, st || {});
  st.meta = Object.assign(freshState().meta, st.meta || {});
  st.text = Object.assign(clone(DEFAULT_TEXT), st.text || {});
  st.lists = Object.assign(clone(DEFAULT_LISTS), st.lists || {});
  SECTIONS.forEach(s => st.secs[s.id] = Object.assign({on: true, auditor: '', comment: '', att: [], custom: []}, st.secs[s.id] || {}));
  st.items = st.items || {}; st.files = st.files || {}; st.genAtt = st.genAtt || []; st.imports = st.imports || []; st.inputs = st.inputs || {};
  if (st.conflicts && st.conflicts.length) { st.conflicts.forEach(c => { const l = st.items[c.id]; if (l && l.by) { st.inputs[c.id] = st.inputs[c.id] || {}; if (!st.inputs[c.id][l.by]) st.inputs[c.id][l.by] = Object.assign({}, l); } (st.inputs[c.id] = st.inputs[c.id] || {})[c.from] = c.inc; }); }
  delete st.conflicts;
  if (!MASTER) {
    st.me = Object.assign({name: '', role: 'Auditor', label: 'Auditor', sections: []}, clone(CFG.me || {}), st.me || {});
    const team = st.lists.team || [];
    const tIdx = (CFG.instanceId && CFG.instanceId.startsWith('A')) ? parseInt(CFG.instanceId.slice(1), 10) : -1;
    let member = (tIdx > 0 && team[tIdx]) ? team[tIdx] : null;
    if (!member) {
      member = team.find(t => t.name && ((st.me.name && t.name.trim().toLowerCase() === st.me.name.trim().toLowerCase()) || t.role === st.me.label));
    }
    if (member && member.name) {
      st.me.name = member.name.trim();
      st.me.email = member.email || '';
      st.me.role = member.role || st.me.label || 'Auditor';
    }
    if (st.me.name) {
      const mySecs = SECTIONS.filter(s => {
        const secAud = (st.secs[s.id] && st.secs[s.id].auditor || '').trim().toLowerCase();
        return secAud === st.me.name.trim().toLowerCase();
      }).map(s => s.id);
      if (mySecs.length > 0) {
        st.me.sections = mySecs;
      }
    }
    applyMe(st);
  }
  return st;
}

/* ---------- toast / download ---------- */
function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('on'); clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('on'), 3200); }
function download(blob, name) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 60000);
}
const slug = s => (s || 'FTO').replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40) || 'FTO';
const today = () => new Date().toISOString().slice(0, 10);
const fmtDate = d => { if (!d) return ''; const x = new Date(d + 'T00:00:00'); return isNaN(x) ? d : x.toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'}); };

/* ---------- NAV ---------- */
function navList() {
  if (MASTER) return {top: [['dash', 'Master dashboard'], ['data', 'Auditor files: create & import'], ['multi', 'Multi-auditor items'], ['info', 'Audit information & team'], ['exec', 'Executive summary & conclusion']],
    bottom: [['reg', 'Findings register'], ['cap', 'Corrective action programme']]};
  return {top: [['dash', 'My progress'], ['info', 'Me & my sections'], ['send', 'Send my work to the lead auditor']], bottom: [['reg', 'My findings']]};
}
function navHTML() {
  const st = stats(); const L = navList();
  const link = (v, label, extra = '') => `<a data-go="${v}" class="${view === v ? 'on' : ''}">${label}${extra}</a>`;
  const badge = v => v === 'multi' && pendingCount() ? ` <span class="pill pH">${pendingCount()}</span>` : (v === 'reg' ? ` <span class="chip">${st.findings.length}</span>` : '');
  let h = '<div class="grp">' + (MASTER ? 'Master' : 'Auditor: ' + esc(meName())) + '</div>' + L.top.map(([v, l]) => link(v, l, badge(v))).join('');
  h += '<div class="grp">' + (MASTER ? 'Checklist sections' : 'My checklist sections') + '</div>';
  SECTIONS.forEach(s => {
    const ss = S.secs[s.id]; const b = st.bySec[s.id];
    if (!ss.on) { if (MASTER) h += `<a data-go="${s.id}" class="${view === s.id ? 'on' : ''}" style="opacity:.5">${esc(s.title)} <span class="chip">off</span></a>`; return; }
    const pct = b.tot ? Math.round(b.done / b.tot * 100) : 0;
    h += `<a data-go="${s.id}" class="${view === s.id ? 'on' : ''}">${esc(s.title)}<div class="meta"><span>${b.done}/${b.tot}${MASTER && ss.auditor ? ' · ' + esc(secAuditors(s.id)) : ''}</span><span>${b.f ? b.f + ' finding' + (b.f > 1 ? 's' : '') : ''}</span></div><div class="pb"><i style="width:${pct}%"></i></div></a>`;
  });
  if (!MASTER && !S.me.sections.length) h += '<div class="help" style="padding:4px 16px">No sections selected yet – open “Me & my sections”.</div>';
  h += '<div class="grp">Outputs</div>' + L.bottom.map(([v, l]) => link(v, l, badge(v))).join('');
  return h;
}
function mnavHTML() {
  const L = navList();
  const o = L.top.concat(SECTIONS.filter(s => MASTER || S.secs[s.id].on).map(s => [s.id, s.title])).concat(L.bottom);
  return '<select id="mnavSel">' + o.map(([v, l]) => `<option value="${v}" ${v === view ? 'selected' : ''}>${esc(l)}</option>`).join('') + '</select>';
}
function headerHTML() {
  if (MASTER) return `<h1>FTO Audit – MASTER Dashboard<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Save to OneDrive">💾 Save progress</button><button class="btn" data-act="excel" title="Download Excel with embedded links">📊 Excel report</button><button class="btn" data-act="merge">⤵ Import auditor files</button><button class="btn" data-act="docx">⬇ Word report</button><button class="btn hl" data-act="print">🖨 Print / PDF</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button><a href="/logout" class="btn" style="text-decoration:none;background:rgba(255,255,255,0.15);color:#fff" title="Sign out of Microsoft 365">🚪 Sign out</a></div>`;
  const isLead = (CFG.currentUser && (CFG.currentUser.role === 'Lead Auditor' || String(CFG.currentUser.name || '').toLowerCase().includes('sunny') || String(CFG.currentUser.email || '').toLowerCase().includes('sunny')));
  const switchBtn = isLead ? `<a href="/master" class="btn hl" style="text-decoration:none;background:#2b3585;color:#fff">👑 Switch to Master Dashboard</a>` : '';
  return `<h1>FTO Audit – Auditor: ${esc(meName())}<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb">${switchBtn}<button class="btn hl" data-act="fsave" title="Save to OneDrive">💾 Save progress</button><button class="btn" data-act="excel" title="Download Excel with embedded links">📊 Excel report</button><button class="btn" data-act="aopen">📂 Load saved work</button><button class="btn" data-act="print">🖨 Print my sections</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button><a href="/logout" class="btn" style="text-decoration:none;background:rgba(255,255,255,0.15);color:#fff" title="Sign out of Microsoft 365">🚪 Sign out</a></div>`;
}
function refreshNav() {
  // patch existing nodes in place so a click that is in progress on a nav link is not lost
  const side = $('#side'); const tmp = document.createElement('div'); tmp.innerHTML = navHTML();
  if (side.children.length === tmp.children.length) {
    [...tmp.children].forEach((n, i) => { const o = side.children[i]; if (o.innerHTML !== n.innerHTML) o.innerHTML = n.innerHTML; o.className = n.className; o.style.cssText = n.style.cssText; });
  } else side.innerHTML = tmp.innerHTML;
  $('#mnav').innerHTML = mnavHTML();
}
function go(v) { view = v; render(); window.scrollTo(0, 0); }

/* ---------- field helpers ---------- */
const fld = (path, label, val, type = 'text', ph = '') => `<div><label class="f">${label}</label>${type === 'area'
  ? `<textarea data-b="${path}" placeholder="${esc(ph)}">${esc(val)}</textarea>`
  : `<input type="${type}" data-b="${path}" value="${esc(val)}" placeholder="${esc(ph)}">`}</div>`;
const sel = (path, opts, val, blank = '—') => `<select data-b="${path}"><option value="">${blank}</option>${Object.entries(opts).map(([k, v]) => `<option value="${k}" ${k === val ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>`;

function listTable(name, note = '') {
  const cols = LIST_COLS[name]; const rows = S.lists[name] || [];
  const colW = Math.max(130, Math.floor(660 / (cols.length || 1)));
  return `<div class="tw"><table class="t"><thead><tr>${cols.map(c => `<th style="width:${colW}px">${c[1]}</th>`).join('')}<th style="width:40px"></th></tr></thead><tbody>${rows.map((r, i) =>
    `<tr>${cols.map(c => `<td><input type="text" data-b="lists.${name}.${i}.${c[0]}" value="${esc(r[c[0]])}"></td>`).join('')}<td><button class="btn sm danger" data-lrm="${name}.${i}" title="Remove row">✕</button></td></tr>`).join('')}</tbody></table></div>
    <button class="btn sm" data-ladd="${name}" style="margin-top:6px">+ Add row</button>${note ? `<div class="help" style="margin-top:4px">${note}</div>` : ''}`;
}

/* ---------- attachments ---------- */
function attHTML(key, ids) {
  ids = ids || [];
  const th = ids.filter(id => S.files[id]).map(id => {
    const f = S.files[id]; let vis;
    if (f.kind === 'image') vis = `<img src="${f.d}" data-zoom="${id}" alt="">`;
    else if (f.kind === 'pdf' && f.pages && f.pages.length) vis = `<img src="${f.pages[0].d}" data-zoom="${id}" alt=""><div style="position:absolute;top:8px;left:8px" class="pill pMA">PDF ${f.pages.length}p</div>`;
    else vis = `<div class="fi">${esc((f.name.split('.').pop() || 'FILE').toUpperCase())}</div>`;
    return `<div class="th">${vis}<button class="x" data-arm="${key}|${id}" title="Remove">×</button><div class="nm" title="${esc(f.name)}">${esc(f.name)}</div>${f.kind === 'file' || (f.kind === 'pdf' && f.d) ? `<button class="more" data-dl="${id}">download</button>` : ''}<input type="text" placeholder="Caption" data-b="files.${id}.cap" value="${esc(f.cap || '')}"></div>`;
  }).join('');
  return `<div class="att" id="att-${key.replace(/[^A-Za-z0-9]/g, '_')}">${th}</div>
  <div class="up"><label class="btn sm">📷 Photo<input type="file" accept="image/*" capture="environment" data-up="${key}" multiple></label>
  <label class="btn sm">📎 Upload documents / pictures<input type="file" accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv" data-up="${key}" multiple></label></div>`;
}
function attTarget(key) {
  const [t, id] = key.split(':');
  if (t === 'item') return rec(id).att || (rec(id).att = []);
  if (t === 'sec') return S.secs[id].att;
  return S.genAtt;
}
function readAs(file, how) { return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => rej(r.error); r[how](file); }); }
function loadImg(src) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; }); }
function toJpeg(img, max = 1600, q = .82) {
  let w = img.naturalWidth || img.width, h = img.naturalHeight || img.height; const k = Math.min(1, max / Math.max(w, h)); w = Math.round(w * k); h = Math.round(h * k);
  const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, w, h); x.drawImage(img, 0, 0, w, h);
  return {d: c.toDataURL('image/jpeg', q), w, h};
}
async function pdfPages(buf, maxPages = 10) {
  if (!window.pdfjsLib) throw new Error('PDF renderer unavailable');
  const pdf = await pdfjsLib.getDocument({data: buf}).promise; const n = Math.min(pdf.numPages, maxPages); const pages = [];
  for (let i = 1; i <= n; i++) {
    const p = await pdf.getPage(i); const vp0 = p.getViewport({scale: 1}); const vp = p.getViewport({scale: Math.min(2, 1300 / vp0.width)});
    const c = document.createElement('canvas'); c.width = vp.width; c.height = vp.height; const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
    await p.render({canvasContext: x, viewport: vp}).promise; pages.push({d: c.toDataURL('image/jpeg', .8), w: c.width, h: c.height});
  }
  return {pages, total: pdf.numPages};
}
async function addFiles(key, fileList) {
  const arr = attTarget(key); let n = 0;
  toast('Processing ' + fileList.length + ' file(s)…');
  for (const file of fileList) {
    const id = uid(); const base = {id, name: file.name, type: file.type, size: file.size, cap: '', added: new Date().toISOString(), ref: key};
    try {
      if (file.type.startsWith('image/')) {
        const src = await readAs(file, 'readAsDataURL');
        try { const im = await loadImg(src); Object.assign(base, {kind: 'image'}, toJpeg(im)); }
        catch (e) { Object.assign(base, {kind: 'file', d: src}); }
      } else if (file.type === 'application/pdf' || /\.pdf$/i.test(file.name)) {
        const buf = await readAs(file, 'readAsArrayBuffer');
        base.kind = 'pdf';
        try { const r = await pdfPages(new Uint8Array(buf.slice(0))); base.pages = r.pages; base.totalPages = r.total; } catch (e) { base.pages = []; }
        if (file.size <= 8e6) base.d = await readAs(file, 'readAsDataURL');
        if (!base.pages.length) base.kind = base.d ? 'file' : 'file';
      } else {
        if (file.size > 15e6) { toast(file.name + ' is over 15 MB – skipped'); continue; }
        base.kind = 'file'; base.d = await readAs(file, 'readAsDataURL');
      }
      S.files[id] = base; arr.push(id); n++;
    } catch (e) { console.error(e); toast('Could not read ' + file.name); }
  }
  save(); rerenderAtt(key); refreshNav(); toast(n + ' file(s) attached');
}
function rerenderAtt(key) {
  const [t, id] = key.split(':');
  if (t === 'item') { const c = document.getElementById('it-' + id); if (c) { c.outerHTML = itemCard(itemDef(id).sec, itemDef(id).def); return; } }
  render();
}

/* ---------- auditor contribution summary (master) ---------- */
function contributions() {
  const team = S.lists.team || [];
  if (!team.length) return [];
  const by = {};
  team.forEach(t => {
    if (t.name && t.name.trim()) {
      const k = t.name.trim();
      by[k] = {name: k, role: t.role || 'Auditor', email: t.email || '', secs: new Set(), items: 0, f: 0, files: 0, imp: null};
    }
  });

  // Assign sections from S.secs
  SECTIONS.forEach(s => {
    const ss = S.secs[s.id];
    if (ss && ss.on) {
      [ss.auditor, ss.auditor2].filter(Boolean).forEach(aName => {
        const k = aName.trim();
        const found = Object.keys(by).find(nameKey => nameKey.toLowerCase() === k.toLowerCase());
        if (found) by[found].secs.add(s.id);
      });
    }
  });

  // Count items assessed and findings raised strictly for active team members
  Object.entries(S.items || {}).forEach(([id, r]) => {
    if (r && r.by) {
      const k = r.by.trim();
      const found = Object.keys(by).find(nameKey => nameKey.toLowerCase() === k.toLowerCase());
      if (found) {
        by[found].items++;
        const x = itemDef(id);
        if (x && isFinding(x.sec, r)) by[found].f++;
        by[found].files += (r.att || []).length;
      }
    }
  });

  return Object.values(by);
}
function vContrib() {
  const c = contributions();
  if (!c.length) return '<div class="card help">No auditor files imported yet. Use <b>Import auditor files</b> once the auditors send their files.</div>';
  return `<div class="tw"><table class="t"><thead><tr><th style="width:130px">Auditor</th><th style="width:180px">Sections</th><th style="width:95px">Items</th><th style="width:95px">Shared</th><th style="width:85px">Findings</th><th style="width:85px">Files</th><th style="width:140px">Last import</th></tr></thead><tbody>${c.map(x => `<tr><td><b>${esc(x.name)}</b></td><td><div class="t-clamp">${[...x.secs].map(s => `<span class="chip">${s}</span>`).join('')}</div></td><td>${x.items}</td><td>${x.shared ? `<a href="#" data-go="multi">${x.shared}</a>` : 0}</td><td>${x.f}</td><td>${x.files}</td><td>${x.imp ? esc(new Date(x.imp.at).toLocaleString()) + '<br><span class="help">' + esc(x.imp.file) + '</span>' : '<span class="help">—</span>'}</td></tr>`).join('')}</tbody></table></div>`;
}

/* ---------- VIEWS ---------- */
function vDash() {
  const st = stats(); const f = st.findings;
  const cnt = (k, v) => f.filter(x => x.r[k] === v).length;
  const openImm = f.filter(x => (x.r.tf === 'IMM') && !['Closed', 'Verified'].includes(x.r.st)).length;
  const openMA = f.filter(x => x.r.cls === 'MA' && !['Closed', 'Verified'].includes(x.r.st)).length;
  const pct = st.tot ? Math.round(st.done / st.tot * 100) : 0;
  const applic = st.done - st.res.NA;
  const compl = applic ? Math.round(st.res.C / applic * 100) : 0;
  let ban;
  if (!MASTER) ban = st.tot && st.done === st.tot ? ['grn', `<b>All ${st.tot} items in your sections are assessed.</b> Export your audit file and send it to the lead auditor.`] : ['gry', `<b>Your sections:</b> ${st.done} of ${st.tot} items assessed. Export your file whenever you want to send progress to the lead auditor.`];
  else if (openImm) ban = ['red', `<b>Not suitable for cadet placement:</b> ${openImm} immediate action(s) open. Immediate actions should be completed and independently verified before any cadet is placed.`];
  else if (openMA) ban = ['amb', `<b>Conditional:</b> ${openMA} major non-conformance(s) open with short/medium-term corrective actions.`];
  else if (st.done < st.tot) ban = ['gry', `<b>Audit in progress:</b> ${st.tot - st.done} checklist item(s) not yet assessed.`];
  else ban = ['grn', '<b>No open major non-conformances</b> recorded.'];
  const mx = Math.max(1, ...Object.keys(CLS).map(k => cnt('cls', k)), ...Object.keys(RISK).map(k => cnt('risk', k)));
  const hb = (label, n, col) => `<div class="hbar"><span>${label}</span><div class="bar"><i style="width:${n / mx * 100}%;background:${col}"></i></div><b>${n}</b></div>`;
  const colC = {MA: 'var(--nc)', MI: 'var(--p)', OB: 'var(--lo)', IO: 'var(--c)'}, colR = {H: 'var(--hi)', M: 'var(--me)', L: 'var(--lo)'};
  const secRows = SECTIONS.filter(s => S.secs[s.id].on && s.type === 'check').map(s => {
    const b = st.bySec[s.id]; const w = k => b.tot ? b.res[k] / b.tot * 100 : 0;
    return `<tr><td><a href="#" data-go="${s.id}"><div class="t-clamp">${esc(s.title)}</div></a></td><td><div class="t-clamp">${esc(secAuditors(s.id))}</div></td><td style="min-width:140px"><div class="bar"><i style="width:${w('C')}%;background:var(--c)"></i><i style="width:${w('P')}%;background:var(--p)"></i><i style="width:${w('NC')}%;background:var(--nc)"></i><i style="width:${w('NE')}%;background:var(--ne)"></i><i style="width:${w('NA')}%;background:var(--na)"></i></div><span class="help">${b.done}/${b.tot} assessed</span></td><td>${b.res.C}</td><td>${b.res.P}</td><td>${b.res.NC}</td><td>${b.res.NE}</td><td>${b.f}</td><td>${b.maxRisk ? `<span class="pill p${b.maxRisk}">${RISK[b.maxRisk]}</span>` : ''}</td></tr>`;
  }).join('');
  const nb = S.secs.NB.on ? `<h3>New / proposed base readiness</h3><div class="tw"><table class="t"><thead><tr><th style="width:260px">Element</th><th style="width:120px">Readiness</th><th style="width:130px">Critical path</th><th style="width:105px">Assessed date</th></tr></thead><tbody>${itemsOf('NB').map(d => { const r = S.items[d[0]] || {}; return `<tr><td><div class="t-clamp">${esc(d[1])}</div></td><td>${r.r ? esc(RDY[r.r]) : '<span class="help">not assessed</span>'}</td><td><div class="t-clamp">${esc(r.cp || '')}</div></td><td>${fmtDate(r.asDate)}</td></tr>`; }).join('')}</tbody></table></div>` : '';
  const top = f.filter(x => x.r.risk === 'H' && !['Closed', 'Verified'].includes(x.r.st)).slice(0, 12);
  return `<h2>${MASTER ? 'Master dashboard – integrated audit' : 'My progress'}</h2><p class="sub">${esc(S.meta.auditedOrg || 'Audited organisation not yet entered')} ${S.meta.from ? '· ' + fmtDate(S.meta.from) + (S.meta.to ? ' – ' + fmtDate(S.meta.to) : '') : ''}</p>
  <div class="banner ${ban[0]}">${ban[1]}${MASTER ? '<div class="help" style="margin-top:4px">Auto-computed indicator. The due diligence position you write in the Executive Summary is what appears in the report.</div>' : ''}</div>
  ${MASTER && pendingCount() ? `<div class="banner amb"><b>${pendingCount()} item(s)</b> were assessed differently by two or more auditors and need your review. <a href="#" data-go="multi">Review multi-auditor items</a></div>` : ''}
  <div class="kpis">
   <div class="kpi"><b>${pct}%</b><span>Checklist assessed (${st.done}/${st.tot})</span></div>
   <div class="kpi"><b>${compl}%</b><span>Compliant of applicable items assessed</span></div>
   <div class="kpi"><b>${f.length}</b><span>Findings raised</span></div>
   <div class="kpi"><b style="color:var(--nc)">${cnt('cls', 'MA')}</b><span>Major non-conformances</span></div>
   <div class="kpi"><b style="color:var(--hi)">${cnt('risk', 'H')}</b><span>High-risk findings</span></div>
   <div class="kpi"><b>${openImm}</b><span>Immediate actions open</span></div>
   <div class="kpi"><b>${st.files}</b><span>Evidence files attached</span></div>
  </div>
  ${MASTER ? `<h3>Auditor inputs integrated</h3>${vContrib()}${(() => { const ml = multiItems(); if (!ml.length) return ''; return `<h3>Items assessed by more than one auditor</h3><div class="tw"><table class="t"><thead><tr><th style="width:65px">Ref</th><th style="width:280px">Check item</th><th style="width:200px">Auditor inputs</th><th style="width:120px">Reported</th><th style="width:75px">Status</th></tr></thead><tbody>${ml.slice(0, 15).map(m => `<tr><td><a href="#" data-go="${m.x.sec.id}">${m.id}</a></td><td><div class="t-clamp">${esc(m.x.def[1])}</div></td><td><div class="t-clamp">${inputsOf(m.id).map(([w, r]) => `<div><b>${esc(w)}:</b> ${esc(cfVal('r', r.r) || '—')}${r.cls ? ' · ' + CLS[r.cls] : ''}</div>`).join('')}</div></td><td>${esc(cfVal('r', (S.items[m.id] || {}).r) || '')}${(S.items[m.id] || {}).by ? '<br><span class="help">' + esc(S.items[m.id].mEdit ? 'lead edit' : S.items[m.id].by) + '</span>' : ''}</td><td>${m.d.pending ? '<span class="pill pH">review</span>' : m.d.diff ? '<span class="pill pIO">reviewed</span>' : '<span class="pill pOB">agree</span>'}</td></tr>`).join('')}</tbody></table></div>${ml.length > 15 ? `<p class="help"><a href="#" data-go="multi">See all ${ml.length}</a></p>` : ''}`; })()}` : ''}
  <div class="grid g2" style="margin-top:12px"><div class="card"><h3 style="margin-top:0">Findings by classification</h3>${Object.keys(CLS).map(k => hb(CLS[k], cnt('cls', k), colC[k])).join('')}</div>
  <div class="card"><h3 style="margin-top:0">Findings by risk</h3>${Object.keys(RISK).map(k => hb(RISK[k], cnt('risk', k), colR[k])).join('')}</div>
  <h3>Corrective action timeframe</h3>${Object.keys(TF).map(k => hb(TF[k].split(' – ')[0], cnt('tf', k), 'var(--acc)')).join('')}</div></div>
  <h3>Section status</h3><p class="help">Bar: <span style="color:var(--c)">■</span> Compliant <span style="color:var(--p)">■</span> Partial <span style="color:var(--nc)">■</span> Non-compliant <span style="color:var(--ne)">■</span> Not evidenced <span style="color:var(--na)">■</span> N/A</p>
  <div class="tw"><table class="t"><thead><tr><th style="width:160px">Section</th><th style="width:130px">Auditor</th><th style="width:140px">Progress</th><th style="width:42px">C</th><th style="width:42px">P</th><th style="width:42px">NC</th><th style="width:42px">NE</th><th style="width:65px">Findings</th><th style="width:95px">Highest risk</th></tr></thead><tbody>${secRows}</tbody></table></div>
  ${top.length ? `<h3>Open high-risk findings</h3><div class="tw"><table class="t"><thead><tr><th style="width:65px">Ref</th><th style="width:340px">Finding</th><th style="width:95px">Class</th><th style="width:110px">Timeframe</th></tr></thead><tbody>${top.map(x => `<tr><td><a href="#" data-go="${x.sec}">${x.id}</a></td><td><div class="t-clamp">${esc(findText(x.r, x.def))}</div></td><td><span class="pill p${x.r.cls}">${CLS[x.r.cls]}</span></td><td>${x.r.tf ? TF[x.r.tf].split(' – ')[0] : ''}</td></tr>`).join('')}</tbody></table></div>` : ''}
  ${nb}`;
}

function vInfo() {
  const m = S.meta;
  if (!MASTER) {
    const ro = (l, v) => `<div><label class="f">${l}</label><div style="padding:6px 0;font-weight:500">${esc(v) || '<span class="help">—</span>'}</div></div>`;
    const myName = S.me.name || S.me.label;
    const teamRow = (S.lists.team || []).find(t => t.name && (t.name.trim().toLowerCase() === myName.trim().toLowerCase() || t.role === S.me.label));
    const myEmail = teamRow ? teamRow.email : '';

    return `<h2>Me & my sections</h2><p class="sub">Your auditor profile and section assignments configured by the Lead Auditor (Read-Only).</p>
    <div class="card">
      <div class="row">
        <div><label class="f">Auditor Name</label><div style="font-weight:700;font-size:15px;padding:6px 0">${esc(myName)}</div></div>
        <div><label class="f">Assigned Role</label><div style="font-weight:600;padding:6px 0">${esc(S.me.role || 'Auditor')}</div></div>
        <div><label class="f">Email ID</label><div style="color:var(--mute);padding:6px 0">${esc(myEmail || '—')}</div></div>
      </div>
      <div style="margin-top:14px">
        <label class="f">My Assigned Checklist Sections</label>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
          ${S.me.sections.length ? S.me.sections.map(sid => `<span class="pill pIO" style="font-size:12px;padding:4px 10px">✓ ${sid} — ${esc(SEC[sid].title)}</span>`).join('') : '<span class="help">No sections assigned yet by Lead Auditor.</span>'}
        </div>
        <p class="help" style="margin-top:12px">🔒 Section assignments and rights are locked and managed by the Lead Auditor. This page is informational and cannot be modified by field auditors.</p>
      </div>
    </div>
    <h3>Audit details (set by the lead auditor)</h3><div class="card"><div class="row">${ro('Audited organisation', m.auditedOrg)}${ro('Audit period', m.from ? fmtDate(m.from) + (m.to ? ' – ' + fmtDate(m.to) : '') : '')}${ro('Audit conducted by', m.auditingOrg)}</div>
    <div class="row">${ro('FTO approval / reference no.', m.approvalNo)}${ro('Report status', m.status)}${ro('Classification', m.classification)}</div></div>
    <h3>General evidence (not tied to a checklist item)</h3><div class="card">${attHTML('gen:', S.genAtt)}</div>`;
  }

  return `<h2>Audit information & team</h2><p class="sub">Populates Section 1 of the report. Complete this before creating the auditor files – it is copied into each one.</p>
  <div class="card"><div class="row">${fld('meta.auditingOrg', 'Audit conducted by (organisation)', m.auditingOrg)}${fld('meta.auditedOrg', 'Audited organisation (FTO)', m.auditedOrg)}</div>
  <div class="row">${fld('meta.approvalNo', 'FTO approval / reference no.', m.approvalNo)}${fld('meta.from', 'Audit from', m.from, 'date')}${fld('meta.to', 'Audit to', m.to, 'date')}</div>
  <div class="row">${fld('meta.title', 'Report title', m.title)}${fld('meta.type', 'Audit type', m.type)}</div>
  <div class="row">${fld('meta.framework', 'Regulatory framework', m.framework)}</div>
  <div class="row"><div><label class="f">Report status</label><select data-b="meta.status">${['Draft', 'Interim', 'Final'].map(x => `<option ${x === m.status ? 'selected' : ''}>${x}</option>`).join('')}</select></div>${fld('meta.classification', 'Classification', m.classification)}</div>
  ${fld('meta.distribution', 'Distribution', m.distribution, 'area')}</div>
  <h3>Locations</h3>${listTable('locations')}
  <h3>Audit Team, Email IDs & Section Rights</h3>${teamRightsTable()}
  <h3>Personnel engaged during the audit (auditee)</h3>${listTable('personnel')}
  <h3>Purpose of the audit</h3><div class="card">${fld('text.purpose', 'Purpose (Section 1.1)', S.text.purpose, 'area')}</div>
  <h3>Sections in scope</h3><div class="card"><p class="help" style="margin-top:0">Switch off any section not in scope – it will be excluded from the dashboard, auditor files and reports.</p>${SECTIONS.map(s => `<label style="display:block;margin:4px 0"><input type="checkbox" data-secon="${s.id}" ${S.secs[s.id].on ? 'checked' : ''}> ${esc(s.title)}</label>`).join('')}</div>
  <h3>General evidence (not tied to a checklist item)</h3><div class="card">${attHTML('gen:', S.genAtt)}</div>`;
}
function vExec() {
  const t = S.text;
  return `<h2>Executive summary & conclusion</h2><p class="sub">Written by the lead auditor once section inputs are merged. Use “Draft from findings” to start from the recorded data, then edit.</p>
  <div class="card">${fld('text.exec', 'Executive summary – overview (Section 2)', t.exec, 'area')}<button class="btn sm" data-draft="exec">Draft from findings</button>
  ${fld('text.themes', 'Principal risk themes (Section 2.1)', t.themes, 'area', 'A. … B. … C. …')}<button class="btn sm" data-draft="themes">Draft from findings</button>
  ${fld('text.position', 'Due diligence position (Section 2.3)', t.position, 'area')}</div>
  <div class="card">${fld('text.methodology', 'Methodology (Section 3.2)', t.methodology, 'area')}${fld('text.limitations', 'Limitations (Section 3.3) – one per line', t.limitations, 'area')}</div>
  <div class="card">${fld('text.conclusion', "Auditor's conclusion", t.conclusion, 'area')}</div>
  <p class="help">Sign-off block uses the Audit team list (Audit information page).</p>`;
}
function draft(which) {
  const st = stats(); const f = st.findings; const c = k => f.filter(x => x.r.cls === k).length;
  if (which === 'exec') {
    S.text.exec = `The audit assessed ${st.done} of ${st.tot} checklist items across ${Object.keys(st.bySec).length} functional areas and raised ${f.length} findings: ${c('MA')} major non-conformances, ${c('MI')} minor non-conformances, ${c('OB')} observations and ${c('IO')} improvement opportunities. ${f.filter(x => x.r.risk === 'H').length} findings are rated high risk and ${f.filter(x => x.r.tf === 'IMM').length} require immediate corrective action before cadet placement.`;
  } else {
    const L = 'ABCDEFGHIJKLMNOP'; let i = 0;
    S.text.themes = SECTIONS.filter(s => st.bySec[s.id] && f.some(x => x.sec === s.id && x.r.risk === 'H')).map(s => {
      const hs = f.filter(x => x.sec === s.id && x.r.risk === 'H');
      return `${L[i++]}. ${s.title}. ${hs.map(x => findText(x.r, x.def)).join(' ')}`;
    }).join('\n\n');
  }
  save(); render();
}

function inputsPanel(id) {
  if (!MASTER) return ''; const ins = inputsOf(id); if (!ins.length) return '';
  if (ins.length === 1 && !(S.items[id] || {}).mEdit) return `<p class="help" style="margin:8px 0 0">Recorded by <b>${esc(ins[0][0])}</b></p>`;
  const d = divergence(id);
  return `<div class="fp" style="border-color:${d.pending ? '#efd08a' : '#c9d2dc'};background:${d.pending ? '#fffbeb' : '#fbfbfd'}"><h4 style="color:var(--acc)">Auditor inputs (${ins.length}) ${d.pending ? '<span class="pill pH">auditors disagree – review</span>' : d.diff ? '<span class="pill pIO">reviewed</span>' : '<span class="pill pOB">auditors agree</span>'}</h4>
  <p class="help" style="margin:0 0 6px">The fields above are the <b>reported</b> version. Each auditor's comments appear under their name in the report.</p>${inputsTable(id, true)}
  ${d.pending ? `<button class="btn sm" style="margin-top:6px" data-rev="${id}">Mark reviewed – keep reported version</button>` : ''}</div>`;
}
function itemCard(sec, d) {
  const id = d[0]; const r = S.items[id] || {};
  const custom = (S.secs[sec.id].custom || []).some(c => c[0] === id);
  const methods = (d[3] || '').split(',').filter(Boolean).map(m => `<span class="chip">${METHODS[m] || m}</span>`).join('');
  if (sec.type === 'ready') {
    return `<div class="item ${r.r ? (r.r === 'R' ? 'rC' : r.r === 'NA' ? 'rNA' : r.r === 'PR' || r.r === 'UC' ? 'rP' : 'rNC') : ''}" id="it-${id}">
    <div class="ih"><span class="id">${id}</span><div class="q">${esc(d[1])}</div>${custom ? `<button class="btn sm danger" data-cdel="${sec.id}|${id}">Delete</button>` : ''}</div><div style="margin-top:4px">${methods}</div>
    <div class="seg">${Object.entries(RDY).map(([k, v]) => `<button data-res="${id}" data-v="${k}" class="${r.r === k ? 'on ' + (k === 'R' ? 'C' : k === 'NA' ? 'NA' : (k === 'PR' || k === 'UC') ? 'P' : 'NC') : ''}">${v}</button>`).join('')}</div>
    <div class="row">${fld(`items.${id}.status`, 'Status as assessed', r.status || '', 'area')}${fld(`items.${id}.cp`, 'Critical path / dependency', r.cp || '', 'area')}</div>
    <div class="row">${fld(`items.${id}.opDate`, 'Operator stated date', r.opDate || '', 'date')}${fld(`items.${id}.asDate`, 'Audit team assessed date', r.asDate || '', 'date')}</div>
    ${fld(`items.${id}.comment`, 'Auditor comments', r.comment || '', 'area')}
    ${inputsPanel(id)}${attHTML('item:' + id, r.att)}</div>`;
  }
  const showF = r.cls || ['P', 'NC', 'NE'].includes(r.r);
  return `<div class="item ${r.r ? 'r' + r.r : ''}" id="it-${id}">
  <div class="ih"><span class="id">${id}</span><div class="q">${esc(d[1])}</div>${custom ? `<button class="btn sm danger" data-cdel="${sec.id}|${id}">Delete</button>` : ''}</div>
  ${d[2] ? `<p class="ev"><b>Evidence:</b> ${esc(d[2])}</p>` : ''}<div style="margin-top:4px">${methods}</div>
  <div class="seg">${Object.entries(RES).map(([k, v]) => `<button data-res="${id}" data-v="${k}" class="${r.r === k ? 'on ' + k : ''}">${v}</button>`).join('')}</div>
  ${fld(`items.${id}.comment`, 'Auditor comments / evidence sighted', r.comment || '', 'area', 'What was seen, sampled or stated…')}
  ${showF ? `<div class="fp"><h4>Finding${r.cls ? ' – ' + id : ''}</h4>
    <div class="row"><div><label class="f">Classification</label>${sel(`items.${id}.cls`, CLS, r.cls || '', 'No finding')}</div><div><label class="f">Risk</label>${sel(`items.${id}.risk`, RISK, r.risk || '')}</div><div><label class="f">Corrective action timeframe</label>${sel(`items.${id}.tf`, TF, r.tf || '')}</div></div>
    ${fld(`items.${id}.find`, 'Finding statement (as it will appear in the report)', r.find || '', 'area', 'State the condition evidenced, e.g. “No Safety Manager is appointed; the post is vacant.”')}
    ${fld(`items.${id}.act`, 'Required corrective action', r.act || '', 'area')}
    <div class="row">${fld(`items.${id}.owner`, 'Action owner (auditee)', r.owner || '')}${fld(`items.${id}.due`, 'Target date', r.due || '', 'date')}<div><label class="f">Status</label><select data-b="items.${id}.st">${['Open', 'In progress', 'Closed', 'Verified'].map(x => `<option ${x === (r.st || 'Open') ? 'selected' : ''}>${x}</option>`).join('')}</select></div></div>
  </div>` : `<button class="more" data-raise="${id}">+ Raise observation / improvement opportunity</button>`}
  ${inputsPanel(id)}${attHTML('item:' + id, r.att)}</div>`;
}

function vSection(sid) {
  const sec = SEC[sid]; const ss = S.secs[sid];
  const team = (S.lists.team || []).map(t => t.name).filter(Boolean);
  let extra = '';
  if (sid === 'ORG') extra = `<h3>Instructional cadre</h3>${listTable('cadre')}`;
  if (sid === 'FLT') extra = `<h3>Fleet reconciliation (record each source)</h3>${listTable('fleet', 'Figures from different sources should reconcile. Unreconciled numbers support finding FLT-01.')}`;
  return `<div style="display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap"><div style="flex:1;min-width:240px"><h2>${esc(sec.title)}</h2><p class="sub">${esc(sec.intro)}</p></div>
   </div>
  ${!ss.on ? (MASTER ? '<div class="banner gry">This section is switched off (out of scope). Turn it on under Audit information.</div>' : '<div class="banner gry">This section is not assigned to you. Tick it under “Me & my sections” if you are auditing it.</div>') : ''}
  <div class="card"><div class="row"><div><label class="f">Section auditor</label>${MASTER ? `<select data-b="secs.${sid}.auditor"><option value="">— Unassigned —</option>${team.map(n => `<option value="${esc(n)}" ${n === ss.auditor ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select>` : `<div style="padding:7px 0"><b>${esc(meName())}</b></div>`}</div></div>
  ${fld(`secs.${sid}.comment`, 'Section narrative / general comments (appears at the start of this section in the report)', ss.comment, 'area')}
  <label class="f">Section-level evidence</label>${attHTML('sec:' + sid, ss.att)}</div>
  ${itemsOf(sid).map(d => itemCard(sec, d)).join('')}
  <div class="card"><b>Add a check item to this section</b><div class="row">${`<div><label class="f">Check item</label><input type="text" id="newQ"></div><div><label class="f">Evidence to request / sight</label><input type="text" id="newE"></div>`}</div>
  <button class="btn sm" data-cadd="${sid}" style="margin-top:8px">+ Add item</button></div>
  ${extra}`;
}

function findingsSorted(filter) {
  const order = {}; SECTIONS.forEach((s, i) => order[s.id] = i);
  return stats().findings.filter(filter || (() => true)).sort((a, b) => order[a.sec] - order[b.sec]);
}
let regF = {cls: '', risk: '', st: ''};
function vReg() {
  const list = findingsSorted(x => (!regF.cls || x.r.cls === regF.cls) && (!regF.risk || x.r.risk === regF.risk) && (!regF.st || (x.r.st || 'Open') === regF.st));
  const fs = (k, o) => `<select data-regf="${k}"><option value="">All</option>${Object.entries(o).map(([a, b]) => `<option value="${a}" ${regF[k] === a ? 'selected' : ''}>${b}</option>`).join('')}</select>`;
  return `<h2>Consolidated findings register</h2><p class="sub">Every checklist item with a classification is a finding. Edit the finding in its section; status can be updated here.</p>
  <div class="row" style="max-width:700px;margin-bottom:10px"><div><label class="f">Classification</label>${fs('cls', CLS)}</div><div><label class="f">Risk</label>${fs('risk', RISK)}</div><div><label class="f">Status</label>${fs('st', {Open: 'Open', 'In progress': 'In progress', Closed: 'Closed', Verified: 'Verified'})}</div></div>
  <div class="tw"><table class="t"><thead><tr><th style="width:65px">Ref</th><th style="width:340px">Finding</th><th style="width:110px">Classification</th><th style="width:90px">Risk</th><th style="width:110px">Timeframe</th><th style="width:110px">Status</th>${MASTER ? '<th style="width:120px">Assessed by</th>' : ''}</tr></thead><tbody>
  ${list.map(x => `<tr><td><a href="#" data-go="${x.sec}">${x.id}</a></td><td><div class="t-clamp">${esc(findText(x.r, x.def))}</div></td><td><span class="pill p${x.r.cls}">${CLS[x.r.cls]}</span></td><td>${x.r.risk ? `<span class="pill p${x.r.risk}">${RISK[x.r.risk]}</span>` : ''}</td><td>${x.r.tf ? TF[x.r.tf].split(' – ')[0] : ''}</td><td><select data-b="items.${x.id}.st">${['Open', 'In progress', 'Closed', 'Verified'].map(s => `<option ${s === (x.r.st || 'Open') ? 'selected' : ''}>${s}</option>`).join('')}</select></td>${MASTER ? `<td><div class="t-clamp">${esc(inputsOf(x.id).map(i => i[0]).join(', ') || x.r.by || '')}</div></td>` : ''}</tr>`).join('') || '<tr><td colspan="7" class="help">No findings match.</td></tr>'}</tbody></table></div>`;
}
function capGroups() {
  const f = findingsSorted(); const g = {IMM: [], D30: [], D90: [], '': []};
  f.forEach(x => g[x.r.tf || ''].push(x)); return g;
}
function vCap() {
  const g = capGroups(); let n = 0;
  const blk = (k, title) => g[k].length ? `<h3>${title}</h3><div class="tw"><table class="t"><thead><tr><th style="width:45px">No.</th><th style="width:320px">Action</th><th style="width:75px">Finding</th><th style="width:140px">Owner</th><th style="width:125px">Target</th><th style="width:110px">Status</th></tr></thead><tbody>${g[k].map(x => `<tr><td>${++n}</td><td><textarea data-b="items.${x.id}.act">${esc(x.r.act || '')}</textarea></td><td><a href="#" data-go="${x.sec}">${x.id}</a></td><td><input type="text" data-b="items.${x.id}.owner" value="${esc(x.r.owner || '')}"></td><td><input type="date" data-b="items.${x.id}.due" value="${esc(x.r.due || '')}"></td><td><select data-b="items.${x.id}.st">${['Open', 'In progress', 'Closed', 'Verified'].map(s => `<option ${s === (x.r.st || 'Open') ? 'selected' : ''}>${s}</option>`).join('')}</select></td></tr>`).join('')}</tbody></table></div>` : '';
  return `<h2>Corrective action programme</h2><p class="sub">Actions grouped by timeframe. Edits here update the finding.</p>
  ${blk('IMM', 'Immediate actions – to be completed before cadet placement')}${blk('D30', 'Short-term actions – within 30 days')}${blk('D90', 'Medium-term actions – within 90 days')}${blk('', 'Timeframe not set')}
  ${n ? '' : '<p class="help">No findings yet.</p>'}`;
}
function applyTableClamps() {
  document.querySelectorAll('table.t td').forEach(td => {
    if (!td.querySelector('input, select, textarea, button') && !td.querySelector('.t-clamp') && td.innerText.trim().length > 60) {
      const html = td.innerHTML;
      td.innerHTML = `<div class="t-clamp">${html}</div>`;
    }
  });
  document.querySelectorAll('.t-clamp').forEach(el => {
    if (el.scrollHeight > el.clientHeight + 2) {
      el.classList.add('can-expand');
    }
  });
}

function render() {
  refreshNav();
  const m = $('#main');
  if (view === 'dash') m.innerHTML = vDash();
  else if (view === 'info') m.innerHTML = vInfo();
  else if (view === 'exec' && MASTER) m.innerHTML = vExec();
  else if (view === 'reg') m.innerHTML = vReg();
  else if (view === 'cap') m.innerHTML = vCap();
  else if (view === 'data' && MASTER) m.innerHTML = vData();
  else if (view === 'multi' && MASTER) m.innerHTML = vMulti();
  else if (view === 'send' && !MASTER) m.innerHTML = vSend();
  else if (SEC[view]) m.innerHTML = vSection(view);
  $('#hdrOrg').textContent = S.meta.auditedOrg ? S.meta.auditedOrg + (S.meta.from ? ' · ' + fmtDate(S.meta.from) : '') : (MASTER ? 'Lead auditor – integrates the auditors\' files into one report' : 'Auditor file – complete your sections and export for the lead auditor');
  setTimeout(applyTableClamps, 40);
}

/* ---------- binding ---------- */
function setPath(path, val) {
  const p = path.split('.'); let o = S;
  for (let i = 0; i < p.length - 1; i++) { if (o[p[i]] == null) o[p[i]] = /^\d+$/.test(p[i + 1]) ? [] : {}; o = o[p[i]]; }
  o[p[p.length - 1]] = val;
}
function onField(e) {
  const el = e.target; const b = el.dataset.b; if (!b) return;
  setPath(b, el.value);
  if (MASTER && /^items\./.test(b)) { const r = S.items[b.split('.')[1]]; if (r && r.by) r.mEdit = true; }
  save();
  if (/^items\.[^.]+\.cls$/.test(b)) { const id = b.split('.')[1]; const x = itemDef(id); const r = rec(id);
    if (el.value) { r.risk = r.risk || x.def[5] || ''; r.tf = r.tf || x.def[6] || ''; r.act = r.act || x.def[7] || ''; r.st = r.st || 'Open'; }
    document.getElementById('it-' + id).outerHTML = itemCard(x.sec, x.def); }
  if (e.type === 'change' && view === 'data' && /^secs\.[^.]+\.auditor$/.test(b)) render();
  if (e.type === 'change' && (/^secs\.[^.]+\.auditor$/.test(b) || /\.(cls|risk|st)$/.test(b) || b.startsWith('meta.auditedOrg'))) refreshNav();
  if (b === 'meta.auditedOrg' || b === 'meta.from') $('#hdrOrg').textContent = S.meta.auditedOrg || 'FTO audit';
}
function setResult(id, v) {
  const x = itemDef(id); const r = rec(id);
  r.r = r.r === v ? '' : v;
  if (MASTER && r.by) r.mEdit = true;
  if (x.sec.type === 'check') {
    if (['P', 'NC', 'NE'].includes(r.r) && !r.cls) { r.cls = x.def[4] || 'OB'; r.risk = r.risk || x.def[5] || 'M'; r.tf = r.tf || x.def[6] || 'D90'; r.act = r.act || x.def[7] || ''; r.st = r.st || 'Open'; if (r.r === 'P' && r.cls === 'MA') r.cls = 'MI'; }
    if (['C', 'NA', ''].includes(r.r) && r.cls && !r.find && (r.act || '') === (x.def[7] || '') && !r.owner && !r.due) { delete r.cls; delete r.risk; delete r.tf; delete r.act; delete r.st; }
  }
  save(); document.getElementById('it-' + id).outerHTML = itemCard(x.sec, x.def); refreshNav();
}

/* ---------- MASTER: create auditor files & import ---------- */
function teamOpts() { return (S.lists.team || []).map(t => t.name).filter(Boolean); }
function assignedTo(name) { return SECTIONS.filter(s => S.secs[s.id].on && (S.secs[s.id].auditor === name || S.secs[s.id].auditor2 === name)).map(s => s.id); }
function vData() {
  const team = teamOpts();
  const pick = (s, f, blank) => `<select data-b="secs.${s.id}.${f}"><option value="">${blank}</option>${team.concat(S.secs[s.id][f] && !team.includes(S.secs[s.id][f]) ? [S.secs[s.id][f]] : []).map(n => `<option ${n === S.secs[s.id][f] ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select>`;
  const rows = SECTIONS.filter(s => S.secs[s.id].on).map(s => `<tr><td><div class="t-clamp">${esc(s.title)}</div></td><td>${pick(s, 'auditor', '— unassigned —')}</td><td>${pick(s, 'auditor2', '— none —')}</td></tr>`).join('');
  const unassigned = SECTIONS.filter(s => S.secs[s.id].on && !S.secs[s.id].auditor).length;
  const auds = team.map(n => ({n, secs: assignedTo(n)}));
  return `<h2>Auditor files: create & import</h2><p class="sub">Three steps: assign sections → send each auditor their own file → import their returned files here to build one integrated report.</p>
  <div class="card"><h3 style="margin-top:0">Step 1 – Assign sections to auditors</h3>
  ${team.length ? '' : '<div class="banner amb">Add auditor names in <a href="#" data-go="info">Audit information & team</a> first.</div>'}
  <div class="tb" style="margin-bottom:8px"><button class="btn sm" data-act="split3">Apply default 3-auditor split</button></div>
  <div class="tw"><table class="t"><thead><tr><th style="width:240px">Section</th><th style="width:220px">Auditor</th><th style="width:220px">Second auditor (optional – same checklist)</th></tr></thead><tbody>${rows}</tbody></table></div>
  ${unassigned ? `<p class="help">${unassigned} section(s) unassigned.</p>` : ''}</div>
  <div class="card"><h3 style="margin-top:0">Step 2 – Create an auditor file for each auditor</h3>
  <p class="help" style="margin-top:0">Each file is a copy of this tool locked to that auditor's sections, with the audit details already filled in. Email or share it; the auditor opens it in any browser (works offline).</p>
  <div class="tw"><table class="t"><thead><tr><th style="width:160px">Auditor</th><th style="width:340px">Sections</th><th style="width:180px"></th></tr></thead><tbody>${auds.map(a => `<tr><td><b>${esc(a.n)}</b></td><td><div class="t-clamp">${a.secs.map(s => `<span class="chip">${s}</span>`).join('') || '<span class="help">none assigned</span>'}</div></td><td>${a.secs.length ? `<button class="btn sm pri" data-mk="${esc(a.n)}">⬇ Create auditor file</button>` : ''}</td></tr>`).join('') || '<tr><td colspan="3" class="help">No team members yet.</td></tr>'}</tbody></table></div>
  ${auds.filter(a => a.secs.length).length > 1 ? '<button class="btn" data-act="mkall" style="margin-top:8px">⬇ Create all auditor files</button>' : ''}</div>
  <div class="card"><h3 style="margin-top:0">Step 3 – Import the auditors' returned files</h3>
  <p class="help" style="margin-top:0">Each auditor sends you either their export (<code>.json</code>, from <b>Send to lead auditor</b>) or their latest <b>Save progress</b> copy (<code>…_saved_….html</code>). Both work – select all of them at once, part-finished files included. Re-importing a newer file from the same auditor updates their data. When two auditors fill in the same checklist item, <b>both inputs are kept under each auditor's name</b>. The first one imported becomes the reported version; where the auditors disagree on result, classification or risk the item is flagged under <a href="#" data-go="multi">Multi-auditor items</a> for you to choose. Evidence from every auditor is always kept.</p>
  <button class="btn pri" data-act="merge">⤵ Import auditor files</button>
  <h3>Import log</h3>${S.imports.length ? `<div class="tw"><table class="t"><thead><tr><th style="width:120px">Auditor</th><th style="width:140px">File</th><th style="width:140px">Sections</th><th style="width:80px">Items</th><th style="width:80px">Evidence</th><th style="width:100px">Differ</th><th style="width:120px">Imported</th></tr></thead><tbody>${S.imports.map(i => `<tr><td>${esc(i.auditor)}</td><td><div class="t-clamp">${esc(i.file)}</div></td><td><div class="t-clamp">${(i.sections || []).join(', ')}</div></td><td>${i.items}</td><td>${i.files}</td><td>${i.diverge ?? i.conflicts ?? 0}</td><td>${esc(new Date(i.at).toLocaleString())}</td></tr>`).join('')}</tbody></table></div>` : '<p class="help">Nothing imported yet.</p>'}</div>
  <div class="card"><h3 style="margin-top:0">Saving the master</h3><p class="help" style="margin-top:0"><b>💾 Save progress</b> (Cmd+S) downloads a new copy of this master dashboard with everything inside – imported auditor inputs, your edits and all evidence. Open the newest copy to continue. The data-only options below are for backup.</p><div class="tb"><button class="btn pri" data-act="fsave">💾 Save progress</button><button class="btn" data-act="save">Save data file (.json)</button><button class="btn" data-act="open">📂 Open data file (replace)</button><button class="btn danger" data-act="new">Start a new blank audit</button></div>
  <p class="help">Safari may not keep browser autosave for files opened from your disk, so always use Save progress before closing.</p></div>
  <div class="card help"><b>Evidence handling:</b> photos are resized to max 1600 px and embedded. PDFs are rendered page-by-page (first 10 pages) as images so they appear in the Word / PDF report; the original PDF is also kept (up to 8 MB). Word, Excel and other files are kept inside the data files and listed in the report's evidence index – their content is not reproduced in the report.</div>`;
}
/* ---------- MULTI-AUDITOR INPUTS (master) ----------
   S.inputs[itemId][auditorName] = that auditor's own record, exactly as exported.
   S.items[itemId] = the "reported" record used for the report (first input, a chosen input, or master edit). */
const CF_FIELDS = [['r', 'Result'], ['cls', 'Classification'], ['risk', 'Risk'], ['tf', 'Timeframe'], ['find', 'Finding statement'], ['act', 'Corrective action'], ['comment', 'Comments'], ['status', 'Status as assessed'], ['cp', 'Critical path'], ['opDate', 'Operator date'], ['asDate', 'Assessed date'], ['owner', 'Owner'], ['due', 'Target'], ['st', 'Status']];
const cfVal = (k, v) => !v ? '' : k === 'r' ? (RES[v] || RDY[v] || v) : k === 'cls' ? CLS[v] : k === 'risk' ? RISK[v] : k === 'tf' ? TF[v] : (/Date|due/.test(k) ? fmtDate(v) : v);
const inputsOf = id => Object.entries((S.inputs || {})[id] || {});
const sigOf = r => [r.r || '', r.cls || '', r.risk || ''].join('|');
function divergence(id) { // do the auditors (and any master edit) disagree on result / classification / risk?
  const ins = inputsOf(id); const l = S.items[id] || {};
  const sigs = new Set(ins.map(([, r]) => sigOf(r))); if (l.mEdit && hasContent(l)) sigs.add(sigOf(l));
  const all = ins.map(([n, r]) => n + ':' + sigOf(r)).sort().join(';') + (l.mEdit ? ';M:' + sigOf(l) : '');
  return {multi: ins.length > 1, diff: sigs.size > 1, pending: sigs.size > 1 && l.rev !== all, key: all};
}
function multiItems() {
  const out = []; Object.keys(S.inputs || {}).forEach(id => { const x = itemDef(id); if (!x || !S.secs[x.sec.id].on) return; const d = divergence(id); if (d.multi || d.diff) out.push({id, x, d}); });
  const order = {}; SECTIONS.forEach((s, i) => order[s.id] = i);
  return out.sort((a, b) => (b.d.pending - a.d.pending) || (order[a.x.sec.id] - order[b.x.sec.id]));
}
const pendingCount = () => MASTER ? multiItems().filter(m => m.d.pending).length : 0;
function inputsTable(id, withButtons) {
  const ins = inputsOf(id); const l = S.items[id] || {}; const x = itemDef(id); const ready = x && x.sec.type === 'ready';
  const cols = ready ? [['r', 'Readiness'], ['status', 'Status as assessed'], ['cp', 'Critical path'], ['asDate', 'Assessed date'], ['comment', 'Comments']] : [['r', 'Result'], ['cls', 'Classification'], ['risk', 'Risk'], ['find', 'Finding'], ['comment', 'Comments']];
  const row = (who, r, cur, btn) => `<tr${cur ? ' style="background:#eef6ee"' : ''}><td><b>${esc(who)}</b>${cur ? '<br><span class="pill pIO">reported</span>' : ''}</td>${cols.map(([k]) => `<td>${esc(cfVal(k, r[k]))}</td>`).join('')}<td>${(r.att || []).length}</td>${withButtons ? `<td>${btn}</td>` : ''}</tr>`;
  const isCur = (who, r) => !l.mEdit && l.by === who && sameData(l, r);
  return `<div class="tw"><table class="t"><tr><th>Auditor</th>${cols.map(c => `<th>${c[1]}</th>`).join('')}<th>Evidence</th>${withButtons ? '<th></th>' : ''}</tr>
  ${ins.map(([who, r]) => row(who, r, isCur(who, r), isCur(who, r) ? '' : `<button class="btn sm" data-use="${id}|${esc(who)}">Report this version</button>`)).join('')}
  ${l.mEdit ? row('Lead auditor (edited in master)', l, true, '') : ''}</table></div>`;
}
function vMulti() {
  const list = multiItems(); const pend = list.filter(m => m.d.pending).length;
  return `<h2>Multi-auditor items</h2><p class="sub">Checklist items assessed by more than one auditor. Every auditor's input is kept under their name and appears in the report comments. The <b>reported</b> version sets the result and finding used in the dashboard, register and corrective action plan.</p>
  ${list.length ? `<div class="kpis"><div class="kpi"><b>${list.length}</b><span>Items with 2+ auditor inputs</span></div><div class="kpi"><b>${list.filter(m => m.d.diff).length}</b><span>Auditors disagree (result / class / risk)</span></div><div class="kpi"><b style="color:${pend ? 'var(--nc)' : 'var(--c)'}">${pend}</b><span>Awaiting lead auditor review</span></div></div>` : '<div class="card help">None yet. When two auditors fill in the same checklist item and their files are imported, the item appears here.</div>'}
  ${list.map(m => `<div class="card"><div class="ih"><span class="id">${m.id}</span><div class="q"><a href="#" data-go="${m.x.sec.id}">${esc(m.x.def[1])}</a></div>${m.d.pending ? '<span class="pill pH">review</span>' : m.d.diff ? '<span class="pill pIO">reviewed</span>' : '<span class="pill pOB">agree</span>'}</div>
   <div style="margin-top:8px">${inputsTable(m.id, true)}</div>
   ${m.d.pending ? `<div class="tb" style="margin-top:8px"><button class="btn sm pri" data-rev="${m.id}">Mark reviewed – keep reported version</button></div>` : ''}</div>`).join('')}`;
}
function useInput(id, who) {
  const inp = (S.inputs[id] || {})[who]; if (!inp) return; const l = rec(id); const att = l.att || [];
  CF_FIELDS.forEach(([k]) => { if (inp[k] != null && inp[k] !== '') l[k] = inp[k]; else delete l[k]; });
  Object.assign(l, {att, by: who, mEdit: false}); l.rev = divergence(id).key;
  save(); render(); toast(`${id}: ${who}'s version is now reported`);
}
function markReviewed(id) { rec(id).rev = divergence(id).key; save(); render(); }
// report text for the comments column: every auditor's comment under their name
function repComment(id, r) {
  const ins = inputsOf(id).filter(([, x]) => hasContent(x));
  if (ins.length < 2) return r.comment || '';
  const lines = ins.map(([who, x]) => { const bits = []; if (x.comment) bits.push(x.comment); if (divergence(id).diff) bits.unshift('[' + (cfVal('r', x.r) || 'not assessed') + (x.cls ? ', ' + CLS[x.cls] : '') + ']'); return bits.length ? `${who}: ${bits.join(' ')}` : ''; }).filter(Boolean);
  if (r.mEdit && r.comment && !ins.some(([, x]) => x.comment === r.comment)) lines.push('Lead auditor: ' + r.comment);
  return lines.join('\n');
}
function makeAuditorFile(name) {
  const secs = assignedTo(name); if (!secs.length) { toast(name + ' has no sections assigned'); return; }
  const t = (S.lists.team || []).find(x => x.name === name) || {};
  const custom = {}; secs.forEach(s => { if (S.secs[s].custom.length) custom[s] = S.secs[s].custom; });
  const cfg = {mode: 'auditor', instanceId: 'i' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), me: {name, role: t.role || 'Auditor', label: name, sections: secs},
    seed: {meta: S.meta, lists: {locations: S.lists.locations, team: S.lists.team, personnel: S.lists.personnel}, custom}};
  const js = 'window.CFG=' + JSON.stringify(cfg).replace(/</g, '\\u003c') + ';';
  const html = withSaved(PRISTINE.replace(/<script id="cfg">[\s\S]*?<\/script>/, () => '<script id="cfg">' + js + '<\/script>'), null);
  download(new Blob([html], {type: 'text/html'}), `${slug(S.meta.auditedOrg)}_AUDITOR_${slug(name)}.html`);
}
function makeAll() { const names = teamOpts().filter(n => assignedTo(n).length); names.forEach((n, i) => setTimeout(() => makeAuditorFile(n), i * 900)); toast(`Creating ${names.length} auditor files – allow multiple downloads if the browser asks`); }
function applySplit() {
  const team = teamOpts(); if (team.length < 3 && !confirm('Fewer than 3 team names are entered. Missing auditors will be named "Auditor 2/3". Continue?')) return;
  Object.entries(DEFAULT_SPLIT).forEach(([k, secs], i) => { let n = team[i]; if (!n) { n = k; const row = S.lists.team[i]; if (row) row.name = n; else S.lists.team.push({name: n, role: 'Auditor'}); } secs.forEach(s => S.secs[s].auditor = n); });
  save(); render(); toast('Default split applied – adjust as needed');
}

/* ---------- AUDITOR: send page ---------- */
function vSend() {
  const st = stats();
  return `<h2>Send my work to the lead auditor</h2><p class="sub">Your file contains your results, comments, findings, photos and documents for your sections.</p>
  <div class="card"><ol style="margin:0;padding-left:18px"><li>Check your name is filled in under <a href="#" data-go="info">Me & my sections</a>${S.me.name ? ` (currently <b>${esc(S.me.name)}</b>)` : ' – <b style="color:var(--nc)">not yet entered</b>'}.</li>
  <li>Click <b>Export my audit file</b>. A <code>.json</code> file downloads.</li>
  <li>Send that file to the lead auditor (email, shared drive, WhatsApp document). They import it into the master dashboard.</li>
  <li>You can keep working and send an updated file later – the master replaces your earlier data with the newer file.</li></ol>
  <p><b>${st.done}/${st.tot}</b> items assessed · <b>${st.findings.length}</b> findings · <b>${st.files}</b> evidence files</p>
  <button class="btn pri" data-act="aexp">⬆ Export my audit file for the lead auditor</button></div>
  <div class="card help"><b>Saving part-way through:</b> click <b>💾 Save progress</b> (or press Cmd+S) at any time. It downloads a new copy of this HTML file with all your work, photos and documents inside. Next time, open the <b>newest</b> saved copy and carry on. You can also send that saved HTML file straight to the lead auditor – the master can import it just like an export file.</div>`;
}

/* ---------- import / export ---------- */
function filesFor(ids) { const o = {}; ids.forEach(id => { if (S.files[id]) o[id] = S.files[id]; }); return o; }
function auditorPayload(st = S, inst = CFG.instanceId) {
  const me = st.me || {sections: []}; const sids = me.sections || []; const items = {}; let fids = [...(st.genAtt || [])]; const secs = {};
  sids.forEach(sid => { const ss = st.secs[sid] || {att: []}; secs[sid] = ss; fids = fids.concat(ss.att || []); });
  Object.entries(st.items || {}).forEach(([id, r]) => { if (sids.includes(id.split('-')[0]) && hasContent(r)) { items[id] = r; fids = fids.concat(r.att || []); } });
  const lists = {}; if (sids.includes('ORG')) lists.cadre = st.lists.cadre; if (sids.includes('FLT')) lists.fleet = st.lists.fleet;
  const files = {}; fids.forEach(id => { if (st.files && st.files[id]) files[id] = st.files[id]; });
  return {kind: 'fto-audit-auditor', v: APPV, instanceId: inst, auditor: {name: me.name || me.label || 'Auditor', role: me.role}, sections: sids, exportedAt: new Date().toISOString(), meta: st.meta, secs, items, lists, genAtt: st.genAtt || [], files};
}
function auditorExport() {
  if (!S.me.name && !confirm('Your name is not entered (Me & my sections). Export anyway as "' + meName() + '"?')) return;
  if (!S.me.sections.length) { toast('Select your sections first'); return; }
  download(new Blob([JSON.stringify(auditorPayload())], {type: 'application/json'}), `${slug(S.meta.auditedOrg)}_${slug(meName())}_audit_${today()}.json`);
  toast('Audit file exported – send it to the lead auditor');
}
function saveAudit() { download(new Blob([JSON.stringify({kind: 'fto-audit-full', v: APPV, savedAt: new Date().toISOString(), state: S})], {type: 'application/json'}), `${slug(S.meta.auditedOrg)}_MASTER_audit_${today()}.json`); toast('Master file saved'); }
function listEmpty(l) { return !l || l.every(r => Object.entries(r).every(([k, v]) => !v || ['cat', 'src', 'role', 'designation', 'status'].includes(k))); }
const sameData = (a, b) => CF_FIELDS.every(([k]) => (a[k] || '') === (b[k] || ''));

// Normalise any supported file into {auditor, sections, secs, items, files, lists, gen, meta, text}
function unpack(p) {
  if (p.kind === 'fto-audit-auditor') return {auditor: (p.auditor && p.auditor.name) || 'Auditor', inst: p.instanceId, sections: p.sections || Object.keys(p.secs || {}), secs: p.secs || {}, items: p.items || {}, files: p.files || {}, lists: p.lists || {}, gen: p.genAtt || [], meta: p.meta};
  if (p.kind === 'fto-audit-section') return {auditor: p.auditor || 'Auditor', sections: [p.section], secs: p.secs, items: p.items || {}, files: p.files || {}, lists: p.lists || {}, gen: [], meta: null};
  if (p.kind === 'fto-audit-full') { const s = p.state || {}; return {auditor: 'Master file', sections: Object.keys(s.secs || {}).filter(k => s.secs[k].on), secs: s.secs || {}, items: s.items || {}, files: s.files || {}, lists: s.lists || {}, gen: s.genAtt || [], meta: s.meta, text: s.text}; }
  throw new Error('Not an FTO audit data file');
}
function integrate(p, fileName) {
  const u = unpack(p); const who = u.auditor; let n = 0, nc = 0;
  const inSec = new Set(u.sections);
  Object.entries(u.files).forEach(([id, f]) => { S.files[id] = Object.assign({}, f, {by: who}); });
  Object.entries(u.secs).forEach(([sid, rs]) => {
    if (!S.secs[sid] || !inSec.has(sid)) return; const ls = S.secs[sid];
    if (MASTER && p.kind !== 'fto-audit-full') { ls.on = true; if (!ls.auditor) ls.auditor = who; else if (ls.auditor !== who && ls.auditor2 !== who) ls.co = [...new Set((ls.co || []).concat(who))]; }
    if (rs.comment) { if (!ls.comment || ls.commentBy === who) { ls.comment = rs.comment; ls.commentBy = who; } else if (!ls.comment.includes(rs.comment)) ls.comment += `\n\n[${who}] ` + rs.comment; }
    ls.att = [...new Set(ls.att.filter(id => !S.files[id] || S.files[id].by !== who || (rs.att || []).includes(id)).concat(rs.att || []))];
    (rs.custom || []).forEach(c => { const i = ls.custom.findIndex(x => x[0] === c[0]); if (i < 0) ls.custom.push(c); else ls.custom[i] = c; });
  });
  const multi = MASTER && p.kind !== 'fto-audit-full';
  if (multi) { // this auditor's inputs that are no longer in their file were cleared by them
    Object.keys(S.inputs).forEach(id => { const x = itemDef(id); if (x && inSec.has(x.sec.id) && S.inputs[id][who] && !(u.items[id] && hasContent(u.items[id]))) delete S.inputs[id][who]; });
  }
  if (p.kind === 'fto-audit-full' && p.state && p.state.inputs) Object.entries(p.state.inputs).forEach(([id, o]) => { S.inputs[id] = Object.assign(S.inputs[id] || {}, o); });
  Object.entries(u.items).forEach(([id, ri]) => {
    const x = itemDef(id); if (!x || !inSec.has(x.sec.id) || !hasContent(ri)) return;
    const l = S.items[id]; const inc = Object.assign({}, ri); delete inc.att; delete inc.by; delete inc.mEdit; delete inc.rev; delete inc.at;
    const incAtt = ri.att || [];
    n++;
    if (multi) (S.inputs[id] = S.inputs[id] || {})[who] = Object.assign({}, inc, {att: incAtt, at: new Date().toISOString()});
    if (!l || !hasContent(l)) { S.items[id] = Object.assign({}, inc, {att: incAtt, by: who, at: new Date().toISOString()}); return; }
    // evidence from every auditor is kept on the reported record; this auditor's earlier evidence is replaced by its new list
    l.att = [...new Set((l.att || []).filter(fid => !S.files[fid] || S.files[fid].by !== who || incAtt.includes(fid)).concat(incAtt))];
    if (!l.by) l.by = who;
    if (l.by === who && !l.mEdit && !sameData(l, inc)) { CF_FIELDS.forEach(([k]) => { if (inc[k] != null && inc[k] !== '') l[k] = inc[k]; else delete l[k]; }); l.at = new Date().toISOString(); }
    if (multi && divergence(id).pending) nc++;
  });
  Object.entries(u.lists).forEach(([k, v]) => { if (v && !listEmpty(v) && (listEmpty(S.lists[k]) || S.lists[k + 'By'] === who)) { S.lists[k] = v; S.lists[k + 'By'] = who; } });
  if (u.meta) Object.entries(u.meta).forEach(([k, v]) => { if (v && !S.meta[k]) S.meta[k] = v; });
  if (u.text) Object.entries(u.text).forEach(([k, v]) => { if (v && (!S.text[k] || S.text[k] === DEFAULT_TEXT[k])) S.text[k] = v; });
  if (u.gen.length) S.genAtt = [...new Set(S.genAtt.filter(id => !S.files[id] || S.files[id].by !== who || u.gen.includes(id)).concat(u.gen))];
  gcFiles();
  if (MASTER) { const key = who + '|' + (u.inst || ''); S.imports = S.imports.filter(i => i.key !== key);
    S.imports.push({key, auditor: who, file: fileName || '', sections: u.sections, items: n, files: Object.keys(u.files).length, diverge: nc, at: new Date().toISOString()}); }
  return {n, nc, who};
}
function pickFiles(multiple, cb) {
  const i = document.createElement('input'); i.type = 'file'; i.accept = '.json,.html,.htm,application/json,text/html'; i.multiple = multiple;
  i.onchange = () => cb([...i.files]); i.click();
}
async function readJSON(f) {
  const txt = await readAs(f, 'readAsText');
  if (/^\s*\{/.test(txt)) return JSON.parse(txt);
  // a "Save progress" copy of this tool (HTML with the work inside)
  const m = txt.match(/<script id="saved">window\.SAVED=([\s\S]*?);<\/script>/);
  if (!m || m[1] === 'null') throw new Error('this HTML file has no saved work inside (use a file made with “Save progress”)');
  const sv = JSON.parse(m[1]); const st = sv.state || {};
  if (st.me) { const c = txt.match(/<script id="cfg">window\.CFG=([\s\S]*?);<\/script>/); let inst = ''; try { inst = JSON.parse(c[1]).instanceId; } catch (e) {} return auditorPayload(st, inst); }
  return {kind: 'fto-audit-full', v: APPV, state: st};
}
function doAct(a) {
  if (a === 'save') saveAudit();
  if (a === 'fsave') saveProgress();
  if (a === 'excel') window.open('/api/export-excel', '_blank');
  if (a === 'open') pickFiles(false, async fs => { try { const p = await readJSON(fs[0]); if (p.kind !== 'fto-audit-full') { toast('That is an auditor file – use Import auditor files'); return; } if (!confirm('Replace the current master with this file?')) return; S = normalise(p.state); save(); go('dash'); toast('Master file opened'); } catch (e) { toast('Could not open: ' + e.message); } });
  if (a === 'merge') pickFiles(true, async fs => { const out = []; for (const f of fs) { try { const r = integrate(await readJSON(f), f.name); out.push(`${r.who}: ${r.n} items${r.nc ? ', ' + r.nc + ' differ from another auditor' : ''}`); } catch (e) { out.push(f.name + ': ' + e.message); } } save(); render(); toast('Imported – ' + out.join(' · ')); });
  if (a === 'aexp') auditorExport();
  if (a === 'aopen') pickFiles(false, async fs => { try { const p = await readJSON(fs[0]); if (p.kind !== 'fto-audit-auditor') { toast('Choose a file exported from an auditor file'); return; } if (!confirm('Load this saved file? It replaces what is currently in this auditor file.')) return; const keepMe = S.me; S = freshState(); S.me = Object.assign(keepMe, {name: p.auditor.name, role: p.auditor.role, sections: p.sections}); applyMe(S); integrate(p, fs[0].name); applyMe(S); save(); render(); document.querySelector('header.top').innerHTML = headerHTML(); toast('Saved work loaded'); } catch (e) { toast('Could not open: ' + e.message); } });
  if (a === 'new') { if (confirm('Start a new blank audit? Save the master file first if you need it.')) { S = freshState(); save(); go('info'); } }
  if (a === 'reset') {
    const ans = prompt('CLEAR ALL ENTRIES?\n\nThis erases every result, finding, note, list row and attachment in this dashboard and in this browser\'s autosave. It cannot be undone.\n\nTip: click Cancel and use "Save progress" first if you may need the current work.\n\nType RESET to confirm:');
    if (ans === null) return;
    if (ans.trim().toUpperCase() !== 'RESET') { toast('Not cleared – you must type RESET to confirm'); return; }
    S = freshState(); S.edited = new Date().toISOString();
    document.title = MASTER ? 'FTO Audit – MASTER Dashboard' : 'FTO Audit – Auditor: ' + meName();
    document.querySelector('header.top').innerHTML = headerHTML();
    save(); go(!MASTER && !S.me.name ? 'info' : 'dash');
    toast('All entries cleared. Click Save progress to keep a blank copy of this file.');
  }
  if (a === 'split3') applySplit();
  if (a === 'mkall') makeAll();
  if (a === 'docx') buildDocx();
  if (a === 'print') doPrint();
}

/* ---------- events ---------- */
function bind() {
  document.addEventListener('input', e => { if (e.target.dataset.b && e.target.tagName !== 'SELECT') onField(e); if (e.target.dataset.me) { S.me[e.target.dataset.me] = e.target.value; save(); } });
  document.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.b) onField(e);
    if (t.id === 'mnavSel') go(t.value);
    if (t.dataset.up) { addFiles(t.dataset.up, [...t.files]); t.value = ''; }
    if (t.dataset.secon) { S.secs[t.dataset.secon].on = t.checked; save(); refreshNav(); }
    if (t.dataset.mysec) { const a = S.me.sections; const id = t.dataset.mysec; if (t.checked && !a.includes(id)) a.push(id); if (!t.checked) a.splice(a.indexOf(id), 1); S.me.sections = SECTIONS.map(s => s.id).filter(x => a.includes(x)); applyMe(S); save(); refreshNav(); }
    if (t.dataset.me) { applyMe(S); refreshNav(); document.querySelector('header.top').innerHTML = headerHTML(); render(); }
    if (t.dataset.regf) { regF[t.dataset.regf] = t.value; render(); }
  });
  document.addEventListener('click', e => {
    const clampEl = e.target.closest('.t-clamp');
    if (clampEl && !e.target.closest('a, button, input, select, textarea')) {
      clampEl.classList.toggle('open');
      return;
    }
    const tdEl = e.target.closest('table.t td');
    if (tdEl && !e.target.closest('a, button, input, select, textarea')) {
      const tc = tdEl.querySelector('.t-clamp');
      if (tc) {
        tc.classList.toggle('open');
        return;
      }
    }
    const t = e.target.closest('[data-go],[data-res],[data-act],[data-mk],[data-use],[data-rev],[data-arm],[data-zoom],[data-dl],[data-ladd],[data-lrm],[data-raise],[data-cadd],[data-cdel],[data-draft],[data-toggle-sec]');
    if (!t) return; const d = t.dataset;
        if (d.toggleSec) {
      const parts = d.toggleSec.split('|');
      let person = '';
      let sid = '';
      if (parts.length === 2) {
        if (!isNaN(parts[0])) {
          const idx = parseInt(parts[0], 10);
          person = (S.lists.team[idx] && S.lists.team[idx].name) ? S.lists.team[idx].name.trim() : '';
        } else {
          person = parts[0].trim();
        }
        sid = parts[1];
      }
      if (!person) {
        toast('Please enter the auditor name before assigning sections.');
      } else {
        const current = (S.secs[sid].auditor || '').trim().toLowerCase();
        if (current === person.toLowerCase()) {
          S.secs[sid].auditor = '';
        } else {
          S.secs[sid].auditor = person;
        }
        save(); render(); toast(`${sid} assigned to ${S.secs[sid].auditor || 'unassigned'}`);
      }
    } else if (d.go) { e.preventDefault(); go(d.go); }
    else if (d.res) setResult(d.res, d.v);
    else if (d.act) doAct(d.act);
    else if (d.mk) makeAuditorFile(d.mk);
    else if (d.use) { const i = d.use.indexOf('|'); useInput(d.use.slice(0, i), d.use.slice(i + 1)); }
    else if (d.rev) markReviewed(d.rev);
    else if (d.arm) { const [key, id] = d.arm.split('|'); const a = attTarget(key); const i = a.indexOf(id); if (i > -1) a.splice(i, 1); delete S.files[id]; save(); rerenderAtt(key); }
    else if (d.zoom) { const f = S.files[d.zoom]; $('#zimg').src = f.kind === 'image' ? f.d : f.pages[0].d; $('#zoom').classList.add('on'); }
    else if (d.dl) { const f = S.files[d.dl]; fetch(f.d).then(r => r.blob()).then(b => download(b, f.name)); }
    else if (d.ladd) { const cols = LIST_COLS[d.ladd]; S.lists[d.ladd].push(Object.fromEntries(cols.map(c => [c[0], '']))); save(); render(); }
    else if (d.lrm) { const [n, i] = d.lrm.split('.'); S.lists[n].splice(+i, 1); save(); render(); }
    else if (d.raise) { const x = itemDef(d.raise); const r = rec(d.raise); r.cls = 'OB'; r.risk = r.risk || 'L'; r.tf = r.tf || 'D90'; r.st = 'Open'; save(); document.getElementById('it-' + d.raise).outerHTML = itemCard(x.sec, x.def); refreshNav(); }
    else if (d.cadd) { const q = $('#newQ').value.trim(); if (!q) { toast('Enter the check item text'); return; } const ss = S.secs[d.cadd]; const ini = MASTER ? 'X' : (meName().replace(/^(capt|mr|ms|dr)\.?\s+/i, '').split(/\s+/).map(w => w[0] || '').join('').toUpperCase().replace(/[^A-Z]/g, '') || 'A'); let k = ss.custom.length + 1, id; do { id = `${d.cadd}-${ini}${String(k++).padStart(2, '0')}`; } while (itemDef(id)); ss.custom.push(SEC[d.cadd].type === 'ready' ? [id, q, $('#newE').value, ''] : [id, q, $('#newE').value.trim(), '', 'OB', 'M', 'D90', '']); save(); render(); toast(id + ' added'); }
    else if (d.cdel) { const [sid, id] = d.cdel.split('|'); if (!confirm('Delete item ' + id + '?')) return; S.secs[sid].custom = S.secs[sid].custom.filter(c => c[0] !== id); delete S.items[id]; save(); render(); }
    else if (d.draft) { if ((S.text[d.draft] || '').trim() && !confirm('Replace the current text with a draft?')) return; draft(d.draft); }
  });
  $('#zoom').addEventListener('click', () => $('#zoom').classList.remove('on'));
  $('#printGo').addEventListener('click', () => { $('#printBar').classList.remove('on'); window.print(); });
  $('#printX').addEventListener('click', () => $('#printBar').classList.remove('on'));
}

/* ============================================================
   REPORT MODEL (shared by Word and Print/PDF)
   ============================================================ */
function reportModel() {
  const st = stats(); const secs = SECTIONS.filter(s => S.secs[s.id].on);
  let fig = 0; const annex = [];
  const evidence = (ids, label) => {
    const imgs = [], docs = [];
    (ids || []).forEach(id => { const f = S.files[id]; if (!f) return;
      const cap = (f.cap || f.name) + (f.by && MASTER ? ' (' + f.by + ')' : '');
      if (f.kind === 'image') { fig++; imgs.push({n: fig, d: f.d, w: f.w, h: f.h, cap: `${label} – ${cap}`}); annex.push({fig: fig, label, name: f.name, type: 'Photograph / image', cap: f.cap}); }
      else if (f.kind === 'pdf' && f.pages && f.pages.length) { const n0 = fig + 1; f.pages.forEach((p, i) => { fig++; imgs.push({n: fig, d: p.d, w: p.w, h: p.h, cap: `${label} – ${cap} (page ${i + 1} of ${f.totalPages || f.pages.length})`}); }); annex.push({fig: n0 + (fig > n0 ? '–' + fig : ''), label, name: f.name, type: 'PDF document' + ((f.totalPages || 0) > f.pages.length ? ` (first ${f.pages.length} of ${f.totalPages} pages reproduced)` : ''), cap: f.cap}); }
      else { docs.push({name: f.name, cap: f.cap}); annex.push({fig: '—', label, name: f.name, type: 'Document (retained in audit data file)', cap: f.cap}); }
    });
    return {imgs, docs};
  };
  let num = 3; const body = secs.map(s => {
    num++;
    const items = itemsOf(s.id).map(d => ({d, r: S.items[d[0]] || {}}));
    const secEv = evidence(S.secs[s.id].att, s.title);
    const itemEv = items.map(x => ({id: x.d[0], ev: evidence(x.r.att, x.d[0])})).filter(x => x.ev.imgs.length || x.ev.docs.length);
    return {num, s, items, findings: s.type === 'check' ? items.filter(x => x.r.cls) : [], secEv, itemEv};
  });
  const genEv = evidence(S.genAtt, 'General');
  const f = findingsSorted(); const c = (k, v) => f.filter(x => x.r[k] === v).length;
  return {st, body, f, c, genEv, annex, cap: capGroups(), after: num};
}
const resText = (s, r) => s.type === 'ready' ? (r.r ? RDY[r.r] : 'Not assessed') : (r.r ? RES[r.r] : 'Not assessed');
const resFill = r => ({C: 'E3F3EA', P: 'FDF3DC', NC: 'FDE8E6', NE: 'EFE7F8', NA: 'EEF0F2', R: 'E3F3EA', PR: 'FDF3DC', UC: 'FDF3DC', NR: 'FDE8E6', NP: 'FDE8E6'}[r.r] || 'FFFFFF');
const period = () => S.meta.from ? fmtDate(S.meta.from) + (S.meta.to && S.meta.to !== S.meta.from ? ' to ' + fmtDate(S.meta.to) : '') : '';
const teamNames = () => (S.lists.team || []).filter(t => t.name);
const locs = () => (S.lists.locations || []).filter(l => l.name).map(l => `${l.name}${l.state ? ', ' + l.state : ''}${l.status ? ' (' + l.status + ')' : ''}`);

/* ---------- PRINT / PDF ---------- */
function doPrint() {
  const M = reportModel(); const m = S.meta; const p = s => `<p>${esc(s)}</p>`;
  const tbl = (hd, rows) => `<table><thead><tr>${hd.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  const figs = ev => (ev.imgs.length ? `<div class="figs">${ev.imgs.map(i => `<figure><img src="${i.d}"><figcaption>Figure ${i.n}: ${esc(i.cap)}</figcaption></figure>`).join('')}</div>` : '') + (ev.docs.length ? `<p><i>Supporting documents: ${ev.docs.map(d => esc(d.name + (d.cap ? ' – ' + d.cap : ''))).join('; ')} (retained in audit data file)</i></p>` : '');
  let h = `<div class="cover"><div style="margin-bottom:18pt"><img src="${LOGO.d}" alt="Marigold Aviation" style="width:75mm;height:auto;border:0"></div><div style="font-weight:700;letter-spacing:.05em">${esc((m.auditingOrg || '').toUpperCase())}</div><h1 style="margin:14pt 0 6pt">${esc((m.title || '').toUpperCase())}</h1><div style="font-size:15pt;font-weight:700">${esc(m.auditedOrg)}</div><div>${locs().map(esc).join('<br>')}</div><div style="margin-top:14pt;font-weight:700">Audit period: ${esc(period())}</div><div>Report status: ${esc(m.status)} | Classification: ${esc(m.classification)}</div><div style="margin-top:20pt">Prepared by the audit team</div><div>${teamNames().map(t => esc(t.name + (t.role ? ' (' + t.role + ')' : ''))).join(' · ')}</div></div>`;
  h += `<h2>Contents</h2>${['Audit Information', 'Executive Summary', 'Scope, Methodology and Limitations'].concat(M.body.map(b => b.s.title)).concat(['Consolidated Findings Register', 'Corrective Action Programme', "Auditor's Conclusion"]).map((t, i) => `<div>${i + 1}. ${esc(t)}</div>`).join('')}<div>Annex A. Evidence index</div>`;
  h += `<h2 class="pb">1. Audit Information</h2>` + tbl(['Item', 'Details'], [['Audit conducted by', esc(m.auditingOrg)], ['Audited organisation', esc(m.auditedOrg)], ['Approval / reference', esc(m.approvalNo)], ['Locations', locs().map(esc).join('<br>')], ['Audit team', teamNames().map(t => esc(t.name + ' – ' + t.role)).join('<br>')], ['Audit period', esc(period())], ['Audit type', esc(m.type)], ['Regulatory framework', esc(m.framework)], ['Report status', esc(m.status)], ['Distribution', esc(m.distribution)]]);
  h += `<h3>1.1 Purpose of the Audit</h3>${p(S.text.purpose)}<h3>1.2 Personnel Engaged During the Audit</h3>` + tbl(['Representative', 'Designation / Department'], (S.lists.personnel || []).filter(x => x.name || x.designation).map(x => [esc(x.name), esc(x.designation)]));
  h += `<h2 class="pb">2. Executive Summary</h2>${p(S.text.exec)}<h3>2.1 Principal Risk Themes</h3>${p(S.text.themes)}<h3>2.2 Findings Summary</h3>` + tbl(['Classification', 'Count', 'Definition'], Object.keys(CLS).map(k => [`<b>${CLS[k]}</b>`, M.c('cls', k), CLS_DEF[k]]).concat([['<b>Total findings raised</b>', M.f.length, '—']])) + tbl(['Risk rating', 'Count', 'Basis'], Object.keys(RISK).map(k => [`<b>${RISK[k]}</b>`, M.c('risk', k), RISK_DEF[k]])) + `<h3>2.3 Due Diligence Position</h3>${p(S.text.position)}`;
  h += `<h2 class="pb">3. Scope, Methodology and Limitations</h2><h3>3.1 Scope</h3><ul>${M.body.map(b => `<li>${esc(b.s.title)} – ${esc(b.s.intro)}</li>`).join('')}</ul><h3>3.2 Methodology</h3>${p(S.text.methodology)}<h3>3.3 Limitations</h3><ul>${S.text.limitations.split('\n').filter(x => x.trim()).map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;
  M.body.forEach(b => {
    const s = b.s; const ss = S.secs[s.id];
    h += `<h2 class="pb">${b.num}. ${esc(s.title)}</h2>${ss.auditor ? `<p><i>Section auditor(s): ${esc(secAuditors(s.id))}</i></p>` : ''}${ss.comment ? p(ss.comment) : ''}`;
    if (s.id === 'ORG') h += `<h3>Instructional cadre</h3>` + tbl(['Category', 'Number', 'Notes'], (S.lists.cadre || []).filter(x => x.count || x.notes).map(x => [esc(x.cat), esc(x.count), esc(x.notes)]));
    if (s.id === 'FLT') h += `<h3>Fleet reconciliation</h3>` + tbl(['Source', 'Aircraft type(s)', 'Aircraft', 'Notes'], (S.lists.fleet || []).filter(x => x.count || x.type || x.notes).map(x => [esc(x.src), esc(x.type), esc(x.count), esc(x.notes)]));
    if (s.type === 'ready') h += `<h3>Readiness summary</h3>` + tbl(['Ref', 'Element', 'Readiness', 'Status as assessed', 'Critical path', 'Operator date', 'Assessed date'], b.items.map(x => [x.d[0], esc(x.d[1]), `<span style="background:#${resFill(x.r)};-webkit-print-color-adjust:exact;print-color-adjust:exact;padding:0 3pt">${esc(resText(s, x.r))}</span>`, esc(x.r.status || ''), esc(x.r.cp || ''), fmtDate(x.r.opDate), fmtDate(x.r.asDate)])) + b.items.filter(x => repComment(x.d[0], x.r)).map(x => `<p><b>${x.d[0]}:</b> ${esc(repComment(x.d[0], x.r)).replace(/\n/g, '<br>')}</p>`).join('');
    else {
      h += `<h3>Checklist results</h3>` + tbl(['Ref', 'Check item', 'Result', 'Auditor comments'], b.items.map(x => [x.d[0], esc(x.d[1]), `<span style="background:#${resFill(x.r)};-webkit-print-color-adjust:exact;print-color-adjust:exact;padding:0 3pt">${esc(resText(s, x.r))}</span>`, esc(repComment(x.d[0], x.r)).replace(/\n/g, '<br>')]));
      if (b.findings.length) h += `<h3>Findings raised: ${b.findings.map(x => x.d[0]).join(', ')}</h3>` + b.findings.map(x => `<div class="fbox"><b>${x.d[0]}</b> – ${esc(CLS[x.r.cls])}${x.r.risk ? ' | Risk: ' + RISK[x.r.risk] : ''}${x.r.tf ? ' | ' + esc(TF[x.r.tf]) : ''}<br>${esc(findText(x.r, x.d))}${x.r.act ? `<br><b>Required action:</b> ${esc(x.r.act)}` : ''}</div>`).join('');
    }
    if (b.secEv.imgs.length || b.secEv.docs.length || b.itemEv.length) h += `<h3>Evidence</h3>` + figs(b.secEv) + b.itemEv.map(x => figs(x.ev)).join('');
  });
  let n = M.after;
  h += `<h2 class="pb">${++n}. Consolidated Findings Register</h2><p>Classification and risk rating represent the assessment of the audit team. They are not a regulatory determination by the DGCA.</p>` + tbl(['Ref', 'Finding', 'Classification', 'Risk', 'Status'], M.f.map(x => [x.id, esc(findText(x.r, x.def)), esc(CLS[x.r.cls]), esc(RISK[x.r.risk] || ''), esc(x.r.st || 'Open')]));
  let k = 0; h += `<h2 class="pb">${++n}. Corrective Action Programme</h2>`;
  [['IMM', 'Immediate Actions – To Be Completed Before Cadet Placement'], ['D30', 'Short-Term Actions – Within 30 Days'], ['D90', 'Medium-Term Actions – Within 90 Days'], ['', 'Timeframe Not Set']].forEach(([t, title]) => { if (!M.cap[t].length) return; h += `<h3>${title}</h3>` + tbl(['No.', 'Action', 'Related finding', 'Owner', 'Target', 'Status'], M.cap[t].map(x => [++k, esc(x.r.act || ''), x.id, esc(x.r.owner || ''), fmtDate(x.r.due), esc(x.r.st || 'Open')])); });
  h += `<h2 class="pb">${++n}. Auditor's Conclusion</h2>${p(S.text.conclusion)}` + (M.genEv.imgs.length || M.genEv.docs.length ? `<h3>General evidence</h3>${figs(M.genEv)}` : '');
  h += `<h3>Sign-off</h3>` + tbl(teamNames().map(t => esc(t.role)), [teamNames().map(t => esc(t.name)), teamNames().map(() => 'Signature:<br><br>'), teamNames().map(() => 'Date:')]);
  h += `<h2 class="pb">Annex A. Evidence Index</h2>` + tbl(['Figure', 'Reference', 'File', 'Type', 'Caption'], M.annex.map(a => [a.fig, esc(a.label), esc(a.name), esc(a.type), esc(a.cap || '')]));
  h += `<p style="margin-top:14pt;font-size:8pt"><i>${esc(m.classification)}. ${esc(m.distribution)}</i></p>`;
  const LG = `<div class="plogo"><img src="${LOGO.d}" alt="Marigold Aviation"></div>`;
  h = h.replace('<h2>Contents</h2>', LG + '<h2>Contents</h2>').split('<h2 class="pb">').join('<div class="pb">' + LG + '</div><h2>');
  $('#print').innerHTML = h;
  const imgs = [...$('#print').querySelectorAll('img')];
  const bar = $('#printBar'); bar.querySelector('b').textContent = 'Preparing report…'; bar.querySelector('button').disabled = true; bar.classList.add('on');
  Promise.all(imgs.map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; }))).then(() => { bar.querySelector('b').textContent = 'Report ready (' + imgs.length + ' images).'; bar.querySelector('button').disabled = false; });
}

/* ---------- WORD (.docx) ---------- */
function b64ToBytes(dataUrl) { const b = atob(dataUrl.split(',')[1]); const u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
async function buildDocx() {
  if (!window.docx) { toast('Word library not loaded'); return; }
  toast('Building Word report…');
  const D = window.docx; const {Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ImageRun, AlignmentType, ShadingType, Footer, Header, PageNumber, BorderStyle} = D;
  const M = reportModel(); const m = S.meta; const W = 9638;
  const paras = (t, o = {}) => String(t || '').split('\n').map(line => new Paragraph({spacing: {after: o.after ?? 80}, alignment: o.align, children: [new TextRun({text: line, bold: o.bold, italics: o.italics, size: o.size, color: o.color})]}));
  const H1 = (t, br = true) => new Paragraph({text: t, heading: HeadingLevel.HEADING_1, pageBreakBefore: br});
  const H2 = t => new Paragraph({text: t, heading: HeadingLevel.HEADING_2});
  const cell = (c, w, hdr) => { const o = typeof c === 'object' && c !== null ? c : {t: c};
    return new TableCell({width: {size: w, type: WidthType.DXA}, margins: {top: 50, bottom: 50, left: 90, right: 90},
      shading: hdr ? {type: ShadingType.CLEAR, color: 'auto', fill: 'DFE8F1'} : (o.fill ? {type: ShadingType.CLEAR, color: 'auto', fill: o.fill} : undefined),
      children: String(o.t == null ? '' : o.t).split('\n').map(l => new Paragraph({children: [new TextRun({text: l, bold: hdr || o.bold, size: 18})]}))}); };
  const tbl = (hd, rows, fr) => { const ws = fr.map(f => Math.round(f * W));
    return new Table({width: {size: W, type: WidthType.DXA}, columnWidths: ws, rows: [new TableRow({tableHeader: true, children: hd.map((h, i) => cell(h, ws[i], true))})].concat(rows.map(r => new TableRow({cantSplit: true, children: r.map((c, i) => cell(c, ws[i]))})))}); };
  const gap = () => new Paragraph({text: '', spacing: {after: 60}});
  const figs = ev => { const out = []; const im = ev.imgs;
    const fit = (i, mw, mh) => { const k = Math.min(mw / i.w, mh / i.h, 1); return {width: Math.round(i.w * k), height: Math.round(i.h * k)}; };
    const figCell = i => new TableCell({width: {size: W / 2, type: WidthType.DXA}, borders: {top: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, bottom: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, left: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, right: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}}, margins: {top: 60, bottom: 60, left: 60, right: 60},
      children: i ? [new Paragraph({alignment: AlignmentType.CENTER, children: [new ImageRun({type: 'jpg', data: b64ToBytes(i.d), transformation: fit(i, 300, 330)})]}), new Paragraph({alignment: AlignmentType.CENTER, children: [new TextRun({text: `Figure ${i.n}: ${i.cap}`, size: 16, italics: true})]})] : [new Paragraph('')]});
    for (let k = 0; k < im.length; k += 2) out.push(new Table({width: {size: W, type: WidthType.DXA}, columnWidths: [W / 2, W / 2], rows: [new TableRow({cantSplit: true, children: [figCell(im[k]), figCell(im[k + 1])]})]}));
    if (ev.docs.length) out.push(...paras('Supporting documents: ' + ev.docs.map(d => d.name + (d.cap ? ' – ' + d.cap : '')).join('; ') + ' (retained in audit data file)', {italics: true, size: 18}));
    return out; };
  const ch = [];
  // cover – Marigold logo
  const logoBytes = b64ToBytes(LOGO.d);
  ch.push(new Paragraph({alignment: AlignmentType.CENTER, spacing: {before: 600}, children: [new ImageRun({type: 'png', data: logoBytes, transformation: {width: 300, height: Math.round(300 * LOGO.h / LOGO.w)}})]}));
  ch.push(new Paragraph({spacing: {before: 900, after: 200}, alignment: AlignmentType.CENTER, children: [new TextRun({text: (m.auditingOrg || '').toUpperCase(), bold: true, size: 28, color: '1F4E79'})]}));
  ch.push(new Paragraph({alignment: AlignmentType.CENTER, spacing: {after: 300}, children: [new TextRun({text: (m.title || '').toUpperCase(), bold: true, size: 36})]}));
  ch.push(new Paragraph({alignment: AlignmentType.CENTER, spacing: {after: 120}, children: [new TextRun({text: m.auditedOrg || '', bold: true, size: 30})]}));
  locs().forEach(l => ch.push(new Paragraph({alignment: AlignmentType.CENTER, children: [new TextRun({text: l, size: 22})]})));
  ch.push(new Paragraph({alignment: AlignmentType.CENTER, spacing: {before: 400}, children: [new TextRun({text: 'Audit period: ' + period(), bold: true, size: 24})]}));
  ch.push(new Paragraph({alignment: AlignmentType.CENTER, children: [new TextRun({text: `Report status: ${m.status} | Classification: ${m.classification}`, size: 20})]}));
  ch.push(new Paragraph({alignment: AlignmentType.CENTER, spacing: {before: 600}, children: [new TextRun({text: 'Prepared by the audit team', size: 20})]}));
  ch.push(new Paragraph({alignment: AlignmentType.CENTER, children: [new TextRun({text: teamNames().map(t => t.name + (t.role ? ' (' + t.role + ')' : '')).join(' · '), size: 20})]}));
  // contents
  ch.push(H1('Contents'));
  ['Audit Information', 'Executive Summary', 'Scope, Methodology and Limitations'].concat(M.body.map(b => b.s.title)).concat(['Consolidated Findings Register', 'Corrective Action Programme', "Auditor's Conclusion", 'Annex A. Evidence Index']).forEach((t, i, a) => ch.push(new Paragraph({children: [new TextRun({text: (i < a.length - 1 ? (i + 1) + '. ' : '') + t, size: 22})]})));
  // 1
  ch.push(H1('1. Audit Information'));
  ch.push(tbl(['Item', 'Details'], [['Audit conducted by', m.auditingOrg], ['Audited organisation', m.auditedOrg], ['Approval / reference', m.approvalNo], ['Locations', locs().join('\n')], ['Audit team', teamNames().map(t => t.name + ' – ' + t.role).join('\n')], ['Audit period', period()], ['Audit type', m.type], ['Regulatory framework', m.framework], ['Report status', m.status], ['Distribution', m.distribution]].map(r => [{t: r[0], bold: true}, r[1]]), [.28, .72]));
  ch.push(H2('1.1 Purpose of the Audit'), ...paras(S.text.purpose));
  ch.push(H2('1.2 Personnel Engaged During the Audit'), tbl(['Representative', 'Designation / Department'], (S.lists.personnel || []).filter(x => x.name || x.designation).map(x => [{t: x.name, bold: true}, x.designation]), [.4, .6]));
  // 2
  ch.push(H1('2. Executive Summary'), ...paras(S.text.exec), H2('2.1 Principal Risk Themes'), ...paras(S.text.themes), H2('2.2 Findings Summary'));
  ch.push(tbl(['Classification', 'Count', 'Definition'], Object.keys(CLS).map(k => [{t: CLS[k], bold: true}, String(M.c('cls', k)), CLS_DEF[k]]).concat([[{t: 'Total findings raised', bold: true}, String(M.f.length), '—']]), [.28, .1, .62]), gap());
  ch.push(tbl(['Risk rating', 'Count', 'Basis'], Object.keys(RISK).map(k => [{t: RISK[k], bold: true}, String(M.c('risk', k)), RISK_DEF[k]]), [.28, .1, .62]));
  ch.push(H2('2.3 Due Diligence Position'), ...paras(S.text.position));
  // 3
  ch.push(H1('3. Scope, Methodology and Limitations'), H2('3.1 Scope'));
  M.body.forEach(b => ch.push(new Paragraph({bullet: {level: 0}, children: [new TextRun({text: b.s.title + ' – ', bold: true}), new TextRun(b.s.intro)]})));
  ch.push(H2('3.2 Methodology'), ...paras(S.text.methodology), H2('3.3 Limitations'));
  S.text.limitations.split('\n').filter(x => x.trim()).forEach(x => ch.push(new Paragraph({bullet: {level: 0}, text: x})));
  // sections
  M.body.forEach(b => {
    const s = b.s; const ss = S.secs[s.id];
    ch.push(H1(`${b.num}. ${s.title}`));
    if (ss.auditor) ch.push(...paras('Section auditor(s): ' + secAuditors(s.id), {italics: true}));
    if (ss.comment) ch.push(...paras(ss.comment));
    if (s.id === 'ORG') { const r = (S.lists.cadre || []).filter(x => x.count || x.notes); if (r.length) ch.push(H2('Instructional cadre'), tbl(['Category', 'Number', 'Notes'], r.map(x => [{t: x.cat, bold: true}, x.count, x.notes]), [.4, .15, .45])); }
    if (s.id === 'FLT') { const r = (S.lists.fleet || []).filter(x => x.count || x.type || x.notes); if (r.length) ch.push(H2('Fleet reconciliation'), tbl(['Source', 'Aircraft type(s)', 'Aircraft', 'Notes'], r.map(x => [{t: x.src, bold: true}, x.type, x.count, x.notes]), [.34, .2, .1, .36])); }
    if (s.type === 'ready') {
      ch.push(H2('Readiness summary'), tbl(['Ref', 'Element', 'Readiness', 'Status as assessed', 'Critical path', 'Operator date', 'Assessed date'], b.items.map(x => [x.d[0], x.d[1], {t: resText(s, x.r), fill: resFill(x.r)}, x.r.status || '', x.r.cp || '', fmtDate(x.r.opDate), fmtDate(x.r.asDate)]), [.07, .2, .12, .21, .18, .11, .11]));
      b.items.filter(x => repComment(x.d[0], x.r)).forEach(x => ch.push(new Paragraph({spacing: {before: 60}, children: [new TextRun({text: x.d[0] + ': ', bold: true}), new TextRun(repComment(x.d[0], x.r).replace(/\n/g, ' | '))]})));
    } else {
      ch.push(H2('Checklist results'), tbl(['Ref', 'Check item', 'Result', 'Auditor comments'], b.items.map(x => [x.d[0], x.d[1], {t: resText(s, x.r), fill: resFill(x.r)}, repComment(x.d[0], x.r)]), [.1, .39, .13, .38]));
      if (b.findings.length) { ch.push(H2('Findings raised: ' + b.findings.map(x => x.d[0]).join(', ')));
        b.findings.forEach(x => ch.push(tbl([`${x.d[0]} – ${CLS[x.r.cls]}`, `Risk: ${RISK[x.r.risk] || '—'}   |   ${x.r.tf ? TF[x.r.tf] : ''}`], [[{t: 'Finding', bold: true}, findText(x.r, x.d)], [{t: 'Required action', bold: true}, x.r.act || '']], [.22, .78]), gap())); }
    }
    if (b.secEv.imgs.length || b.secEv.docs.length || b.itemEv.length) { ch.push(H2('Evidence'), ...figs(b.secEv)); b.itemEv.forEach(x => ch.push(...figs(x.ev))); }
  });
  let n = M.after;
  ch.push(H1(`${++n}. Consolidated Findings Register`), ...paras('Classification and risk rating represent the assessment of the audit team. They are not a regulatory determination by the DGCA.', {italics: true}));
  ch.push(tbl(['Ref', 'Finding', 'Classification', 'Risk', 'Status'], M.f.map(x => [{t: x.id, bold: true}, findText(x.r, x.def), CLS[x.r.cls], RISK[x.r.risk] || '', x.r.st || 'Open']), [.1, .5, .18, .1, .12]));
  ch.push(H1(`${++n}. Corrective Action Programme`)); let k = 0;
  [['IMM', 'Immediate Actions – To Be Completed Before Cadet Placement'], ['D30', 'Short-Term Actions – Within 30 Days'], ['D90', 'Medium-Term Actions – Within 90 Days'], ['', 'Timeframe Not Set']].forEach(([t, title]) => { if (!M.cap[t].length) return; ch.push(H2(title), tbl(['No.', 'Action', 'Related finding', 'Owner', 'Target', 'Status'], M.cap[t].map(x => [String(++k), x.r.act || '', x.id, x.r.owner || '', fmtDate(x.r.due), x.r.st || 'Open']), [.06, .46, .12, .14, .11, .11])); });
  ch.push(H1(`${++n}. Auditor's Conclusion`), ...paras(S.text.conclusion));
  if (M.genEv.imgs.length || M.genEv.docs.length) ch.push(H2('General evidence'), ...figs(M.genEv));
  const tn = teamNames(); if (tn.length) ch.push(H2('Sign-off'), tbl(tn.map(t => t.role || 'Auditor'), [tn.map(t => ({t: t.name, bold: true})), tn.map(() => 'Signature:\n\n'), tn.map(() => 'Date:')], tn.map(() => 1 / tn.length)));
  ch.push(H1('Annex A. Evidence Index'), tbl(['Figure', 'Reference', 'File', 'Type', 'Caption'], M.annex.map(a => [String(a.fig), a.label, a.name, a.type, a.cap || '']), [.1, .2, .25, .2, .25]));
  ch.push(new Paragraph({spacing: {before: 300}, children: [new TextRun({text: `${m.classification}. ${m.distribution}`, italics: true, size: 16})]}));
  const doc = new Document({creator: m.auditingOrg || 'Audit team', title: `${m.title} – ${m.auditedOrg}`,
    styles: {default: {document: {run: {font: 'Calibri', size: 21}}},
      paragraphStyles: [{id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: {size: 30, bold: true, color: '1F4E79'}, paragraph: {spacing: {before: 120, after: 160}}},
        {id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: {size: 24, bold: true, color: '1F4E79'}, paragraph: {spacing: {before: 220, after: 100}, keepNext: true}}]},
    sections: [{properties: {titlePage: true, page: {margin: {top: 1000, bottom: 1000, left: 1134, right: 1134}}},
      headers: {first: new Header({children: [new Paragraph('')]}), default: new Header({children: [new Table({width: {size: W, type: WidthType.DXA}, columnWidths: [2600, W - 2600], borders: {top: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, left: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, right: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, insideHorizontal: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, insideVertical: {style: BorderStyle.NONE, size: 0, color: 'FFFFFF'}, bottom: {style: BorderStyle.SINGLE, size: 6, color: '2B3585'}},
        rows: [new TableRow({children: [new TableCell({width: {size: 2600, type: WidthType.DXA}, children: [new Paragraph({children: [new ImageRun({type: 'png', data: logoBytes, transformation: {width: 110, height: Math.round(110 * LOGO.h / LOGO.w)}})]})]}),
          new TableCell({width: {size: W - 2600, type: WidthType.DXA}, verticalAlign: 'bottom', children: [new Paragraph({alignment: AlignmentType.RIGHT, children: [new TextRun({text: `${m.auditedOrg || ''} – ${m.title || ''}`, size: 16, color: '777777'})]})]})]})]}), new Paragraph({text: '', spacing: {after: 0}})]})},
      footers: {default: new Footer({children: [new Paragraph({alignment: AlignmentType.CENTER, children: [new TextRun({size: 16, color: '777777', children: [`${m.classification}   |   Page `, PageNumber.CURRENT, ' of ', PageNumber.TOTAL_PAGES]})]})]})},
      children: ch}]});
  try { const blob = await Packer.toBlob(doc); download(blob, `${slug(m.auditedOrg)}_Audit_Report_${today()}.docx`); toast('Word report downloaded'); }
  catch (e) { console.error(e); toast('Word export failed: ' + e.message); }
}

/* ---------- init ---------- */
(async function init() {
  try { if (window.pdfjsLib) { const w = document.getElementById('pdfw').textContent; pdfjsLib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([w], {type: 'text/javascript'})); } } catch (e) {}
  const auto = await load(); const emb = window.SAVED && window.SAVED.state;
  let how = '';
  if (emb && (!auto || (emb.edited || emb.fileSavedAt || '') >= (auto.edited || ''))) { S = normalise(emb); how = 'file'; }
  else if (auto) { S = normalise(auto); how = 'auto'; }
  document.title = MASTER ? 'FTO Audit – MASTER Dashboard' : 'FTO Audit – Auditor: ' + meName();
  document.querySelector('header.top').innerHTML = headerHTML();
  if (!MASTER && !S.me.name) view = 'info';
  bind(); render();
  markDirty(how === 'auto' && (!S.fileSavedAt || (S.edited || '') > S.fileSavedAt));
  if (how === 'file') toast('Opened with the work saved in this file (' + hhmm(S.fileSavedAt) + ')');
  if (how === 'auto' && emb) toast('This browser has newer work than this file – newer work loaded. Click Save progress.');
  else if (how === 'auto') toast('Work restored from this browser. Click Save progress to keep it in a file.');
  window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
  document.addEventListener('keydown', e => { if ((e.metaKey || e.ctrlKey) && (e.key === 's' || e.key === 'S')) { e.preventDefault(); saveProgress(); } });
})();


/* ---------- LIVE BACKGROUND AUTO-REFLECTION LOOP ---------- */
let pollBusy = false;
setInterval(async () => {
  if (pollBusy || dirty) return;
  const activeTag = document.activeElement ? document.activeElement.tagName : '';
  if (activeTag === 'INPUT' || activeTag === 'TEXTAREA') return;

  try {
    const res = await fetch('/api/sync');
    if (!res.ok) return;
    const data = await res.json();
    if (data.savedAt && S.fileSavedAt && data.savedAt > S.fileSavedAt) {
      pollBusy = true;
      const stateRes = await fetch('/api/state');
      if (stateRes.ok) {
        const stateData = await stateRes.json();
        if (stateData.state) {
          const remote = stateData.state;
          Object.assign(S.items, remote.items || {});
          Object.assign(S.inputs, remote.inputs || {});
          if (MASTER) {
            Object.assign(S.meta, remote.meta || {});
            Object.assign(S.lists, remote.lists || {});
          }
          S.files = Object.assign(S.files || {}, remote.files || {});
          S.fileSavedAt = data.savedAt;
          refreshNav();
          render();
          const el = document.getElementById('saveInd');
          if (el) el.innerHTML = `✓ Live Synced (${hhmm(data.savedAt)})<br><span style="opacity:.8">Auto-reflected from team</span>`;
        }
      }
      pollBusy = false;
    }
  } catch (e) {
    pollBusy = false;
  }
}, 2500);
