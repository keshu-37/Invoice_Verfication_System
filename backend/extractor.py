import cv2
import numpy as np
from pyzbar.pyzbar import decode
import fitz  # PyMuPDF
import base64
import json


#  QR JWT DECODER 
def decode_qr_jwt(jwt_token: str) -> dict:
    """
    Decode GST e-invoice QR JWT payload into readable invoice data.
    Signature verification is NOT done here.
    """
    try:
        payload_part = jwt_token.split(".")[1]
        padding = "=" * (-len(payload_part) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload_part + padding)
        payload = json.loads(decoded_bytes)

        # GST invoice data is JSON string inside "data"
        return json.loads(payload.get("data", "{}"))
    except Exception:
        return {}



def extract_qr(file_bytes: bytes, content_type: str):
    print(">>> Extracting QR from:", content_type)

    if content_type.startswith("image"):
        qr_data = extract_from_image(file_bytes)
        return {
            "input_type": "IMAGE",
            "qr_found": qr_data is not None,
            "qr_decoded": qr_data is not None,
            "qr_data_raw": qr_data,
            "qr_data_decoded": decode_qr_jwt(qr_data) if qr_data else {}
        }

    if content_type == "application/pdf":
        return extract_from_pdf(file_bytes)

    return None


#  IMAGE 
def extract_from_image(image_bytes):
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    return try_decode(img)


#  SCANNED PDF DETECTOR 
def is_scanned_pdf(doc: fitz.Document) -> bool:
    for page in doc:
        text_len = len(page.get_text("text").strip())
        images = page.get_images(full=True)

        if images and text_len < 200:
            return True
        if text_len > 500:
            return False

    return True


#   PDF  
def extract_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    scanned = is_scanned_pdf(doc)
    input_type = "SCANNED_PDF" if scanned else "DIGITAL_PDF"

    print(">>> PDF TYPE:", input_type)

    qr_raw = None
    qr_found = False
    qr_decoded = False

    for page_index, page in enumerate(doc):
        if page_index > 0:
            break

        pix = page.get_pixmap(dpi=180)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, pix.n)

        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        qr_raw = try_decode(img)

        if qr_raw:
            qr_found = True
            qr_decoded = True
            break
        else:
            qr_found = True

    return {
        "input_type": input_type,
        "qr_found": qr_found,
        "qr_decoded": qr_decoded,
        "qr_data_raw": qr_raw,
        "qr_data_decoded": decode_qr_jwt(qr_raw) if qr_raw else {}
    }


#   QR DECODER  
def try_decode(img):
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    decoded = decode(gray)

    if decoded:
        print(">>> QR FOUND")
        return decoded[0].data.decode("utf-8")

    print(">>> QR NOT FOUND")
    return None

