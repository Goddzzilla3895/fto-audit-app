import os
import json
import base64
import sqlite3
import datetime
import sys

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, redirect, url_for
from excel_sync import generate_audit_excel

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max payload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_ONEDRIVE = r"C:\Users\sunny\OneDrive - Marigold Aviation\Apps\Anitgravity\Audit Trail"
if os.path.exists(LOCAL_ONEDRIVE):
    ONEDRIVE_DIR = LOCAL_ONEDRIVE
else:
    ONEDRIVE_DIR = os.environ.get("AUDIT_TRAIL_DIR", os.path.join(BASE_DIR, "Audit_Trail"))
EVIDENCE_DIR = os.path.join(ONEDRIVE_DIR, "Evidence")
EXCEL_PATH = os.path.join(ONEDRIVE_DIR, "FTO_Audit_Consolidated.xlsx")
DB_PATH = os.path.join(BASE_DIR, "fto_audit.db")

os.makedirs(EVIDENCE_DIR, exist_ok=True)
os.makedirs(ONEDRIVE_DIR, exist_ok=True)

PDFW_PATH = os.path.join(BASE_DIR, "static", "pdfw.js")
PDFW_CONTENT = ""
if os.path.exists(PDFW_PATH):
    with open(PDFW_PATH, "r", encoding="utf-8", errors="ignore") as f:
        PDFW_CONTENT = f.read()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_state (
                key TEXT PRIMARY KEY,
                json_data TEXT,
                updated_at TIMESTAMP
            )
        """)
        row = conn.execute("SELECT key FROM audit_state WHERE key = 'current'").fetchone()
        if not row:
            initial_path = os.path.join(BASE_DIR, "initial_saved.json")
            if os.path.exists(initial_path):
                with open(initial_path, "r", encoding="utf-8") as f:
                    init_data = json.load(f)
                state = init_data.get("state", {})
                conn.execute(
                    "INSERT INTO audit_state (key, json_data, updated_at) VALUES (?, ?, ?)",
                    ("current", json.dumps(state), datetime.datetime.now().isoformat())
                )
                print("Database initialized with Dunes Aviation initial state.")

init_db()

def get_current_state():
    with get_db() as conn:
        row = conn.execute("SELECT json_data FROM audit_state WHERE key = 'current'").fetchone()
        if row and row["json_data"]:
            return json.loads(row["json_data"])
    return {}

from excel_sync import generate_audit_excel, import_audit_excel

import time

LAST_EXCEL_MTIME = os.path.getmtime(EXCEL_PATH) if os.path.exists(EXCEL_PATH) else 0
LAST_SERVER_WRITE_TIME = 0

def check_and_sync_excel():
    global LAST_EXCEL_MTIME, LAST_SERVER_WRITE_TIME
    if not os.path.exists(EXCEL_PATH):
        return False
    try:
        current_mtime = os.path.getmtime(EXCEL_PATH)
        # If Excel file has a different mtime than what we recorded, and server didn't write it in the last 2 seconds
        if abs(current_mtime - LAST_EXCEL_MTIME) > 0.05:
            if time.time() - LAST_SERVER_WRITE_TIME > 2.0:
                print(f"[Two-Way Sync] Detected Excel save on disk (mtime: {current_mtime}). Importing to Web App...")
                current_state = get_current_state()
                updated_count, new_state = import_audit_excel(EXCEL_PATH, current_state)
                now = datetime.datetime.now().isoformat()
                new_state["fileSavedAt"] = now
                with get_db() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO audit_state (key, json_data, updated_at) VALUES (?, ?, ?)",
                        ("current", json.dumps(new_state), now)
                    )
                LAST_EXCEL_MTIME = os.path.getmtime(EXCEL_PATH)
                print(f"[Two-Way Sync] Successfully imported {updated_count} items from Excel to Web App at {now}.")
                return True
            else:
                LAST_EXCEL_MTIME = current_mtime
    except PermissionError:
        pass
    except Exception as e:
        print(f"[Two-Way Sync] Notice checking Excel: {e}")
    return False

def save_current_state(state):
    global LAST_EXCEL_MTIME, LAST_SERVER_WRITE_TIME
    files = state.get("files", {})
    for fid, finfo in files.items():
        fname = finfo.get("name", f"{fid}.jpg")
        clean_name = f"{fid}_{fname.replace(' ', '_')}"
        if not clean_name.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf', '.webp')):
            clean_name += ".jpg"
        finfo["saved_filename"] = clean_name
        dest_path = os.path.join(EVIDENCE_DIR, clean_name)
        
        d = finfo.get("d", "")
        if d and "," in d and not os.path.exists(dest_path):
            try:
                b64 = d.split(",", 1)[1]
                raw = base64.b64decode(b64)
                with open(dest_path, "wb") as img_f:
                    img_f.write(raw)
            except Exception as e:
                print(f"Error extracting base64 file {clean_name}: {e}")

    now = datetime.datetime.now().isoformat()
    state["fileSavedAt"] = now
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO audit_state (key, json_data, updated_at) VALUES (?, ?, ?)",
            ("current", json.dumps(state), now)
        )
    
    try:
        LAST_SERVER_WRITE_TIME = time.time()
        generate_audit_excel(state, EXCEL_PATH, EVIDENCE_DIR)
        LAST_EXCEL_MTIME = os.path.getmtime(EXCEL_PATH)
    except PermissionError:
        print(f"Notice: {EXCEL_PATH} is open in Excel; will sync to disk once closed.")
    except Exception as e:
        print(f"Error auto-generating Excel on save: {e}")
        
    return now

# ----------------------------------------------------
# 3 Canonical Roles (Master, Auditor 1, Auditor 2)
# ----------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", mode="portal", role_label="Portal")

@app.route("/master")
def master_view():
    cfg = {"mode": "master"}
    return render_template("index.html", mode="master", role_label="Master Dashboard", cfg=json.dumps(cfg), pdfw_content=PDFW_CONTENT)

@app.route("/auditor<int:num>")
def auditor_n_view(num):
    cfg = {
        "mode": "auditor",
        "instanceId": f"A{num}",
        "me": {
            "name": "",
            "role": "Auditor",
            "label": f"Auditor {num}",
            "sections": []
        }
    }
    return render_template("index.html", mode="auditor", role_label=f"Auditor {num}", cfg=json.dumps(cfg), pdfw_content=PDFW_CONTENT)

@app.route("/auditor1")
def auditor1_view():
    return auditor_n_view(1)

@app.route("/auditor2")
def auditor2_view():
    return auditor_n_view(2)

# ----------------------------------------------------
# REST API Endpoints (Auto-Save, Auto-Populate, Excel)
# ----------------------------------------------------
@app.route("/api/state", methods=["GET"])
def api_get_state():
    state = get_current_state()
    return jsonify({"status": "ok", "state": state})

@app.route("/api/sync", methods=["GET"])
def api_sync():
    check_and_sync_excel()
    with get_db() as conn:
        row = conn.execute("SELECT updated_at FROM audit_state WHERE key = 'current'").fetchone()
        updated_at = row["updated_at"] if row else ""
    return jsonify({"status": "ok", "savedAt": updated_at})

@app.route("/api/save", methods=["POST"])
def api_save_state():
    payload = request.get_json(force=True)
    incoming_state = payload.get("state")
    if not incoming_state:
        return jsonify({"status": "error", "message": "No state provided"}), 400
    
    saved_time = save_current_state(incoming_state)
    return jsonify({
        "status": "ok",
        "savedAt": saved_time,
        "excelPath": EXCEL_PATH,
        "evidenceDir": EVIDENCE_DIR
    })

@app.route("/api/upload", methods=["POST"])
def api_upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({"status": "error", "message": "Empty filename"}), 400
        
    fid = request.form.get("fid", f"f_{int(datetime.datetime.now().timestamp()*1000)}")
    ref = request.form.get("ref", "")
    caption = request.form.get("cap", "")
    
    clean_name = f"{fid}_{f.filename.replace(' ', '_')}"
    dest_path = os.path.join(EVIDENCE_DIR, clean_name)
    f.save(dest_path)
    
    file_info = {
        "id": fid,
        "name": f.filename,
        "type": f.content_type,
        "size": os.path.getsize(dest_path),
        "cap": caption,
        "added": datetime.datetime.now().isoformat(),
        "ref": ref,
        "saved_filename": clean_name,
        "url": f"/evidence/{clean_name}"
    }
    return jsonify({"status": "ok", "file": file_info})

@app.route("/api/export-excel", methods=["GET"])
def api_export_excel():
    import io
    state = get_current_state()
    bio = io.BytesIO()
    generate_audit_excel(state, bio, EVIDENCE_DIR)
    bio.seek(0)
    
    # Also update the OneDrive file
    try:
        generate_audit_excel(state, EXCEL_PATH, EVIDENCE_DIR)
    except Exception as e:
        print(f"Notice updating OneDrive file: {e}")
        
    return send_file(
        bio,
        as_attachment=True,
        download_name="FTO_Audit_Consolidated.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/api/import-excel", methods=["POST"])
def api_import_excel():
    from excel_sync import import_audit_excel
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No excel file uploaded"}), 400
    f = request.files['file']
    state = get_current_state()
    try:
        updated_count, new_state = import_audit_excel(f.stream, state)
        save_current_state(new_state)
        return jsonify({"status": "ok", "updated_items": updated_count, "message": f"Successfully imported {updated_count} items from Excel."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to import Excel: {str(e)}"}), 500

@app.route("/evidence/<path:filename>")
def serve_evidence(filename):
    return send_from_directory(EVIDENCE_DIR, filename)

if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
        
    print("\n" + "="*60)
    print("FTO AUDIT SYSTEM - RUNNING")
    print("="*60)
    print(f"Laptop / Local:   http://localhost:8000")
    print(f"Phone / Wi-Fi:    http://{local_ip}:8000")
    print(f"Master Auditor:   http://localhost:8000/master")
    print(f"Auditor 1:        http://localhost:8000/auditor1")
    print(f"Auditor 2:        http://localhost:8000/auditor2")
    print(f"OneDrive Path:    {ONEDRIVE_DIR}")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)

