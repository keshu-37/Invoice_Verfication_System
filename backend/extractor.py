import cv2
import numpy as np
from pyzbar.pyzbar import decode
import fitz  # PyMuPDF
from fastapi import HTTPException


def extract_qr(file_bytes: bytes, content_type: str):
    print(">>> Extracting QR from:", content_type)

    if content_type.startswith("image"):
        return extract_from_image(file_bytes)

    if content_type == "application/pdf":
        return extract_from_pdf(file_bytes)

    return None


def extract_from_image(image_bytes):
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    return try_decode(img)


# 🚀 STRONG SCANNED PDF DETECTOR (handles phone OCR PDFs)
def is_scanned_pdf(doc: fitz.Document) -> bool:
    """
    Detect scanned or image-dominant PDFs including
    phone-scanned PDFs with OCR text layer.
    """
    for page in doc:
        text_len = len(page.get_text("text").strip())
        images = page.get_images(full=True)

        # Image-dominant page (scan or phone PDF)
        if images and text_len < 200:
            return True

        # Strong digital signal
        if text_len > 500:
            return False

    # Default safe assumption
    return True


def extract_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    scanned = is_scanned_pdf(doc)

    if scanned:
        print(">>> SCANNED PDF DETECTED - Using image-based QR extraction")
    else:
        print(">>> DIGITAL PDF DETECTED - Using standard QR extraction")

    for page in doc:
        # 🔁 Higher DPI for scanned PDFs
        dpi = 300 if scanned else 200
        pix = page.get_pixmap(dpi=dpi)

        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, pix.n)

        if pix.n == 4:  # RGBA → BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # 🚀 Size fast-fail
        h, w = img.shape[:2]
        if h < 300 or w < 300:
            continue

        result = try_decode(img)
        if result:
            return result

    print(">>> QR NOT FOUND IN PDF")
    return None


def try_decode(img):
    if img is None:
        return None

    # Try multiple scales for small / blurry QR
    for scale in [1.0, 1.5, 2.0]:
        resized = cv2.resize(img, None, fx=scale, fy=scale)

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        thresh = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5
        )

        decoded = decode(thresh)
        if decoded:
            data = decoded[0].data.decode("utf-8")
            print(">>> QR FOUND:", data)
            return data

    return None
