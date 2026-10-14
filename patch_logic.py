import re

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic_original.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update save and persistence
save_old = """function markDirty(v) {
  dirty = v; const el = $('#saveInd'); if (!el) return;
  const fileTxt = S.fileSavedAt ? 'Saved to file ' + hhmm(S.fileSavedAt) : 'Not yet saved to a file';
  el.innerHTML = dirty ? `<b style="color:#ffd27a">● Unsaved changes</b> – click Save progress<br><span style="opacity:.8">${autoOK === false ? 'Browser autosave not available' : 'Kept temporarily in this browser'}</span>`
    : `✓ ${fileTxt}`;
}
function saveProgress() {
  S.fileSavedAt = new Date().toISOString(); S.edited = S.edited || S.fileSavedAt;
  const html = withSaved(PRISTINE, {kind: 'fto-audit-saved', v: APPV, savedAt: S.fileSavedAt, state: S});
  const t = new Date(), z = n => String(n).padStart(2, '0'); const stamp = `${t.getFullYear()}${z(t.getMonth() + 1)}${z(t.getDate())}_${z(t.getHours())}${z(t.getMinutes())}`;
  const name = MASTER ? `${slug(S.meta.auditedOrg)}_MASTER_saved_${stamp}.html` : `${slug(S.meta.auditedOrg)}_AUDITOR_${slug(meName())}_saved_${stamp}.html`;
  download(new Blob([html], {type: 'text/html'}), name);
  save(); markDirty(false);
  toast('Saved: ' + name + ' (in Downloads). Next time open this newest file.');
}
function save() {
  S.edited = new Date().toISOString(); markDirty(true);
  clearTimeout(saveT);
  saveT = setTimeout(async () => {
    try { const d = await withTimeout(db(), 2000); if (!d) throw new Error('no db'); const tx = d.transaction('kv', 'readwrite'); tx.objectStore('kv').put(S, DBKEY);
      tx.onerror = () => { autoOK = false; markDirty(dirty); };
      tx.oncomplete = () => { autoOK = true; markDirty(dirty); };
    } catch (e) { autoOK = false; markDirty(dirty); }
  }, 500);
}
const withTimeout = (p, ms) => Promise.race([p, new Promise(r => setTimeout(() => r(null), ms))]);
async function load() {
  return withTimeout(load0(), 2000);
}"""

save_new = """function markDirty(v) {
  dirty = v; const el = $('#saveInd'); if (!el) return;
  if (dirty) {
    el.innerHTML = `<span style="color:#ffd27a;font-weight:600">● Saving to OneDrive...</span>`;
  }
}
function markSaved(iso) {
  dirty = false;
  const el = $('#saveInd'); if (!el) return;
  const timeStr = hhmm(iso || new Date().toISOString());
  el.innerHTML = `<span style="color:#10b981;font-weight:600">✓ Auto-saved at ${timeStr}</span><br><span style="opacity:.85;font-size:8.5pt">OneDrive & Excel synced</span>`;
}
async function saveNow() {
  toast('Saving to OneDrive & updating Excel...');
  markDirty(true);
  try {
    S.edited = new Date().toISOString();
    const resp = await fetch('/api/save', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({state: S})
    });
    if (resp.ok) {
      const data = await resp.json();
      markSaved(data.savedAt);
      toast('✓ Saved! Excel & images updated in OneDrive.');
    } else {
      toast('Warning: Server save returned error');
    }
  } catch (e) {
    console.error(e);
    toast('Error saving to server: ' + e.message);
  }
}
function saveProgress() {
  saveNow();
}
function save() {
  S.edited = new Date().toISOString();
  markDirty(true);
  clearTimeout(saveT);
  saveT = setTimeout(async () => {
    try {
      // 1. Local IndexedDB backup
      try {
        const d = await withTimeout(db(), 1000);
        if (d) { const tx = d.transaction('kv', 'readwrite'); tx.objectStore('kv').put(S, DBKEY); }
      } catch(e) {}
      
      // 2. Background REST auto-save to Flask backend
      const resp = await fetch('/api/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({state: S})
      });
      if (resp.ok) {
        const data = await resp.json();
        autoOK = true;
        markSaved(data.savedAt);
      } else {
        autoOK = false;
      }
    } catch (e) {
      console.warn('Network sync error:', e);
      autoOK = false;
    }
  }, 600);
}
const withTimeout = (p, ms) => Promise.race([p, new Promise(r => setTimeout(() => r(null), ms))]);
async function load() {
  try {
    const res = await withTimeout(fetch('/api/state'), 3000);
    if (res && res.ok) {
      const data = await res.json();
      if (data.state && Object.keys(data.state).length) {
        console.log('Successfully fetched state from central server');
        return data.state;
      }
    }
  } catch (e) {
    console.warn('Could not fetch state from central server, falling back to local DB:', e);
  }
  return withTimeout(load0(), 2000);
}"""

