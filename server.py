import os
import json
import base64
import sqlite3
import datetime
import sys

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, redirect, url_for, session, render_template_string
import msal
from excel_sync import generate_audit_excel

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "marigold_fto_audit_sso_secret_2026_xyz")
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max payload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load local .env if present
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "95aaa257-5e66-4b77-82c7-a22376ad0d8b")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "04009f21-9442-496d-8d50-a3722ad71fbd")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
SCOPES = ["User.Read"]
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

def _build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=AZURE_CLIENT_SECRET,
        token_cache=cache
    )

def get_redirect_uri():
    host = request.headers.get("X-Forwarded-Host", request.host)
    proto = request.headers.get("X-Forwarded-Proto", "https" if ("onrender.com" in host or "trycloudflare.com" in host) else request.scheme)
    return f"{proto}://{host}/login/callback"

# Permanent Lead Auditors (Full Master Control)
LEAD_AUDITOR_EMAILS = {"srinivas.rao@mgavia.com", "sunny.sharma@mgavia.com"}

PERMANENT_ADMINS = {
    "srinivas.rao@mgavia.com": {"name": "Srinivas Rao", "role": "Lead Auditor", "route": "/master", "index": 0},
    "sunny.sharma@mgavia.com": {"name": "Sunny Sharma", "role": "Lead Auditor", "route": "/master", "index": 0}
}

def get_authorized_team():
    state = get_current_state()
    team = state.get("lists", {}).get("team", [])
    if not team:
        return [
            {"name": "Srinivas Rao", "email": "srinivas.rao@mgavia.com", "role": "Lead Auditor", "base": "All Aerodromes"},
            {"name": "Sunny Sharma", "email": "sunny.sharma@mgavia.com", "role": "Lead Auditor", "base": "All Aerodromes"}
        ]
    return team

def find_authorized_user(email, full_name=""):
    if not email:
        return None
    email_clean = email.strip().lower()
    
    # 1. Permanent Lead Auditors (Srinivas Rao and Sunny Sharma)
    if email_clean in LEAD_AUDITOR_EMAILS:
        name = "Srinivas Rao" if "srinivas" in email_clean else "Sunny Sharma"
        # Auto-heal: Ensure role is Lead Auditor in database team list
        try:
            state = get_current_state()
            if "lists" in state and "team" in state["lists"]:
                for t in state["lists"]["team"]:
                    if t.get("email", "").strip().lower() == email_clean:
                        t["role"] = "Lead Auditor"
                save_current_state(state)
        except Exception:
            pass
        return {
            "name": name,
            "email": email_clean,
            "role": "Lead Auditor",
            "route": "/master",
            "index": 0
        }
    
    # 2. Check active database team list
    team = get_authorized_team()
    for i, m in enumerate(team):
        if m.get("email", "").strip().lower() == email_clean:
            is_lead = "lead" in m.get("role", "").lower()
            return {
                "name": m.get("name") or full_name or email_clean.split("@")[0].title(),
                "email": email_clean,
                "role": "Lead Auditor" if is_lead else "Auditor",
                "route": "/master" if is_lead else f"/auditor{i if i > 0 else 1}",
                "index": i
            }
            
    # 3. Automatic Colleague Enrollment
    # Any authenticated employee logging in via company Microsoft 365 is welcomed as an Auditor
    colleague_name = full_name or email_clean.split("@")[0].replace(".", " ").title()
    try:
        state = get_current_state()
        if "lists" not in state: state["lists"] = {}
        if "team" not in state["lists"]: state["lists"]["team"] = []
        new_idx = len(state["lists"]["team"])
        state["lists"]["team"].append({
            "name": colleague_name,
            "email": email_clean,
            "role": "Auditor",
            "base": "All Aerodromes"
        })
        save_current_state(state)
        print(f"[Auto-Enrolled Colleague] Added {colleague_name} ({email_clean}) to team as Auditor {new_idx}.")
        return {
            "name": colleague_name,
            "email": email_clean,
            "role": "Auditor",
            "route": f"/auditor{new_idx}",
            "index": new_idx
        }
    except Exception as e:
        print(f"[Auto-Enrollment Fallback] {e}")
        return {
            "name": colleague_name,
            "email": email_clean,
            "role": "Auditor",
            "route": "/auditor1",
            "index": 1
        }

LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign In — Marigold Aviation FTO Audit Portal</title>
<link rel="stylesheet" href="/static/style.css">
<style>
  body { display:flex; min-height:100vh; align-items:center; justify-content:center; background:#0f2744; margin:0; padding:20px; box-sizing:border-box; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .login-card { background:#fff; border-radius:14px; padding:40px 32px; width:100%; max-width:440px; box-shadow:0 16px 40px rgba(0,0,0,0.3); text-align:center; }
  .logo-title { font-size:18px; font-weight:800; color:#0f2744; letter-spacing:0.04em; text-transform:uppercase; margin:12px 0 4px; }
  .sub-title { font-size:13px; color:#5d6b7a; margin-bottom:28px; line-height:1.5; }
  .ms-btn { display:inline-flex; align-items:center; justify-content:center; gap:12px; width:100%; background:#2f2f2f; color:#fff; text-decoration:none; padding:14px 20px; border-radius:8px; font-size:15px; font-weight:600; transition:background 0.2s; box-sizing:border-box; }
  .ms-btn:hover { background:#1b1b1b; }
  .ms-logo { width:20px; height:20px; }
  .sec-note { margin-top:28px; font-size:11px; color:#8898aa; line-height:1.5; border-top:1px solid #eef2f6; padding-top:16px; }
</style>
</head>
<body>
<div class="login-card">
  <div style="font-size:32px">✈️</div>
  <div class="logo-title">Marigold Aviation</div>
  <div style="font-weight:700;font-size:15px;color:#1f4e79;margin-bottom:6px">FTO Audit & Compliance Portal</div>
  <div class="sub-title">Flight Training Organisation Due Diligence, Safety & Regulatory Governance</div>
  
  <a href="/login/ms" class="ms-btn">
    <svg class="ms-logo" viewBox="0 0 21 21"><rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/></svg>
    Sign in with Microsoft 365
  </a>

  <div class="sec-note">
    🔒 <b>Protected Enterprise Resource</b><br>
    Access is strictly restricted to designated auditors with corporate Microsoft accounts (<code>@mgavia.com</code>).
  </div>
</div>
</body>
</html>"""

ACCESS_DENIED_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Access Denied — Marigold Aviation</title>
<link rel="stylesheet" href="/static/style.css">
<style>
  body { display:flex; min-height:100vh; align-items:center; justify-content:center; background:#f4f5f7; margin:0; padding:20px; box-sizing:border-box; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .card { background:#fff; border-radius:12px; padding:36px 32px; width:100%; max-width:480px; box-shadow:0 8px 24px rgba(0,0,0,0.1); text-align:center; border:1px solid #e5e7eb; }
  .badge-denied { display:inline-block; padding:4px 12px; background:#fee2e2; color:#b91c1c; border-radius:20px; font-size:12px; font-weight:700; margin-bottom:12px; }
  .email-box { background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:8px 12px; font-weight:600; color:#1e293b; font-size:13px; margin:16px 0; word-break:break-all; }
</style>
</head>
<body>
<div class="card">
  <span class="badge-denied">⛔ ACCESS DENIED</span>
  <h2 style="margin:4px 0 10px;color:#111827">Account Not Authorized</h2>
  <p style="color:#4b5563;font-size:13px;line-height:1.6">You successfully authenticated via Microsoft, but your account is not on the active FTO Audit Team whitelist:</p>
  <div class="email-box">{{ email }}</div>
  <p style="font-size:12px;color:#6b7280;line-height:1.6">If you are an assigned auditor, please request the Lead Auditor (<b>Srinivas Rao</b> · <a href="mailto:srinivas.rao@mgavia.com">srinivas.rao@mgavia.com</a>) to add your email to the governance register.</p>
  <div style="margin-top:20px">
    <a href="/logout" class="btn" style="text-decoration:none;display:inline-block">Sign in with a different account</a>
  </div>
</div>
</body>
</html>"""

@app.route("/login")
def login_view():
    if session.get("user"):
        return redirect(session["user"].get("route", "/"))
    return render_template_string(LOGIN_PAGE_HTML)

@app.route("/login/ms")
def login_ms():
    msal_app = _build_msal_app()
    redirect_uri = get_redirect_uri()
    auth_state = os.urandom(16).hex()
    session["auth_state"] = auth_state
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPES,
        state=auth_state,
        redirect_uri=redirect_uri
    )
    return redirect(auth_url)

@app.route("/login/callback")
def login_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or state != session.get("auth_state"):
        return redirect(url_for("login_view"))
        
    redirect_uri = get_redirect_uri()
    msal_app = _build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    if "error" in result:
        print(f"[Azure Auth Error] {result.get('error')}: {result.get('error_description')}")
        return f"<h3>Authentication Failed</h3><p>{result.get('error_description')}</p><p><a href='/login'>Try Again</a></p>", 400
        
    claims = result.get("id_token_claims", {})
    email = (claims.get("preferred_username") or claims.get("email") or claims.get("upn") or "").strip().lower()
    name = claims.get("name") or email.split("@")[0].title()
    
    auth_user = find_authorized_user(email, full_name=name)
    if not auth_user:
        return render_template_string(ACCESS_DENIED_HTML, email=email), 403
        
    session.permanent = True
    session["user"] = auth_user
    return redirect(auth_user["route"])

@app.route("/logout")
def logout_view():
    session.clear()
    return redirect(url_for("login_view"))

@app.before_request
def enforce_azure_auth():
    path = request.path
    if path.startswith("/static/") or path in ["/login", "/login/ms", "/login/callback", "/logout", "/health"]:
        return None
        
    user = session.get("user")
    if not user:
        return redirect(url_for("login_view"))
        
    # Role protection: Auditor cannot access /master
    if path == "/master" and user.get("role") != "Lead Auditor":
        return redirect(user.get("route", "/auditor1"))

# ----------------------------------------------------
# 3 Canonical Roles (Master, Auditor 1, Auditor 2)
# ----------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", mode="portal", role_label="Portal", user=session.get("user"))

@app.route("/master")
def master_view():
    user = session.get("user", {})
    cfg = {"mode": "master", "currentUser": user}
    return render_template("index.html", mode="master", role_label="Master Dashboard", cfg=json.dumps(cfg), pdfw_content=PDFW_CONTENT, user=user)

@app.route("/auditor<int:num>")
def auditor_n_view(num):
    user = session.get("user", {})
    cfg = {
        "mode": "auditor",
        "instanceId": f"A{num}",
        "currentUser": user,
        "me": {
            "name": user.get("name", ""),
            "role": "Auditor",
            "label": f"Auditor {num}",
            "sections": []
        }
    }
    return render_template("index.html", mode="auditor", role_label=f"Auditor {num}", cfg=json.dumps(cfg), pdfw_content=PDFW_CONTENT, user=user)

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

