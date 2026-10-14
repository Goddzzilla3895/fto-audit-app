import re

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic_original.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update save and load for central auto-saving and auto-populating
# In the original file:
# function markDirty(v) ...
# function saveProgress() ...
# function save() ...
# async function load() ...

old_persistence = """function markDirty(v) {
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

new_persistence = """function markDirty(v) {
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
}"""

if old_persistence in code:
    code = code.replace(old_persistence, new_persistence)
    print("Replaced persistence successfully.")
else:
    print("WARNING: Exact match for old_persistence not found.")

# 2. In headerHTML, keep the exact original layout and button styling, just adding the Excel button cleanly:
old_header = """function headerHTML() {
  if (MASTER) return `<h1>FTO Audit – MASTER Dashboard<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Cmd+S">💾 Save progress</button><button class="btn" data-act="merge">⤵ Import auditor files</button><button class="btn" data-act="docx">⬇ Word report</button><button class="btn hl" data-act="print">🖨 Print / PDF</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;
  return `<h1>FTO Audit – Auditor: ${esc(meName())}<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Cmd+S">💾 Save progress</button><button class="btn" data-act="aexp">⬆ Send to lead auditor (export)</button><button class="btn" data-act="aopen">📂 Load saved work</button><button class="btn" data-act="print">🖨 Print my sections</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;
}"""

new_header = """function headerHTML() {
  if (MASTER) return `<h1>FTO Audit – MASTER Dashboard<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Save to OneDrive">💾 Save progress</button><button class="btn" data-act="excel" title="Download Excel with embedded links">📊 Excel report</button><button class="btn" data-act="merge">⤵ Import auditor files</button><button class="btn" data-act="docx">⬇ Word report</button><button class="btn hl" data-act="print">🖨 Print / PDF</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;
  return `<h1>FTO Audit – Auditor: ${esc(meName())}<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Save to OneDrive">💾 Save progress</button><button class="btn" data-act="excel" title="Download Excel with embedded links">📊 Excel report</button><button class="btn" data-act="aexp">⬆ Send to lead auditor (export)</button><button class="btn" data-act="aopen">📂 Load saved work</button><button class="btn" data-act="print">🖨 Print my sections</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;
}"""

if old_header in code:
    code = code.replace(old_header, new_header)
    print("Replaced headerHTML successfully.")
else:
    print("WARNING: Exact match for old_header not found.")

# 3. Add excel action in doAct
old_doact = "if (a === 'fsave') saveProgress();"
new_doact = """if (a === 'fsave') saveProgress();
  if (a === 'excel') window.open('/api/export-excel', '_blank');"""
if old_doact in code:
    code = code.replace(old_doact, new_doact)
    print("Added excel handler to doAct.")

# Write updated code
with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Saved pristine static/app_logic.js.")
