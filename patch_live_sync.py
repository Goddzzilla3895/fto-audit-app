import re

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update headerHTML to remove the redundant "Send to lead auditor" button
old_auditor_header = """  return `<h1>FTO Audit – Auditor: ${esc(meName())}<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Save to OneDrive">💾 Save progress</button><button class="btn" data-act="excel" title="Download Excel with embedded links">📊 Excel report</button><button class="btn" data-act="aexp">⬆ Send to lead auditor (export)</button><button class="btn" data-act="aopen">📂 Load saved work</button><button class="btn" data-act="print">🖨 Print my sections</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;"""

new_auditor_header = """  return `<h1>FTO Audit – Auditor: ${esc(meName())}<small id="hdrOrg"></small></h1><span class="save-ind" id="saveInd"></span>
  <div class="tb"><button class="btn hl" data-act="fsave" title="Save to OneDrive">💾 Save progress</button><button class="btn" data-act="excel" title="Download Excel with embedded links">📊 Excel report</button><button class="btn" data-act="aopen">📂 Load saved work</button><button class="btn" data-act="print">🖨 Print my sections</button><button class="btn" style="background:#b42318;border-color:#b42318;color:#fff" data-act="reset" title="Erase every entry in this file">🗑 Clear / reset all</button></div>`;"""

if old_auditor_header in code:
    code = code.replace(old_auditor_header, new_auditor_header)
    print("Removed redundant Send button from headerHTML.")
else:
    print("Warning: old_auditor_header exact match not found.")

# 2. Add Live Background Reflection Loop
poll_code = """
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
"""

if "LIVE BACKGROUND AUTO-REFLECTION LOOP" not in code:
    code += "\n" + poll_code
    print("Added live reflection polling loop.")

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Saved updated app_logic.js.")
