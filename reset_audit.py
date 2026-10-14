import os
import json
import sqlite3
import argparse
import datetime
from excel_sync import generate_audit_excel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ONEDRIVE_DIR = r"C:\Users\sunny\OneDrive - Marigold Aviation\Apps\Anitgravity\Audit Trail"
EVIDENCE_DIR = os.path.join(ONEDRIVE_DIR, "Evidence")
EXCEL_PATH = os.path.join(ONEDRIVE_DIR, "FTO_Audit_Consolidated.xlsx")
DB_PATH = os.path.join(BASE_DIR, "fto_audit.db")

def create_blank_audit(lead_name="SRINIVAS RAO", lead_email="srinivas.rao@marigoldaviation.com",
                       audited_org="NEW FTO NAME", approval_no="", base_name="Main Base"):
    """
    Resets the backend SQLite database to a clean, production-ready blank audit.
    Wipes all dummy findings, test evidence, and sample responses.
    """
    now = datetime.datetime.now().isoformat()
    today_str = datetime.date.today().isoformat()
    
    # Load initial template structure to get standard section definitions
    init_path = os.path.join(BASE_DIR, "initial_saved.json")
    if os.path.exists(init_path):
        with open(init_path, "r", encoding="utf-8") as f:
            template = json.load(f).get("state", {})
    else:
        template = {}

    clean_state = {
        "v": 2,
        "meta": {
            "auditingOrg": "Marigold Aviation",
            "auditedOrg": audited_org,
            "approvalNo": approval_no,
            "from": today_str,
            "to": today_str,
            "title": "Operational, Safety and Regulatory Due Diligence Audit",
            "type": "Operational, safety, engineering and quality due diligence audit",
            "framework": "DGCA India FTO requirements, applicable CARs and international best practice",
            "status": "Draft",
            "classification": "Confidential – Commercial in Confidence",
            "distribution": "Management of the commissioning organisation. Confidential – not for onward distribution without written authorisation."
        },
        "text": template.get("text", {
            "purpose": "",
            "exec": "",
            "themes": "",
            "conclusion": ""
        }),
        "lists": {
            "locations": [{"name": base_name, "state": "", "status": "Audited"}],
            "team": [
                {"name": lead_name, "email": lead_email, "role": "Lead Auditor"},
                {"name": "", "email": "", "role": "Auditor"},
                {"name": "", "email": "", "role": "Auditor"}
            ],
            "personnel": [],
            "cadre": template.get("lists", {}).get("cadre", []),
            "fleet": []
        },
        "secs": {},
        "items": {},
        "files": {},
        "genAtt": [],
        "imports": [],
        "inputs": {},
        "me": None,
        "fileSavedAt": now
    }

    # Initialize all standard sections as 'on' with unassigned auditor
    for sid in ["ORG", "FO", "SMS", "FDM", "ATS", "TRG", "QA", "ACC", "NB", "ENG", "CAM", "FLT", "INF"]:
        clean_state["secs"][sid] = {
            "on": True,
            "auditor": "",
            "auditor2": "",
            "comment": "",
            "att": [],
            "custom": []
        }

    # Write clean state to SQLite DB
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_state (
                key TEXT PRIMARY KEY,
                json_data TEXT,
                updated_at TIMESTAMP
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO audit_state (key, json_data, updated_at) VALUES (?, ?, ?)",
            ("current", json.dumps(clean_state), now)
        )
    print(f"Database cleanly reset in: {DB_PATH}")
    print(f"Lead Auditor configured: {lead_name} ({lead_email})")
    print(f"Audited Organisation: {audited_org} | Base: {base_name}")

    # Generate a fresh clean Excel in OneDrive
    try:
        generate_audit_excel(clean_state, EXCEL_PATH, EVIDENCE_DIR)
        print(f"Fresh blank Excel workbook written: {EXCEL_PATH}")
    except PermissionError:
        print(f"Note: {EXCEL_PATH} is currently open in Excel. Close it to update on disk.")
    except Exception as e:
        print(f"Notice generating blank Excel: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset FTO Audit to a blank production state.")
    parser.add_argument("--lead", default="SRINIVAS RAO", help="Lead Auditor full name")
    parser.add_argument("--email", default="srinivas.rao@marigoldaviation.com", help="Lead Auditor email ID")
    parser.add_argument("--org", default="NEW FTO AUDITEE", help="Audited organisation name")
    parser.add_argument("--base", default="Main Base", help="Initial base location")
    args = parser.parse_args()

    create_blank_audit(args.lead, args.email, args.org, "", args.base)
