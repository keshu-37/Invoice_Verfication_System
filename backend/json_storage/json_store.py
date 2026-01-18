import json
from pathlib import Path
from datetime import datetime

JSON_FILE = Path(__file__).parent / "verified_invoices.json"

def save_invoice_to_json(audit_record):
    try:
        if not JSON_FILE.exists():
            JSON_FILE.write_text("[]")

        data = json.loads(JSON_FILE.read_text())

        data.append({
            "file_name": audit_record["file_name"],
            "file_type": audit_record["file_type"],
            "government_invoice": audit_record["government_invoice"],
            "qr_data": audit_record["qr_data_raw"],
            "stored_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ UTC")
        })

        JSON_FILE.write_text(json.dumps(data, indent=2))

        print(">>> Saved invoice to JSON file")

    except Exception as e:
        # VERY IMPORTANT: do NOT break SQL flow
        print("⚠️ JSON save failed (ignored):", e)
