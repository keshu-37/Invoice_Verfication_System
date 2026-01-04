import re

GSTIN_REGEX = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b"
IRN_REGEX = r"\b[a-fA-F0-9]{64}\b"


def is_government_invoice(qr_data: str | None) -> bool:
    if not qr_data:
        return False

    qr_data = qr_data.upper()

    has_gstin = re.search(GSTIN_REGEX, qr_data) is not None
    has_irn = re.search(IRN_REGEX, qr_data) is not None

    return has_gstin and has_irn
