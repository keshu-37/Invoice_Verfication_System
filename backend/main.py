ENABLE_DATABASE = False

from fastapi import FastAPI, UploadFile, File
from backend.database import save_invoice
from backend.models import InvoiceRecord
from backend.json_storage.json_store import save_invoice_to_json
from backend.extractor import extract_qr
from backend.govt_validator import (
    extract_readable_invoice_data,
    verify_nic_signature
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path

import uuid
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def frontend():
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    return html_path.read_text(encoding="utf-8")



@app.post("/upload-invoice")
async def upload_invoice(file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())
    file_bytes = await file.read()

    print(f"[{request_id}] Processing file:", file.filename)

    #  Extract QR
    qr_data = extract_qr(file_bytes, file.content_type)

    # record for audit (non government invoice)
    audit_record = {
    "request_id": request_id,
    "file_name": file.filename,
    "file_type": file.content_type,
    "qr_data_raw": qr_data,
    "government_invoice": False,
    "reason": None
}
    print(f"[{request_id}] QR DATA (RAW):", qr_data)

    #  LEVEL-1 + LEVEL-2
    readable_invoice_data = extract_readable_invoice_data(qr_data)
    if not readable_invoice_data:
        print(f"[{request_id}] Not a government invoice (Failed at Level-1 / Level-2)")
        save_invoice_to_json(audit_record)
        return {
            "request_id": request_id,
            "file_name": file.filename,
            "government_invoice": False,
            "reason": "Level-1 / Level-2 validation failed"
        }

    #  LEVEL-3 (NIC signature verification)
    if not verify_nic_signature(qr_data):
        print(f"[{request_id}] Not a government invoice (Failed at Level-3 Signature)")
        save_invoice_to_json(audit_record)
        return {
            "request_id": request_id,
            "file_name": file.filename,
            "government_invoice": False,
            "reason": "signature verification failed"
        }

    audit_record["government_invoice"] = True
    audit_record["readable_invoice_data"] = readable_invoice_data

    record = InvoiceRecord(
        file_name=file.filename,
        file_type=file.content_type,
        qr_data=json.dumps(readable_invoice_data, indent=2)
    )

    if ENABLE_DATABASE:
      save_invoice(record)   # DB save (disabled for now)

    save_invoice_to_json(audit_record)  # JSON always

    

    print(f"[{request_id}]  Govt invoice verified & saved")

    return {
        "request_id": request_id,
        "file_name": file.filename,
        "government_invoice": True,
        "verification_level": "Level-1 + Level-2 + Level-3",
        "stored_format": "readable_json"
    }

 