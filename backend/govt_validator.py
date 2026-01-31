import re
import base64
import json
import jwt
from pathlib import Path
from cryptography.hazmat.primitives import serialization

# ---------------- REGEX ----------------
GSTIN_REGEX = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b"
IRN_REGEX = r"\b[a-fA-F0-9]{64}\b"


# ---------------- JWT PAYLOAD ----------------
def decode_jwt_payload(jwt_token: str) -> dict | None:
    try:
        parts = jwt_token.split(".")
        if len(parts) != 3:
            return None

        payload_part = parts[1]
        padding = "=" * (-len(payload_part) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload_part + padding)
        return json.loads(decoded_bytes)
    except Exception:
        return None


# ---------------- LEVEL 1 + 2 ----------------
def extract_readable_invoice_data(qr_data: str | None) -> dict | None:
    """
    LEVEL-1 + LEVEL-2 validation
    """
    if not qr_data:
        return None

    qr_data = qr_data.strip()
    upper_data = qr_data.upper()

    # LEVEL-1: Plain-text QR
    if re.search(GSTIN_REGEX, upper_data) and re.search(IRN_REGEX, upper_data):
        return {"raw_qr": qr_data}

    # LEVEL-2: JWT QR
    payload = decode_jwt_payload(qr_data)
    if not payload:
        return None

    data_field = payload.get("data")
    if not data_field:
        return None

    try:
        invoice_data = json.loads(data_field)
    except Exception:
        return None

    combined = json.dumps(invoice_data).upper()
    if re.search(GSTIN_REGEX, combined) and re.search(IRN_REGEX, combined):
        return invoice_data

    return None


# ---------------- LEVEL 3 ----------------
def verify_nic_signature(jwt_token: str) -> bool:
    """
    Verifies QR JWT signature using NIC public key
    """
    try:
        key_path = Path(__file__).parent / "certs" / "einv1_pub_key.pem"

        with open(key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())

        jwt.decode(
            jwt_token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,
                "verify_iss": False
            }
        )
        return True

    except Exception as e:
        print("Level-3 signature verification failed:", e)
        return False


# ---------------- METADATA CHECK (DIGITAL ONLY) ----------------
def has_editing_metadata(pdf_metadata: dict) -> bool:
    suspicious_tools = [
        "ILOVEPDF", "SMALLPDF", "PDFSAM",
        "WORD", "CAMSCANNER", "ADOBE ACROBAT"
    ]

    producer = (pdf_metadata.get("producer") or "").upper()
    creator = (pdf_metadata.get("creator") or "").upper()

    for tool in suspicious_tools:
        if tool in producer or tool in creator:
            return True

    return False


# ---------------- FINAL DECISION ENGINE ----------------
def validate_invoice(
    *,
    input_type: str,
    qr_found: bool,
    qr_decoded: bool,
    qr_data: str | None,
    pdf_metadata: dict | None = None
) -> dict:
    """
    FINAL OFFLINE VALIDATION LOGIC
    """

    # ❌ QR missing
    if not qr_found:
        return {
            "status": "NOT_GOVERNMENT_VERIFIED",
            "reason": "Government-issued QR code not found"
        }

    # ❌ QR exists but decode failed
    if qr_found and not qr_decoded:
       return {
        "status": "NOT_GOVERNMENT_VERIFIED",
        "reason": "QR code is not a government-issued e-Invoice QR"
    }


    # ❌ QR decoded but not valid govt QR
    readable_data = extract_readable_invoice_data(qr_data)
    if not readable_data:
        return {
            "status": "NOT_GOVERNMENT_VERIFIED",
            "reason": "QR code is not issued by government system"
        }

    # ❌ QR signature invalid
    if not verify_nic_signature(qr_data):
        return {
            "status": "NOT_GOVERNMENT_VERIFIED",
            "reason": "QR signature verification failed"
        }

    # ❌ Digital PDF edited
    if input_type == "DIGITAL_PDF" and pdf_metadata:
        if has_editing_metadata(pdf_metadata):
            return {
                "status": "TAMPERED",
                "reason": "Digital PDF appears modified after generation"
            }

    # ✅ GOVERNMENT VERIFIED
    return {
        "status": "GOVERNMENT_VERIFIED",
        "risk_level": "LOW" if input_type == "DIGITAL_PDF" else "MEDIUM",
        "note": (
            "Original digital invoice"
            if input_type == "DIGITAL_PDF"
            else "Scanned copy verified via government-issued QR"
        )
    }

    