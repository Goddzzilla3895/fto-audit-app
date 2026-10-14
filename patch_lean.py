import re

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "r", encoding="utf-8") as f:
    code = f.read()

# Update markDirty and markSaved
old_mark = """function markDirty(v) {
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
}"""

new_mark = """function markDirty(v) {
  dirty = v;
  const pill = $('#saveStatusPill'); const txt = $('#saveStatusText');
  if (pill && txt) {
    pill.className = 'status-pill status-saving';
    txt.textContent = 'Saving to OneDrive...';
  }
}
function markSaved(iso) {
  dirty = false;
  const pill = $('#saveStatusPill'); const txt = $('#saveStatusText');
  if (pill && txt) {
    pill.className = 'status-pill status-saved';
    const timeStr = iso ? new Date(iso).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : 'just now';
    txt.textContent = 'Auto-saved ' + timeStr;
  }
}"""

if old_mark in code:
    code = code.replace(old_mark, new_mark)
    print("Replaced markDirty & markSaved.")

# Update headerHTML
old_header_pat = r'function headerHTML\(\)\s*\{[\s\S]*?\}\nfunction refreshNav'
new_header = """function headerHTML() {
  const isMaster = MASTER;
  const auditorName = esc(meName() || (CFG.instanceId === 'A1' ? 'Auditor 1' : (CFG.instanceId === 'A2' ? 'Auditor 2' : 'Field Auditor')));
  const roleBadge = isMaster 
    ? '<span class="brand-badge badge-master">👑 Lead Auditor</span>' 
    : `<span class="brand-badge badge-auditor">📋 ${auditorName}</span>`;

  return `
    <div class="top-nav-bar">
      <div class="top-brand">
        <span class="brand-title">MARIGOLD AVIATION</span>
        ${roleBadge}
        ${isMaster ? '<a href="/" class="brand-switch-link" title="Auditor Selection Portal">Portal ↗</a>' : ''}
      </div>

      <div class="top-center-status">
        <span id="saveStatusPill" class="status-pill status-saved">
          <span class="dot"></span>
          <span id="saveStatusText">Auto-saved</span>
        </span>
      </div>

      <div class="top-actions">
        <button class="action-btn btn-save" data-act="fsave" title="Save changes now">
          💾 Save
        </button>

        <div class="dropdown-wrap">
          <button class="action-btn btn-export" id="exportMenuBtn" onclick="const m=document.getElementById('exportMenu'); m.classList.toggle('show'); event.stopPropagation();">
            📥 Export ▾
          </button>
          <div class="dropdown-menu" id="exportMenu">
            <a href="/api/export-excel" target="_blank" class="dropdown-item">📊 Excel Report (.xlsx)</a>
            ${isMaster ? '<a href="#" data-act="docx" class="dropdown-item">⬇ Word Report (.docx)</a>' : ''}
            <a href="#" data-act="print" class="dropdown-item">🖨 Print / PDF</a>
          </div>
        </div>

        ${isMaster ? '<button class="action-btn btn-more" data-act="reset" title="Clear/Reset Audit">🗑</button>' : ''}
      </div>
    </div>
  `;
}
function refreshNav"""

code = re.sub(old_header_pat, new_header, code, count=1)
print("Replaced headerHTML with lean UI.")

# Add click-outside listener to close export menu
close_menu_listener = """
document.addEventListener('click', () => {
  const m = document.getElementById('exportMenu');
  if (m) m.classList.remove('show');
});
"""
if "exportMenu" not in code or "close_menu_listener" not in code:
    code += "\n" + close_menu_listener

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated app_logic.js successfully.")

