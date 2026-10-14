import sys

with open(r'static\app_logic.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update teamRightsTable
old_table = '''            const directUrl = r.role === 'Lead Auditor' ? `${host}/master` : (i === 1 ? `${host}/auditor1` : `${host}/auditor2`);
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
              </td>'''

new_table = '''            const directUrl = r.role === 'Lead Auditor' ? `${host}/master` : `${host}/auditor${i}`;
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
                    const isAssigned = (r.name && (S.secs[s.id].auditor || '').trim().toLowerCase() === r.name.trim().toLowerCase());
                    return `<button type="button" class="btn sm ${isAssigned ? 'pri' : ''}" style="padding:2px 6px;font-size:11px" data-toggle-sec="${i}|${s.id}" title="${esc(s.title)}">${s.id} ${isAssigned ? '✓' : ''}</button>`;
                  }).join('')}
                </div>
              </td>'''

if old_table in text:
    text = text.replace(old_table, new_table)
    print('Updated teamRightsTable.')
else:
    print('Warning: old_table not matched exactly.')

# 2. Update toggleSec handler
old_toggle = '''      const [person, sid] = d.toggleSec.split('|');
      const current = (S.secs[sid].auditor || '').trim().toLowerCase();
      if (current === person.trim().toLowerCase()) {
        S.secs[sid].auditor = '';
      } else {
        S.secs[sid].auditor = person;
      }
      save(); render(); toast(`${sid} assigned to ${S.secs[sid].auditor || 'unassigned'}`);'''

new_toggle = '''      const parts = d.toggleSec.split('|');
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
      }'''

if old_toggle in text:
    text = text.replace(old_toggle, new_toggle)
    print('Updated toggleSec handler.')
else:
    print('Warning: old_toggle not matched exactly.')

# 3. Update normalise()
old_norm = '''  if (!MASTER) { st.me = Object.assign({name: '', role: 'Auditor', label: 'Auditor', sections: []}, clone(CFG.me || {}), st.me || {}); applyMe(st); }'''
new_norm = '''  if (!MASTER) {
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
  }'''

if old_norm in text:
    text = text.replace(old_norm, new_norm)
    print('Updated normalise().')
else:
    print('Warning: old_norm not matched exactly.')

with open(r'static\app_logic.js', 'w', encoding='utf-8') as f:
    f.write(text)
print('Saved static/app_logic.js successfully.')
