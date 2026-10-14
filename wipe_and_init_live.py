import os
import json
import sqlite3
import datetime
import shutil
from excel_sync import generate_audit_excel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ONEDRIVE_DIR = r"C:\Users\sunny\OneDrive - Marigold Aviation\Apps\Anitgravity\Audit Trail"
EVIDENCE_DIR = os.path.join(ONEDRIVE_DIR, "Evidence")
EXCEL_PATH = os.path.join(ONEDRIVE_DIR, "FTO_Audit_Consolidated.xlsx")
DB_PATH = os.path.join(BASE_DIR, "fto_audit.db")

def wipe_and_init_live():
    now = datetime.datetime.now().isoformat()
    today_str = datetime.date.today().isoformat()
    
    # 1. Clean Production State
    clean_state = {
        "v": 2,
        "meta": {
            "auditingOrg": "Marigold Aviation",
            "auditedOrg": "",
            "approvalNo": "",
            "from": today_str,
            "to": today_str,
            "title": "Operational, Safety and Regulatory Due Diligence Audit",
            "type": "Operational, safety, engineering and quality due diligence audit",
            "framework": "DGCA India FTO requirements, applicable CARs and international best practice",
            "status": "Draft",
            "classification": "Confidential – Commercial in Confidence",
            "distribution": "Management of the commissioning organisation. Confidential – not for onward distribution without written authorisation."
        },
        "text": {
            "purpose": "Comprehensive operational, regulatory, safety and quality due diligence audit of the Flying Training Organisation.",
            "exec": "",
            "themes": "",
            "conclusion": ""
        },
        "lists": {
            "locations": [{"name": "Main Base", "state": "", "status": "Audited"}],
            "team": [
                {
                    "name": "Srinivas Rao",
                    "email": "srinivas.rao@mgavia.com",
                    "role": "Lead Auditor",
                    "base": "All Aerodromes"
                },
                {
                    "name": "Sunny Sharma",
                    "email": "Sunny.Sharma@mgavia.com",
                    "role": "Auditor",
                    "base": "All Aerodromes"
                }
            ],
            "personnel": [],
            "cadre": [],
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

    # All 13 functional sections active and in-scope
    all_sections = ["ORG", "FO", "SMS", "FDM", "ATS", "TRG", "QA", "ENG", "CAM", "FLT", "INF", "ACC", "NB"]
    for sid in all_sections:
        clean_state["secs"][sid] = {
            "on": True,
            "auditor": "",
            "auditor2": "",
            "comment": "",
            "att": [],
            "custom": []
        }

    # 2. Write to SQLite database
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
    print(" 1. SQLite database successfully reset with clean live state.")

    # 3. Save initial_saved.json for fresh resets
    initial_path = os.path.join(BASE_DIR, "initial_saved.json")
    with open(initial_path, "w", encoding="utf-8") as f:
        json.dump({"savedAt": now, "state": clean_state}, f, indent=2)
    print(" 2. initial_saved.json updated with live team configuration.")

    # 4. Archive old dummy evidence screenshots
    archive_dir = os.path.join(EVIDENCE_DIR, "_archive_test_evidence")
    if os.path.exists(EVIDENCE_DIR):
        test_files = [f for f in os.listdir(EVIDENCE_DIR) if os.path.isfile(os.path.join(EVIDENCE_DIR, f)) and not f.startswith(".")]
        if test_files:
            os.makedirs(archive_dir, exist_ok=True)
            for f in test_files:
                src = os.path.join(EVIDENCE_DIR, f)
                dst = os.path.join(archive_dir, f)
                shutil.move(src, dst)
            print(f" 3. Moved {len(test_files)} dummy test screenshots to Evidence/_archive_test_evidence/.")

    # 5. Generate pristine FTO_Audit_Consolidated.xlsx
    try:
        generate_audit_excel(clean_state, EXCEL_PATH, EVIDENCE_DIR)
        print(f" 4. Generated pristine Excel workbook on disk: {EXCEL_PATH}")
    except PermissionError:
        print(f" [Notice] {EXCEL_PATH} is currently open in Microsoft Excel.")
        print("          Please close Excel so the clean workbook can be written directly to disk.")
    except Exception as e:
        print(f" Notice writing Excel: {e}")

    print("\n" + "="*60)
    print("LIVE PRODUCTION RESET COMPLETE")
    print("="*60)
    print("Team Configuration:")
    print(" - Lead Auditor: Srinivas Rao (srinivas.rao@mgavia.com)")
    print(" - Auditor:      Sunny Sharma (Sunny.Sharma@mgavia.com)")
    print("All dummy findings, ratings, and test evidence cleared.")
    print("="*60 + "\n")

if __name__ == "__main__":
    wipe_and_init_live()
