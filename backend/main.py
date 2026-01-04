from fastapi import FastAPI, UploadFile, File
from backend.database import save_invoice
from backend.models import InvoiceRecord
from backend.extractor import extract_qr
from backend.govt_validator import is_government_invoice
import uuid

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Backend is running 🚀"}


@app.post("/upload-invoice")
async def upload_invoice(file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())  # 🔒 unique request tracking

    file_bytes = await file.read()

    print(f"[{request_id}] Processing file:", file.filename)

    qr_data = extract_qr(file_bytes, file.content_type)

    print(f"[{request_id}] QR DATA:", qr_data)

    is_govt = is_government_invoice(qr_data)

    if not is_govt:
        print(f"[{request_id}] Not a government invoice. Skipped.")
        return {
            "request_id": request_id,
            "file_name": file.filename,
            "government_invoice": False,
            "qr_found": qr_data is not None
        }

    record = InvoiceRecord(
        file_name=file.filename,
        file_type=file.content_type,
        qr_data=qr_data
    )

    save_invoice(record)

    print(f"[{request_id}] Saved to DB:", file.filename)

    return {
        "request_id": request_id,
        "file_name": file.filename,
        "government_invoice": True,
        "qr_found": True
    }
