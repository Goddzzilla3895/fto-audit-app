import re

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update contributions() so it only shows configured team members
old_contrib = """function contributions() {
  const by = {};
  const add = n => by[n] || (by[n] = {name: n, secs: new Set(), items: 0, f: 0, files: 0, imp: null});
  SECTIONS.forEach(s => { const a = S.secs[s.id].auditor; if (a && S.secs[s.id].on) add(a).secs.add(s.id); });
  Object.entries(S.inputs || {}).forEach(([id, o]) => Object.entries(o).forEach(([who, r]) => { const c = add(who); c.items++; const x = itemDef(id); if (x && isFinding(x.sec, r)) c.f++; c.files += (r.att || []).length; if (Object.keys(o).length > 1) c.shared = (c.shared || 0) + 1; }));
  SECTIONS.forEach(s => { const a = S.secs[s.id].auditor2; if (a && S.secs[s.id].on) add(a).secs.add(s.id); });
  S.imports.forEach(i => { const c = add(i.auditor); c.imp = i; (i.sections || []).forEach(s => c.secs.add(s)); });
  return Object.values(by);
}"""

new_contrib = """function contributions() {
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
}"""

if old_contrib in code:
    code = code.replace(old_contrib, new_contrib)
    print("Replaced contributions() to strictly match configured team members.")
else:
    print("WARNING: Exact match for old_contrib not found.")

# 2. Add teamRightsTable helper function
team_table_code = """
function teamRightsTable() {
  const rows = S.lists.team || [];
  const host = window.location.origin;
  return `
    <div class="tw">
      <table class="t">
        <thead>
          <tr>
            <th style="width:170px">Auditor Name</th>
            <th style="width:190px">Email ID</th>
            <th style="width:130px">Role</th>
            <th>Assigned Section Rights (Click to Toggle)</th>
            <th style="width:110px">Access Link</th>
            <th style="width:35px"></th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r, i) => {
            const directUrl = r.role === 'Lead Auditor' ? `${host}/master` : (i === 1 ? `${host}/auditor1` : `${host}/auditor2`);
            return `<tr>
              <td><input type="text" data-b="lists.team.${i}.name" value="${esc(r.name)}" placeholder="Full Name"></td>
              <td><input type="text" data-b="lists.team.${i}.email" value="${esc(r.email || '')}" placeholder="auditor@marigoldaviation.com"></td>
              <td>
                <select data-b="lists.team.${i}.role">
                  <option value="Lead Auditor" ${r.role==='Lead Auditor'?'selected':''}>Lead Auditor</option>
                  <option value="Auditor" ${r.role==='Auditor'?'selected':''}>Auditor</option>
                  <option value="Auditor 1" ${r.role==='Auditor 1'?'selected':''}>Auditor 1</option>
                  <option value="Auditor 2" ${r.role==='Auditor 2'?'selected':''}>Auditor 2</option>
                </select>
              </td>
              <td>
                <div style="display:flex;flex-wrap:wrap;gap:4px">
                  ${SECTIONS.map(s => {
                    const isAssigned = (S.secs[s.id].auditor || '').trim().toLowerCase() === (r.name || '').trim().toLowerCase();
                    return `<button type="button" class="btn sm ${isAssigned ? 'pri' : ''}" style="padding:2px 6px;font-size:11px" data-toggle-sec="${r.name}|${s.id}" title="${esc(s.title)}">${s.id} ${isAssigned ? '✓' : ''}</button>`;
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
"""

if "function teamRightsTable()" not in code:
    code = team_table_code + "\n" + code
    print("Added teamRightsTable helper function.")

# 3. Update vInfo() for read-only auditor view and enhanced master team management
old_vinfo_pat = r'function vInfo\(\)\s*\{[\s\S]*?function vExec\(\)'

new_vinfo = """function vInfo() {
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
function vExec()"""

code = re.sub(old_vinfo_pat, new_vinfo, code, count=1)
print("Updated vInfo() for read-only auditor view and team rights table.")

# 4. Add data-toggle-sec click listener
old_click_listener = "const t = e.target.closest('[data-go],[data-res],[data-act],[data-mk],[data-use],[data-rev],[data-arm],[data-zoom],[data-dl],[data-ladd],[data-lrm],[data-raise],[data-cadd],[data-cdel],[data-draft]'"
new_click_listener = "const t = e.target.closest('[data-go],[data-res],[data-act],[data-mk],[data-use],[data-rev],[data-arm],[data-zoom],[data-dl],[data-ladd],[data-lrm],[data-raise],[data-cadd],[data-cdel],[data-draft],[data-toggle-sec]'"

code = code.replace(old_click_listener, new_click_listener)

toggle_handler = """    if (d.toggleSec) {
      const [person, sid] = d.toggleSec.split('|');
      const current = (S.secs[sid].auditor || '').trim().toLowerCase();
      if (current === person.trim().toLowerCase()) {
        S.secs[sid].auditor = '';
      } else {
        S.secs[sid].auditor = person;
      }
      save(); render(); toast(`${sid} assigned to ${S.secs[sid].auditor || 'unassigned'}`);
    } else """

code = code.replace("if (d.go) { e.preventDefault(); go(d.go); }", toggle_handler + "if (d.go) { e.preventDefault(); go(d.go); }")
print("Added toggleSec click handler.")

with open(r"C:\Users\sunny\.gemini\antigravity\scratch\fto_audit_app\static\app_logic.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Saved updated app_logic.js.")
