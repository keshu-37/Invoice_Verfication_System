import re
import base64
import json
import jwt
from pathlib import Path
from cryptography.hazmat.primitives import serialization

GSTIN_REGEX = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b"
IRN_REGEX = r"\b[a-fA-F0-9]{64}\b"


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


def extract_readable_invoice_data(qr_data: str | None) -> dict | None:
    """
    LEVEL-1 + LEVEL-2
    Returns readable invoice data if govt invoice, else None
    """
    if not qr_data:
        return None

    qr_data = qr_data.strip()

    # LEVEL-1: Plain text QR
    upper_data = qr_data.upper()
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


def verify_nic_signature(jwt_token: str) -> bool:
    """
    LEVEL-3
    Verifies JWT signature using NIC public key
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
        print(" Level-3 signature verification failed:", e)
        return False
    