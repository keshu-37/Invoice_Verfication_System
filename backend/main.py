from fastapi import FastAPI, UploadFile, File
from backend.database import save_invoice
from backend.models import InvoiceRecord
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
from backend.extractor import extract_qr
from backend.govt_validator import (
    extract_readable_invoice_data,
    verify_nic_signature
)

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

    # 1️⃣ Extract QR
    qr_data = extract_qr(file_bytes, file.content_type)
    print(f"[{request_id}] QR DATA (RAW):", qr_data)

    # 2️⃣ LEVEL-1 + LEVEL-2
    readable_invoice_data = extract_readable_invoice_data(qr_data)

    if not readable_invoice_data:
        print(f"[{request_id}] Not a government invoice (Failed at Level-1 / Level-2)")
        return {
            "request_id": request_id,
            "file_name": file.filename,
            "government_invoice": False,
            "reason": "Level-1 / Level-2 validation failed"
        }

    # 3️⃣ LEVEL-3 (NIC signature verification)
    if not verify_nic_signature(qr_data):
        print(f"[{request_id}] Not a government invoice (Failed at Level-3 Signature)")
        return {
            "request_id": request_id,
            "file_name": file.filename,
            "government_invoice": False,
            "reason": "signature verification failed"
        }

    
    record = InvoiceRecord(
        file_name=file.filename,
        file_type=file.content_type,
        qr_data=json.dumps(readable_invoice_data, indent=2)
    )

    save_invoice(record)

    print(f"[{request_id}]  Govt invoice verified & saved")

    return {
        "request_id": request_id,
        "file_name": file.filename,
        "government_invoice": True,
        "verification_level": "Level-1 + Level-2 + Level-3",
        "stored_format": "readable_json"
    }

 