if save_old in code:
    code = code.replace(save_old, save_new)
    print("Replaced save & load successfully.")
else:
    print("WARNING: Exact match for save_old not found, doing regex replacement...")
    # fallback regex replacement
    pat = r'function markDirty\(v\) \{[\s\S]*?async function load\(\) \{[\s\S]*?return withTimeout\(load0\(\), 2000\);[\s\S]*?\}'
    code = re.sub(pat, save_new, code, count=1)
    print("Regex replaced save & load.")

# 2. Update headerHTML
header_old = """function headerHTML() {
  if (MASTER) return `<h1>FTO Audit – MASTER Dashboard<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Cmd+S">💾 Save progress</button><button class="btn" data-act="merge">⤵ Import auditor files</button><button class="btn" data-act="docx">⬇ Word report</button><button class="btn hl" data-act="print">🖨 Print / PDF</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;
  return `<h1>FTO Audit – Auditor: ${esc(meName())}<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Cmd+S">💾 Save progress</button><button class="btn" data-act="aexp">⬆ Send to lead auditor (export)</button><button class="btn" data-act="aopen">📂 Load saved work</button><button class="btn" data-act="print">🖨 Print my sections</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;
}"""

header_new = """function headerHTML() {
  const currentRole = MASTER ? 'master' : (CFG.instanceId === 'A1' ? 'auditor1' : 'auditor2');
  const roleBadge = MASTER 
    ? '<span class="role-badge master">👑 MASTER AUDITOR</span>' 
    : `<span class="role-badge auditor">📋 ${esc(meName() || (CFG.instanceId === 'A1' ? 'Auditor 1' : 'Auditor 2'))}</span>`;

  const roleSwitcher = `
    <div class="role-switcher">
      <span class="rs-label">Role:</span>
      <select onchange="window.location.href=this.value" class="rs-select">
        <option value="/master" ${currentRole==='master'?'selected':''}>👑 Master Auditor</option>
        <option value="/auditor1" ${currentRole==='auditor1'?'selected':''}>📋 Auditor 1 (ORG, FO, SMS, FDM, ATS)</option>
        <option value="/auditor2" ${currentRole==='auditor2'?'selected':''}>📋 Auditor 2 (TRG, QA, ACC, NB)</option>
      </select>
    </div>
  `;

  if (MASTER) return `
    <div class="hdr-left">
      <h1>FTO Audit – MASTER Dashboard <small id="hdrOrg"></small></h1>
      ${roleBadge}
      ${roleSwitcher}
    </div>
    <span class="save-ind" id="saveInd"></span>
    <div class="tb">
      <button class="btn hl save-btn" data-act="fsave" title="Save to OneDrive">💾 Save Now</button>
      <button class="btn excel-btn" data-act="excel" title="Download Excel with embedded links">📊 Download Excel (.xlsx)</button>
      <button class="btn" data-act="docx" title="Generate Word (.docx)">⬇ Word Report</button>
      <button class="btn hl" data-act="print" title="Print or Save as PDF">🖨 Print / PDF</button>
      <button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry">🗑 Reset</button>
    </div>`;

  return `
    <div class="hdr-left">
      <h1>FTO Audit – ${esc(meName() || (CFG.instanceId === 'A1' ? 'Auditor 1' : 'Auditor 2'))} <small id="hdrOrg"></small></h1>
      ${roleBadge}
      ${roleSwitcher}
    </div>
    <span class="save-ind" id="saveInd"></span>
    <div class="tb">
      <button class="btn hl save-btn" data-act="fsave" title="Save to OneDrive">💾 Save Now</button>
      <button class="btn excel-btn" data-act="excel" title="Download Excel">📊 Excel (.xlsx)</button>
      <button class="btn" data-act="print">🖨 Print My Sections</button>
      <button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset">🗑 Reset</button>
    </div>`;
}"""

if header_old in code:
    code = code.replace(header_old, header_new)
    print("Replaced headerHTML successfully.")
else:
    print("WARNING: Exact match for header_old not found, doing regex replacement...")
    pat = r'function headerHTML\(\) \{[\s\S]*?return `<h1>FTO Audit – Auditor[\s\S]*?<\/div>`;\n\}'
    code = re.sub(pat, header_new, code, count=1)
    print("Regex replaced headerHTML.")

# 3. Add excel action to doAct
doact_old = "if (a === 'fsave') saveProgress();"
doact_new = """if (a === 'fsave') saveProgress();
  if (a === 'excel') window.open('/api/export-excel', '_blank');"""
code = code.replace(doact_old, doact_new)

# 4. Save to static/app_logic.js
with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "w", encoding="utf-8") as f:
    f.write(code)

print("static/app_logic.js written successfully! Size:", len(code))

