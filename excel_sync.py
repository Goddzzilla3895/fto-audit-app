import os
import re
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

def slugify(text):
    return re.sub(r'[^A-Za-z0-9]+', '_', str(text or 'FTO')).strip('_')[:50]

def clean_val(v):
    if v is None:
        return ""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()

SECTION_CATALOG = [
    ("ORG", "Organisation, Accountability & Manpower"),
    ("FO", "Flight Operations & Training Area Procedures"),
    ("SMS", "Safety Management System (SMS)"),
    ("FDM", "Flight Data Monitoring / Flight Tracking"),
    ("ATS", "Air Traffic Services & Aerodrome Operations"),
    ("TRG", "Ground & Flight Training Delivery"),
    ("QA", "Quality Assurance & Compliance Monitoring"),
    ("ENG", "Aircraft Maintenance & Continuing Airworthiness"),
    ("CAM", "Continuing Airworthiness Management (CAMO)"),
    ("FLT", "Aircraft Fleet & Fuel Management"),
    ("INF", "Facilities, Runways, Hangars & Infrastructure"),
    ("ACC", "Cadet Welfare, Accommodation & Catering"),
    ("NB", "New Base Readiness & Infrastructure (Bhilwara Base)")
]

def generate_audit_excel(state_data, output_path, evidence_dir):
    """
    Generates an executive-ready, professional multi-tab Excel report.
    Creates:
      1. Executive Overview (KPIs, Governance, Aerodromes, Team with Section Rights,
         Audit Scope Section Governance, Cadre, Personnel, Fleet, Summary & Conclusion)
      2. Consolidated Findings & CAP (All actionable items with DataValidation dropdowns)
      3. Dedicated Checklist Tab for each Audited Aerodrome / Base
      4. Evidence Index (Hyperlinks to photos and files in OneDrive)
    """
    wb = openpyxl.Workbook()
    
    # ----------------------------------------------------
    # Styles & Formatting Palette
    # ----------------------------------------------------
    navy_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    steel_fill = PatternFill(start_color="2F3B4C", end_color="2F3B4C", fill_type="solid")
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    kpi_box_fill = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
    
    comp_fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
    minor_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    major_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
    obs_fill = PatternFill(start_color="E2E3E5", end_color="E2E3E5", fill_type="solid")
    
    white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    white_title = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=16, bold=True, color="1F4E79")
    h2_font = Font(name="Calibri", size=12, bold=True, color="1F4E79")
    kpi_val_font = Font(name="Calibri", size=18, bold=True, color="1F4E79")
    kpi_lbl_font = Font(name="Calibri", size=9, bold=True, color="555555")
    bold_font = Font(name="Calibri", size=10, bold=True)
    norm_font = Font(name="Calibri", size=10)
    small_font = Font(name="Calibri", size=9, color="555555")
    link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    # Pre-index files
    files = state_data.get("files", {})
    files_by_ref = {}
    for fid, finfo in files.items():
        ref = finfo.get("ref", "")
        if ref:
            files_by_ref.setdefault(ref, []).append((fid, finfo))

    items = state_data.get("items", {})
    meta = state_data.get("meta", {})
    lists = state_data.get("lists", {})
    text = state_data.get("text", {})
    secs = state_data.get("secs", {})

    # Compute KPI statistics
    total_items = len(items)
    compliant = sum(1 for v in items.values() if v.get("r") in ("C", "R"))
    partial = sum(1 for v in items.values() if v.get("r") in ("P", "PR"))
    non_compliant = sum(1 for v in items.values() if v.get("r") in ("NC", "NR"))
    not_eval = sum(1 for v in items.values() if v.get("r") in ("NE", "UC"))
    findings = [v for v in items.values() if v.get("cls")]
    major_f = sum(1 for v in findings if v.get("cls") == "MA")
    minor_f = sum(1 for v in findings if v.get("cls") == "MI")
    obs_f = sum(1 for v in findings if v.get("cls") == "OB")
    high_risk = sum(1 for v in findings if v.get("risk") == "H")
    comp_pct = f"{round((compliant / total_items * 100), 1)}%" if total_items > 0 else "0.0%"

    team_members = lists.get("team", [])
    team_names = [m.get("name", "").strip() for m in team_members if m.get("name", "").strip()]
    team_names_str = f'"{",".join(team_names)}"' if team_names else '""'

    loc_list = lists.get("locations", [])
    if not loc_list:
        loc_list = [{"name": "Main Base", "state": "All Facilities", "status": "Audited"}]

    # ----------------------------------------------------
    # Sheet 1: Executive Overview & Governance
    # ----------------------------------------------------
    ws_meta = wb.active
    ws_meta.title = "Executive Overview"
    ws_meta.views.sheetView[0].showGridLines = True
    
    # Banner
    ws_meta.merge_cells("A1:G1")
    ws_meta.cell(row=1, column=1, value="FTO DUE DILIGENCE AUDIT — CONSOLIDATED EXECUTIVE REPORT").font = white_title
    ws_meta.cell(row=1, column=1).fill = navy_fill
    ws_meta.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws_meta.row_dimensions[1].height = 36

    # Scorecard KPIs
    kpi_boxes = [
        ("TOTAL ASSESSED", str(total_items), "A"),
        ("COMPLIANCE RATE", comp_pct, "B"),
        ("COMPLIANT (C)", str(compliant), "C"),
        ("NON-COMPLIANT (NC)", str(non_compliant), "D"),
        ("TOTAL FINDINGS", str(len(findings)), "E"),
        ("MAJOR NON-CONF (MA)", str(major_f), "F"),
        ("HIGH RISK ITEMS", str(high_risk), "G")
    ]
    for lbl, val, col in kpi_boxes:
        c_lbl = ws_meta[f"{col}3"]
        c_lbl.value = lbl
        c_lbl.font = kpi_lbl_font
        c_lbl.fill = kpi_box_fill
        c_lbl.alignment = Alignment(horizontal="center", vertical="center")
        c_lbl.border = thin_border
        
        c_val = ws_meta[f"{col}4"]
        c_val.value = val
        c_val.font = kpi_val_font
        c_val.fill = kpi_box_fill
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.border = thin_border
    ws_meta.row_dimensions[3].height = 18
    ws_meta.row_dimensions[4].height = 28

    # 1. Audit Governance & Regulatory Metadata
    r = 6
    ws_meta.cell(row=r, column=1, value="1. Audit Governance & Regulatory Framework").font = h2_font
    gov_info = [
        ("Audited Organisation (FTO)", meta.get("auditedOrg", "")),
        ("Auditing Organisation", meta.get("auditingOrg", "Marigold Aviation")),
        ("FTO Approval / Reference No.", meta.get("approvalNo", "")),
        ("Audit Dates / Period", f"{clean_val(meta.get('from', ''))} to {clean_val(meta.get('to', ''))}"),
        ("Regulatory Framework", meta.get("framework", "DGCA India FTO requirements, CARs & International Best Practice")),
        ("Audit Type", meta.get("type", "Comprehensive Due Diligence Audit")),
        ("Report Status", meta.get("status", "Draft")),
        ("Classification", meta.get("classification", "Confidential – Commercial in Confidence")),
        ("Distribution", meta.get("distribution", ""))
    ]
    r += 1
    for k, v in gov_info:
        ws_meta.cell(row=r, column=1, value=k).font = bold_font
        ws_meta.cell(row=r, column=2, value=v).font = norm_font
        ws_meta.cell(row=r, column=1).border = thin_border
        ws_meta.cell(row=r, column=2).border = thin_border
        r += 1

    # 2. Audited Destinations & Operating Aerodromes
    r += 1
    ws_meta.cell(row=r, column=1, value="2. Audited Operating Aerodromes & Bases").font = h2_font
    r += 1
    ws_meta.cell(row=r, column=1, value="Base / Aerodrome").fill = header_fill
    ws_meta.cell(row=r, column=2, value="State / Region").fill = header_fill
    ws_meta.cell(row=r, column=3, value="Audit Status").fill = header_fill
    ws_meta.cell(row=r, column=4, value="Assigned Site Auditor(s)").fill = header_fill
    for col in range(1, 5):
        ws_meta.cell(row=r, column=col).font = bold_font
        ws_meta.cell(row=r, column=col).border = thin_border
    
    for loc in loc_list:
        r += 1
        loc_name = loc.get("name", "")
        # Find auditors assigned to this location
        assigned_auds = [m.get("name", "") for m in team_members if m.get("base") == loc_name or m.get("role") == "Lead Auditor"]
        auds_label = ", ".join(filter(Boolean := bool, assigned_auds)) or "Lead Auditor / Team"
        
        ws_meta.cell(row=r, column=1, value=loc_name).font = norm_font
        ws_meta.cell(row=r, column=2, value=loc.get("state", loc.get("icao", ""))).font = norm_font
        ws_meta.cell(row=r, column=3, value=loc.get("status", "Audited")).font = norm_font
        ws_meta.cell(row=r, column=4, value=auds_label).font = norm_font
        for col in range(1, 5):
            ws_meta.cell(row=r, column=col).border = thin_border

    # 3. Audit Team, Roles, Email IDs & Section Rights
    r += 2
    ws_meta.cell(row=r, column=1, value="3. Audit Team, Email IDs & Section Rights").font = h2_font
    r += 1
    team_hdrs = ["Role", "Auditor Name", "Email ID", "Assigned Aerodrome(s) / Base(s)", "Assigned Section Rights"]
    for col_idx, th in enumerate(team_hdrs, 1):
        cell = ws_meta.cell(row=r, column=col_idx, value=th)
        cell.fill = header_fill
        cell.font = bold_font
        cell.border = thin_border
    
    team_start_r = r + 1
    for member in team_members:
        r += 1
        m_name = member.get("name", "").strip()
        m_role = member.get("role", "Auditor")
        m_email = member.get("email", "")
        m_base = member.get("base", "All Aerodromes")
        
        # Calculate active assigned sections for this member
        assigned_secs = [sid for sid, sdata in secs.items() if sdata.get("on") and (sdata.get("auditor", "").strip().lower() == m_name.lower())]
        if m_role == "Lead Auditor":
            sec_rights_str = "All Sections (Lead Oversight & Sign-Off)"
        elif assigned_secs:
            sec_rights_str = ", ".join(assigned_secs)
        else:
            sec_rights_str = "— (No sections assigned yet)"

        ws_meta.cell(row=r, column=1, value=m_role).font = norm_font
        ws_meta.cell(row=r, column=2, value=m_name).font = norm_font
        ws_meta.cell(row=r, column=3, value=m_email).font = norm_font
        ws_meta.cell(row=r, column=4, value=m_base).font = norm_font
        ws_meta.cell(row=r, column=5, value=sec_rights_str).font = norm_font
        for col in range(1, 6):
            ws_meta.cell(row=r, column=col).border = thin_border
    team_end_r = r
    if team_end_r >= team_start_r:
        dv_role = DataValidation(type="list", formula1='"Lead Auditor,Auditor"', allow_blank=True)
        ws_meta.add_data_validation(dv_role)
        dv_role.add(f"A{team_start_r}:A{team_end_r}")

    # 4. Audit Scope & Section Allocation Governance Table
    r += 2
    ws_meta.cell(row=r, column=1, value="4. Audit Scope & Functional Section Governance Table").font = h2_font
    r += 1
    sec_hdrs = ["Section Code", "Functional Section Title", "Scope Status", "Primary Assigned Auditor", "Second Auditor (Optional)", "Applicable Aerodromes"]
    for col_idx, sh in enumerate(sec_hdrs, 1):
        cell = ws_meta.cell(row=r, column=col_idx, value=sh)
        cell.fill = header_fill
        cell.font = bold_font
        cell.border = thin_border

    sec_start_r = r + 1
    for sid, stitle in SECTION_CATALOG:
        r += 1
        sdata = secs.get(sid, {})
        is_on = sdata.get("on", True)
        primary_aud = sdata.get("auditor", "")
        second_aud = sdata.get("auditor2", "")
        
        ws_meta.cell(row=r, column=1, value=sid).font = bold_font
        ws_meta.cell(row=r, column=2, value=stitle).font = norm_font
        ws_meta.cell(row=r, column=3, value="In Scope" if is_on else "Out of Scope").font = norm_font
        ws_meta.cell(row=r, column=4, value=primary_aud or "— Unassigned —").font = norm_font
        ws_meta.cell(row=r, column=5, value=second_aud or "— None —").font = norm_font
        ws_meta.cell(row=r, column=6, value="All Audited Aerodromes").font = norm_font
        for col in range(1, 7):
            ws_meta.cell(row=r, column=col).border = thin_border
    sec_end_r = r

    # Dropdowns for Section Governance Table
    dv_scope = DataValidation(type="list", formula1='"In Scope,Out of Scope"', allow_blank=True)
    ws_meta.add_data_validation(dv_scope)
    dv_scope.add(f"C{sec_start_r}:C{sec_end_r}")

    if team_names_str:
        dv_sec_aud = DataValidation(type="list", formula1=team_names_str, allow_blank=True)
        ws_meta.add_data_validation(dv_sec_aud)
        dv_sec_aud.add(f"D{sec_start_r}:D{sec_end_r}")
        dv_sec_aud.add(f"E{sec_start_r}:E{sec_end_r}")

    # 5. Personnel Engaged During Audit
    r += 2
    ws_meta.cell(row=r, column=1, value="5. Auditee Personnel Engaged During Audit").font = h2_font
    r += 1
    ws_meta.cell(row=r, column=1, value="Name").fill = header_fill
    ws_meta.cell(row=r, column=2, value="Designation / Department").fill = header_fill
    ws_meta.cell(row=r, column=1).font = bold_font
    ws_meta.cell(row=r, column=2).font = bold_font
    ws_meta.cell(row=r, column=1).border = thin_border
    ws_meta.cell(row=r, column=2).border = thin_border
    personnel_list = lists.get("personnel", [])
    if personnel_list:
        for p in personnel_list:
            r += 1
            ws_meta.cell(row=r, column=1, value=p.get("name", "")).font = norm_font
            ws_meta.cell(row=r, column=2, value=p.get("designation", "")).font = norm_font
            ws_meta.cell(row=r, column=1).border = thin_border
            ws_meta.cell(row=r, column=2).border = thin_border
    else:
        r += 1
        ws_meta.cell(row=r, column=1, value="—").font = small_font
        ws_meta.cell(row=r, column=2, value="No personnel records entered yet").font = small_font
        ws_meta.cell(row=r, column=1).border = thin_border
        ws_meta.cell(row=r, column=2).border = thin_border

    # 6. Instructional Cadre (CFI, Instructors)
    r += 2
    ws_meta.cell(row=r, column=1, value="6. Instructional Cadre & Key Post Holders").font = h2_font
    r += 1
    ws_meta.cell(row=r, column=1, value="Category / Post").fill = header_fill
    ws_meta.cell(row=r, column=2, value="Name / Approved Count").fill = header_fill
    ws_meta.cell(row=r, column=3, value="Approval / License / Remarks").fill = header_fill
    for col in range(1, 4):
        ws_meta.cell(row=r, column=col).font = bold_font
        ws_meta.cell(row=r, column=col).border = thin_border
    cadre_list = lists.get("cadre", [])
    if cadre_list:
        for c in cadre_list:
            r += 1
            ws_meta.cell(row=r, column=1, value=c.get("cat", "")).font = norm_font
            ws_meta.cell(row=r, column=2, value=str(c.get("count", c.get("name", "")))).font = norm_font
            ws_meta.cell(row=r, column=3, value=c.get("notes", "")).font = norm_font
            for col in range(1, 4):
                ws_meta.cell(row=r, column=col).border = thin_border
    else:
        r += 1
        ws_meta.cell(row=r, column=1, value="—").font = small_font
        ws_meta.cell(row=r, column=2, value="No cadre records entered yet").font = small_font
        ws_meta.cell(row=r, column=3, value="—").font = small_font
        for col in range(1, 4):
            ws_meta.cell(row=r, column=col).border = thin_border

    # 7. Aircraft Fleet Reconciliation
    r += 2
    ws_meta.cell(row=r, column=1, value="7. Aircraft Fleet Reconciliation").font = h2_font
    r += 1
    ws_meta.cell(row=r, column=1, value="Aircraft Registration").fill = header_fill
    ws_meta.cell(row=r, column=2, value="Type / Model").fill = header_fill
    ws_meta.cell(row=r, column=3, value="Source A Count").fill = header_fill
    ws_meta.cell(row=r, column=4, value="Source B Count").fill = header_fill
    for col in range(1, 5):
        ws_meta.cell(row=r, column=col).font = bold_font
        ws_meta.cell(row=r, column=col).border = thin_border
    fleet_list = lists.get("fleet", [])
    if fleet_list:
        for f in fleet_list:
            r += 1
            ws_meta.cell(row=r, column=1, value=f.get("reg", "")).font = norm_font
            ws_meta.cell(row=r, column=2, value=f.get("type", "")).font = norm_font
            ws_meta.cell(row=r, column=3, value=str(f.get("s1", ""))).font = norm_font
            ws_meta.cell(row=r, column=4, value=str(f.get("s2", ""))).font = norm_font
            for col in range(1, 5):
                ws_meta.cell(row=r, column=col).border = thin_border
    else:
        r += 1
        ws_meta.cell(row=r, column=1, value="—").font = small_font
        ws_meta.cell(row=r, column=2, value="No fleet entries entered yet").font = small_font
        ws_meta.cell(row=r, column=3, value="—").font = small_font
        ws_meta.cell(row=r, column=4, value="—").font = small_font
        for col in range(1, 5):
            ws_meta.cell(row=r, column=col).border = thin_border

    # 8. Executive Summary & Position
    r += 2
    ws_meta.cell(row=r, column=1, value="8. Executive Summary & Position").font = h2_font
    r += 1
    c_exec = ws_meta.cell(row=r, column=1, value=text.get("exec", "Executive summary not yet finalized."))
    c_exec.font = norm_font
    ws_meta.merge_cells(start_row=r, start_column=1, end_row=r+2, end_column=7)
    c_exec.alignment = Alignment(vertical="top", wrap_text=True)

    # 9. Lead Auditor Conclusion
    r += 4
    ws_meta.cell(row=r, column=1, value="9. Lead Auditor Overall Conclusion").font = h2_font
    r += 1
    c_conc = ws_meta.cell(row=r, column=1, value=text.get("conclusion", "Auditor conclusion not yet entered."))
    c_conc.font = norm_font
    ws_meta.merge_cells(start_row=r, start_column=1, end_row=r+2, end_column=7)
    c_conc.alignment = Alignment(vertical="top", wrap_text=True)

    ws_meta.column_dimensions['A'].width = 24
    ws_meta.column_dimensions['B'].width = 38
    ws_meta.column_dimensions['C'].width = 22
    ws_meta.column_dimensions['D'].width = 26
    ws_meta.column_dimensions['E'].width = 30
    ws_meta.column_dimensions['F'].width = 24
    ws_meta.column_dimensions['G'].width = 24

    # ----------------------------------------------------
    # Sheet 2: Consolidated Findings & CAP Plan
    # ----------------------------------------------------
    ws_cap = wb.create_sheet(title="Consolidated Findings & CAP")
    ws_cap.views.sheetView[0].showGridLines = True
    
    cap_headers = [
        "Finding Ref", "Section", "Severity Class", "Risk Rating",
        "Target Timeframe", "Auditor Observation & Non-Conformance Summary",
        "Agreed Corrective Action Plan", "Action Owner", "Agreed Target Due Date",
        "Implementation Status", "Evidence Hyperlink"
    ]
    for col_idx, h in enumerate(cap_headers, 1):
        cell = ws_cap.cell(row=1, column=col_idx, value=h)
        cell.fill = steel_fill
        cell.font = white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws_cap.row_dimensions[1].height = 28
    
    cap_r = 2
    for item_id, item_data in sorted(items.items()):
        if item_data.get("cls") or item_data.get("act"):
            sec_id = item_id.split("-")[0]
            cls_val = item_data.get("cls", "")
            
            ws_cap.cell(row=cap_r, column=1, value=item_id).alignment = Alignment(horizontal="center")
            ws_cap.cell(row=cap_r, column=2, value=sec_id).alignment = Alignment(horizontal="center")
            
            c_cls = ws_cap.cell(row=cap_r, column=3, value=cls_val)
            c_cls.alignment = Alignment(horizontal="center")
            if cls_val == "MA": c_cls.fill = major_fill
            elif cls_val == "MI": c_cls.fill = minor_fill
            elif cls_val == "OB": c_cls.fill = obs_fill

            ws_cap.cell(row=cap_r, column=4, value=item_data.get("risk", "")).alignment = Alignment(horizontal="center")
            ws_cap.cell(row=cap_r, column=5, value=item_data.get("tf", "")).alignment = Alignment(horizontal="center")
            ws_cap.cell(row=cap_r, column=6, value=item_data.get("comment", "") or item_data.get("find", ""))
            ws_cap.cell(row=cap_r, column=7, value=item_data.get("act", ""))
            ws_cap.cell(row=cap_r, column=8, value=item_data.get("owner", ""))
            ws_cap.cell(row=cap_r, column=9, value=clean_val(item_data.get("due", "")))
            ws_cap.cell(row=cap_r, column=10, value=item_data.get("st", "Open")).alignment = Alignment(horizontal="center")
            
            ref_key = f"item:{item_id}"
            ev_list = files_by_ref.get(ref_key, [])
            if ev_list:
                fid, finfo = ev_list[0]
                fname = finfo.get("saved_filename") or f"{fid}.jpg"
                rel_link = f"Evidence\\{fname}"
                cell_l = ws_cap.cell(row=cap_r, column=11)
                cell_l.value = f'=HYPERLINK("{rel_link}", "📷 Open Photo ({fname})")'
                cell_l.font = link_font
            else:
                ws_cap.cell(row=cap_r, column=11, value="—").font = small_font
                
            for c_idx in range(1, 12):
                ws_cap.cell(row=cap_r, column=c_idx).border = thin_border
                if c_idx in (6, 7):
                    ws_cap.cell(row=cap_r, column=c_idx).alignment = Alignment(vertical="center", wrap_text=True)
            cap_r += 1

    cap_widths = [13, 10, 15, 12, 16, 42, 42, 18, 15, 15, 30]
    for idx, w in enumerate(cap_widths, 1):
        ws_cap.column_dimensions[get_column_letter(idx)].width = w

    # Add Dropdowns to Consolidated Findings & CAP
    max_cap_row = max(cap_r - 1, 50)
    dv_cap_cls = DataValidation(type="list", formula1='"MA,MI,OB,IO"', allow_blank=True)
    ws_cap.add_data_validation(dv_cap_cls)
    dv_cap_cls.add(f"C2:C{max_cap_row}")

    dv_cap_risk = DataValidation(type="list", formula1='"H,M,L"', allow_blank=True)
    ws_cap.add_data_validation(dv_cap_risk)
    dv_cap_risk.add(f"D2:D{max_cap_row}")

    dv_cap_tf = DataValidation(type="list", formula1='"IMM,D30,D90"', allow_blank=True)
    ws_cap.add_data_validation(dv_cap_tf)
    dv_cap_tf.add(f"E2:E{max_cap_row}")

    dv_cap_st = DataValidation(type="list", formula1='"Open,In progress,Closed,Verified"', allow_blank=True)
    ws_cap.add_data_validation(dv_cap_st)
    dv_cap_st.add(f"J2:J{max_cap_row}")

    # ----------------------------------------------------
    # Dedicated Tab for EACH Audited Location / Base
    # ----------------------------------------------------
    chk_headers = [
        "Item ID", "Section", "Regulatory Requirement & Standards", "Compliance Result",
        "Severity", "Risk", "Timeframe", "Assessed By",
        "Auditor Observations & Evidence Notes", "Corrective Action", "Owner", "Target Date",
        "Evidence Photo Link"
    ]

    for loc_item in loc_list:
        loc_name = loc_item.get("name", "Base").strip()
        safe_tab_title = re.sub(r'[\:\\\/\?\*\[\]]', '', f"Checklist - {loc_name}")[:31].strip()
        
        ws_loc = wb.create_sheet(title=safe_tab_title)
        ws_loc.views.sheetView[0].showGridLines = True
        
        # Location Header Banner
        ws_loc.merge_cells("A1:M1")
        ws_loc.cell(row=1, column=1, value=f"CHECKLIST ASSESSMENTS — {loc_name.upper()} ({loc_item.get('status', 'Audited').upper()})").font = white_bold
        ws_loc.cell(row=1, column=1).fill = navy_fill
        ws_loc.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws_loc.row_dimensions[1].height = 28

        for col_idx, h in enumerate(chk_headers, 1):
            cell = ws_loc.cell(row=2, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = bold_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws_loc.row_dimensions[2].height = 26

        loc_r = 3
        for item_id, item_data in sorted(items.items()):
            sec_id = item_id.split("-")[0]
            res_val = item_data.get("r", "")
            cls_val = item_data.get("cls", "")
            
            ws_loc.cell(row=loc_r, column=1, value=item_id).alignment = Alignment(horizontal="center")
            ws_loc.cell(row=loc_r, column=2, value=sec_id).alignment = Alignment(horizontal="center")
            ws_loc.cell(row=loc_r, column=3, value=item_data.get("find", "") or f"Requirement {item_id}")
            
            c_res = ws_loc.cell(row=loc_r, column=4, value=res_val)
            c_res.alignment = Alignment(horizontal="center")
            if res_val in ("C", "R"): c_res.fill = comp_fill
            elif res_val in ("NC", "NR"): c_res.fill = major_fill
            elif res_val in ("P", "PR"): c_res.fill = minor_fill

            c_cls = ws_loc.cell(row=loc_r, column=5, value=cls_val)
            c_cls.alignment = Alignment(horizontal="center")
            if cls_val == "MA": c_cls.fill = major_fill
            elif cls_val == "MI": c_cls.fill = minor_fill
            elif cls_val == "OB": c_cls.fill = obs_fill

            ws_loc.cell(row=loc_r, column=6, value=item_data.get("risk", "")).alignment = Alignment(horizontal="center")
            ws_loc.cell(row=loc_r, column=7, value=item_data.get("tf", "")).alignment = Alignment(horizontal="center")
            ws_loc.cell(row=loc_r, column=8, value=item_data.get("by", "")).alignment = Alignment(horizontal="center")
            ws_loc.cell(row=loc_r, column=9, value=item_data.get("comment", ""))
            ws_loc.cell(row=loc_r, column=10, value=item_data.get("act", ""))
            ws_loc.cell(row=loc_r, column=11, value=item_data.get("owner", ""))
            ws_loc.cell(row=loc_r, column=12, value=clean_val(item_data.get("due", "")))
            
            ref_key = f"item:{item_id}"
            ev_list = files_by_ref.get(ref_key, [])
            if ev_list:
                fid, finfo = ev_list[0]
                fname = finfo.get("saved_filename") or f"{fid}.jpg"
                rel_link = f"Evidence\\{fname}"
                c_link = ws_loc.cell(row=loc_r, column=13)
                c_link.value = f'=HYPERLINK("{rel_link}", "📷 Open {finfo.get("name", fname)}")'
                c_link.font = link_font
            else:
                ws_loc.cell(row=loc_r, column=13, value="No attachment").font = small_font
                
            for c_idx in range(1, 14):
                ws_loc.cell(row=loc_r, column=c_idx).border = thin_border
                if c_idx in (3, 9, 10):
                    ws_loc.cell(row=loc_r, column=c_idx).alignment = Alignment(vertical="center", wrap_text=True)
            loc_r += 1

        loc_widths = [12, 10, 40, 14, 12, 10, 14, 18, 38, 38, 16, 14, 30]
        for idx, w in enumerate(loc_widths, 1):
            ws_loc.column_dimensions[get_column_letter(idx)].width = w

        # Dropdowns in Checklist Tab
        max_chk_row = max(loc_r - 1, 50)
        dv_chk_res = DataValidation(type="list", formula1='"C,P,NC,NE,NA"', allow_blank=True)
        ws_loc.add_data_validation(dv_chk_res)
        dv_chk_res.add(f"D3:D{max_chk_row}")

        dv_chk_cls = DataValidation(type="list", formula1='"MA,MI,OB,IO"', allow_blank=True)
        ws_loc.add_data_validation(dv_chk_cls)
        dv_chk_cls.add(f"E3:E{max_chk_row}")

        dv_chk_risk = DataValidation(type="list", formula1='"H,M,L"', allow_blank=True)
        ws_loc.add_data_validation(dv_chk_risk)
        dv_chk_risk.add(f"F3:F{max_chk_row}")

        dv_chk_tf = DataValidation(type="list", formula1='"IMM,D30,D90"', allow_blank=True)
        ws_loc.add_data_validation(dv_chk_tf)
        dv_chk_tf.add(f"G3:G{max_chk_row}")

        if team_names_str:
            dv_chk_by = DataValidation(type="list", formula1=team_names_str, allow_blank=True)
            ws_loc.add_data_validation(dv_chk_by)
            dv_chk_by.add(f"H3:H{max_chk_row}")

    # ----------------------------------------------------
    # Sheet 3: Evidence Index
    # ----------------------------------------------------
    ws_ev = wb.create_sheet(title="Evidence Index")
    ws_ev.views.sheetView[0].showGridLines = True
    ev_headers = ["Item / Reference", "Section", "File Name", "Caption / Description", "File Size", "Evidence Photo / Document Link"]
    for col_idx, h in enumerate(ev_headers, 1):
        cell = ws_ev.cell(row=1, column=col_idx, value=h)
        cell.fill = navy_fill
        cell.font = white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_ev.row_dimensions[1].height = 28

    ev_r = 2
    for fid, finfo in sorted(files.items(), key=lambda x: x[1].get("ref", "")):
        ref = finfo.get("ref", "General")
        sec_id = ref.replace("item:", "").replace("sec:", "").split("-")[0] if ":" in ref else "General"
        fname = finfo.get("saved_filename") or f"{fid}.jpg"
        size_kb = f"{round(finfo.get('size', 0)/1024, 1)} KB" if finfo.get('size') else "—"
        rel_link = f"Evidence\\{fname}"
        
        ws_ev.cell(row=ev_r, column=1, value=ref).alignment = Alignment(horizontal="center")
        ws_ev.cell(row=ev_r, column=2, value=sec_id).alignment = Alignment(horizontal="center")
        ws_ev.cell(row=ev_r, column=3, value=finfo.get("name", fname))
        ws_ev.cell(row=ev_r, column=4, value=finfo.get("cap", "Evidence Photo"))
        ws_ev.cell(row=ev_r, column=5, value=size_kb).alignment = Alignment(horizontal="center")
        
        c_link = ws_ev.cell(row=ev_r, column=6)
        c_link.value = f'=HYPERLINK("{rel_link}", "📷 Open File ({fname})")'
        c_link.font = link_font
        
        for col in range(1, 7):
            ws_ev.cell(row=ev_r, column=col).border = thin_border
        ev_r += 1

    ev_widths = [16, 12, 34, 34, 14, 30]
    for idx, w in enumerate(ev_widths, 1):
        ws_ev.column_dimensions[get_column_letter(idx)].width = w

    # ----------------------------------------------------
    # Output File Writing (Single File Only)
    # ----------------------------------------------------
    if hasattr(output_path, "write"):
        wb.save(output_path)
        return output_path
    elif output_path:
        try:
            wb.save(output_path)
            return output_path
        except PermissionError:
            print(f"[Notice] {output_path} is currently open in Microsoft Excel. Close the file in Excel to allow disk updates.")
            return None
    return wb

def import_audit_excel(excel_file_or_path, current_state):
    """
    Imports modifications from the Excel file back into current_state,
    ensuring full two-way roundtrip synchronization.
    Reads Checklist sheets, Consolidated Findings & CAP, and Executive Overview.
    """
    wb = openpyxl.load_workbook(excel_file_or_path, data_only=True)
    updated_items = 0
    items = current_state.setdefault("items", {})
    secs = current_state.setdefault("secs", {})

    # 1. Read all Checklist sheets
    chk_sheets = [s for s in wb.sheetnames if "checklist" in s.lower()]
    for sname in chk_sheets:
        ws = wb[sname]
        for row in ws.iter_rows(min_row=3, values_only=True):
            if not row or len(row) < 4:
                continue
            item_id = clean_val(row[0])
            if not item_id or "-" not in item_id:
                continue
            
            res_val = clean_val(row[3])
            cls_val = clean_val(row[4]) if len(row) > 4 else ""
            risk_val = clean_val(row[5]) if len(row) > 5 else ""
            tf_val = clean_val(row[6]) if len(row) > 6 else ""
            by_val = clean_val(row[7]) if len(row) > 7 else ""
            comment_val = clean_val(row[8]) if len(row) > 8 else ""
            act_val = clean_val(row[9]) if len(row) > 9 else ""
            owner_val = clean_val(row[10]) if len(row) > 10 else ""
            due_val = clean_val(row[11]) if len(row) > 11 else ""
            
            item = items.setdefault(item_id, {"att": []})
            if res_val: item["r"] = res_val
            if cls_val: item["cls"] = cls_val
            if risk_val: item["risk"] = risk_val
            if tf_val: item["tf"] = tf_val
            if by_val: item["by"] = by_val
            if comment_val: item["comment"] = comment_val
            if act_val: item["act"] = act_val
            if owner_val: item["owner"] = owner_val
            if due_val: item["due"] = due_val
            updated_items += 1

    # 2. Read Consolidated Findings & CAP sheet
    if "Consolidated Findings & CAP" in wb.sheetnames:
        ws_cap = wb["Consolidated Findings & CAP"]
        for row in ws_cap.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 3:
                continue
            item_id = clean_val(row[0])
            if not item_id or "-" not in item_id:
                continue
            
            cls_val = clean_val(row[2])
            risk_val = clean_val(row[3]) if len(row) > 3 else ""
            tf_val = clean_val(row[4]) if len(row) > 4 else ""
            comment_val = clean_val(row[5]) if len(row) > 5 else ""
            act_val = clean_val(row[6]) if len(row) > 6 else ""
            owner_val = clean_val(row[7]) if len(row) > 7 else ""
            due_val = clean_val(row[8]) if len(row) > 8 else ""
            st_val = clean_val(row[9]) if len(row) > 9 else ""

            item = items.setdefault(item_id, {"att": []})
            if cls_val: item["cls"] = cls_val
            if risk_val: item["risk"] = risk_val
            if tf_val: item["tf"] = tf_val
            if comment_val and not item.get("comment"): item["comment"] = comment_val
            if act_val: item["act"] = act_val
            if owner_val: item["owner"] = owner_val
            if due_val: item["due"] = due_val
            if st_val: item["st"] = st_val
            updated_items += 1

    # 3. Read Executive Overview
    overview_key = "Executive Overview" if "Executive Overview" in wb.sheetnames else ("Audit Overview" if "Audit Overview" in wb.sheetnames else None)
    if overview_key:
        ws_m = wb[overview_key]
        meta = current_state.setdefault("meta", {})
        lists = current_state.setdefault("lists", {})
        text = current_state.setdefault("text", {})
        
        mode = None
        for row in ws_m.iter_rows(min_row=6, values_only=True):
            if not row or not any(row):
                continue
            c0 = clean_val(row[0])
            c1 = clean_val(row[1]) if len(row) > 1 else ""
            c2 = clean_val(row[2]) if len(row) > 2 else ""
            c3 = clean_val(row[3]) if len(row) > 3 else ""
            c4 = clean_val(row[4]) if len(row) > 4 else ""

            if "1. Audit Governance" in c0:
                mode = "gov"; continue
            elif "2. Audited Operating" in c0:
                mode = "loc"; continue
            elif "3. Audit Team" in c0:
                mode = "team"; continue
            elif "4. Audit Scope & Functional" in c0:
                mode = "sec_gov"; continue
            elif "5. Auditee Personnel" in c0:
                mode = "personnel"; continue
            elif "6. Instructional Cadre" in c0:
                mode = "cadre"; continue
            elif "7. Aircraft Fleet" in c0:
                mode = "fleet"; continue
            elif "8. Executive Summary" in c0:
                mode = "exec"; continue
            elif "9. Lead Auditor Overall Conclusion" in c0:
                mode = "conc"; continue

            if mode == "gov":
                k_low = c0.lower()
                if "audited organisation" in k_low and c1: meta["auditedOrg"] = c1
                elif "auditing organisation" in k_low and c1: meta["auditingOrg"] = c1
                elif "approval" in k_low and c1: meta["approvalNo"] = c1
                elif "regulatory framework" in k_low and c1: meta["framework"] = c1
                elif "audit type" in k_low and c1: meta["type"] = c1
                elif "report status" in k_low and c1: meta["status"] = c1
                elif "classification" in k_low and c1: meta["classification"] = c1
                elif "distribution" in k_low and c1: meta["distribution"] = c1
            elif mode == "sec_gov" and c0 and c0 in [s[0] for s in SECTION_CATALOG]:
                # c0 = Section Code, c2 = Scope Status, c3 = Primary Assigned Auditor, c4 = Second Auditor
                sec_obj = secs.setdefault(c0, {})
                if c2 in ("In Scope", "Out of Scope"):
                    sec_obj["on"] = (c2 == "In Scope")
                if c3 and c3 != "— Unassigned —":
                    sec_obj["auditor"] = c3
                elif c3 == "— Unassigned —":
                    sec_obj["auditor"] = ""
                if c4 and c4 != "— None —":
                    sec_obj["auditor2"] = c4
                elif c4 == "— None —":
                    sec_obj["auditor2"] = ""
            elif mode == "team" and c1 and c1 != "Auditor Name":
                # c0 = Role, c1 = Name, c2 = Email, c3 = Assigned Aerodrome
                team = lists.setdefault("team", [])
                found_member = next((m for m in team if m.get("name", "").strip().lower() == c1.lower()), None)
                if found_member:
                    if c0 in ("Lead Auditor", "Auditor"): found_member["role"] = c0
                    if c2: found_member["email"] = c2
                    if c3: found_member["base"] = c3
                else:
                    team.append({"name": c1, "role": c0 if c0 in ("Lead Auditor", "Auditor") else "Auditor", "email": c2, "base": c3})
            elif mode == "exec" and c0 and not c0.startswith("8."):
                text["exec"] = c0
            elif mode == "conc" and c0 and not c0.startswith("9."):
                text["conclusion"] = c0

    return updated_items, current_state
