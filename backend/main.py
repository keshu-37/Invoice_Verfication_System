ENABLE_DATABASE = True   # 🔁 set True when DB is enabled

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.database import save_invoice, is_duplicate_invoice_db
from backend.models import InvoiceRecord
from backend.json_storage.json_store import (
    save_invoice_to_json,
    is_duplicate_invoice_json
)
from backend.extractor import extract_qr
from backend.govt_validator import validate_invoice

from pathlib import Path
import uuid
import json
import hashlib

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

    # ------------------------------------------------
    # 1️⃣ Extract QR data
    # ------------------------------------------------
    extracted = extract_qr(file_bytes, file.content_type)

    if not extracted:
        return {
            "request_id": request_id,
            "file_name": file.filename,
            "status": "INVALID",
            "reason": "Unsupported file type"
        }

    input_type = extracted.get("input_type")
    qr_found = extracted.get("qr_found")
    qr_decoded = extracted.get("qr_decoded")

    # 🔑 RAW QR STRING (JWT) — required by validator
    qr_data_raw = extracted.get("qr_data_raw")

    print(f"[{request_id}] INPUT TYPE:", input_type)
    print(f"[{request_id}] QR FOUND:", qr_found)
    print(f"[{request_id}] QR DECODED:", qr_decoded)

    # ------------------------------------------------
    # 2️⃣ Generate invoice hash (for duplicates)
    # ------------------------------------------------
    invoice_hash = None
    if qr_data_raw:
        invoice_hash = hashlib.sha256(qr_data_raw.encode()).hexdigest()

    # ------------------------------------------------
    # 3️⃣ DUPLICATE CHECK (DB + JSON)
    # ------------------------------------------------
    if invoice_hash:
        if ENABLE_DATABASE:
            if is_duplicate_invoice_db(invoice_hash):
                return {
                    "request_id": request_id,
                    "file_name": file.filename,
                    "status": "DUPLICATE_INVOICE",
                    "message": "Invoice already exists in database"
                }
        else:
            if is_duplicate_invoice_json(invoice_hash):
                return {
                    "request_id": request_id,
                    "file_name": file.filename,
                    "status": "DUPLICATE_INVOICE",
                    "message": "Invoice already exists in system"
                }

    # ------------------------------------------------
    # 4️⃣ Validate invoice (business logic)
    # ------------------------------------------------
    validation_result = validate_invoice(
        input_type=input_type,
        qr_found=qr_found,
        qr_decoded=qr_decoded,
        qr_data=qr_data_raw,
        pdf_metadata=None
    )

    status = validation_result["status"]

    # ------------------------------------------------
    # 5️⃣ Audit record (always saved)
    # ------------------------------------------------
    audit_record = {
        "request_id": request_id,
        "file_name": file.filename,
        "file_type": file.content_type,
        "input_type": input_type,
        "invoice_hash": invoice_hash,
        "qr": {
            "found": qr_found,
            "decoded": qr_decoded,
            "invoice_data": extracted.get("qr_data_decoded", {}),
            "raw_jwt": qr_data_raw
        },
        "validation_result": validation_result
    }

    # ------------------------------------------------
    # 6️⃣ Rejection handling
    # ------------------------------------------------
    if status != "GOVERNMENT_VERIFIED":
        print(f"[{request_id}] Invoice rejected:", validation_result["reason"])
        save_invoice_to_json(audit_record)

        return {
            "request_id": request_id,
            "file_name": file.filename,
            "status": status,
            "reason": validation_result["reason"]
        }

    # ------------------------------------------------
    # 7️⃣ Accepted invoice → save
    # ------------------------------------------------
    record = InvoiceRecord(
        file_name=file.filename,
        file_type=file.content_type,
        invoice_hash=invoice_hash,
        qr_data=json.dumps(validation_result, indent=2)
    )

    if ENABLE_DATABASE:
        save_invoice(record)

    save_invoice_to_json(audit_record)

    print(f"[{request_id}] Government verified invoice accepted")

    return {
        "request_id": request_id,
        "file_name": file.filename,
        "status": "GOVERNMENT_VERIFIED",
        "risk_level": validation_result["risk_level"],
        "note": validation_result["note"]
    }
