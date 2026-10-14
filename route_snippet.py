@app.route("/auditor/<auditor_id>")
@app.route("/auditor")
def dynamic_auditor_view(auditor_id=None):
    name = request.args.get("name") or auditor_id or "Auditor"
    # Check current state to find which sections are assigned to this person!
    state = get_current_state()
    secs = state.get("secs", {})
    assigned_sections = []
    for sid, sdata in secs.items():
        if sdata.get("auditor", "").strip().lower() == name.strip().lower():
            assigned_sections.append(sid)
            
    # Default fallbacks if not configured in state yet:
    if not assigned_sections:
        param_secs = request.args.get("sections")
        if param_secs:
            assigned_sections = [s.strip().upper() for s in param_secs.split(",") if s.strip()]
        elif "1" in name:
            assigned_sections = ["ORG", "FO", "SMS", "FDM", "ATS"]
        elif "2" in name:
            assigned_sections = ["TRG", "QA", "ACC", "NB"]
        else:
            assigned_sections = ["ORG", "FO"]
            
    cfg = {
        "mode": "auditor",
        "instanceId": "aud_" + name.replace(" ", "_"),
        "locked": True,
        "me": {
            "name": name,
            "role": "Auditor",
            "label": name,
            "sections": assigned_sections
        }
    }
    return render_template("index.html", mode="auditor", role_label=name, cfg=json.dumps(cfg), pdfw_content=PDFW_CONTENT)
