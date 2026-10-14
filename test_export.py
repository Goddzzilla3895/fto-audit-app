import os
import json
import base64
from excel_sync import generate_audit_excel

onedrive_base = r"C:\Users\sunny\OneDrive - Marigold Aviation\Apps\Anitgravity\Audit Trail"
evidence_dir = os.path.join(onedrive_base, "Evidence")
os.makedirs(evidence_dir, exist_ok=True)
excel_path = os.path.join(onedrive_base, "FTO_Audit_Consolidated.xlsx")

with open("initial_saved.json", "r", encoding="utf-8") as f:
    saved = json.load(f)

state = saved.get("state", {})
files = state.get("files", {})

print(f"Extracting {len(files)} initial evidence files to OneDrive...")
for fid, finfo in files.items():
    d = finfo.get("d", "")
    fname = finfo.get("name", f"{fid}.jpg")
    # Clean filename
    clean_name = f"{fid}_{fname.replace(' ', '_')}"
    if not clean_name.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf')):
        clean_name += ".jpg"
    finfo["saved_filename"] = clean_name
    dest_path = os.path.join(evidence_dir, clean_name)
    
    if d and "," in d:
        b64 = d.split(",", 1)[1]
        try:
            raw = base64.b64decode(b64)
            with open(dest_path, "wb") as img_f:
                img_f.write(raw)
            print(f"  Saved: {clean_name} ({len(raw)} bytes)")
        except Exception as e:
            print(f"  Error saving {clean_name}: {e}")

generate_audit_excel(state, excel_path, evidence_dir)
print("Initial test successful! Check OneDrive output.")

