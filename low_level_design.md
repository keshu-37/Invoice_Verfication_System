#  Low-Level Design (LLD) & Implementation Guide

Name ---> Invoice QR Verification System

## 1. Project Objective

Build a backend system that:
Accepts an invoice file (PDF, PNG, JPG, JPEG)
Converts PDF to image (only first page)
Detects QR code from the image
Validates QR using pattern/format rules (NOT government API)
Stores extracted data in MySQL
Responds within ≤ 3 seconds


## 2. Tech Stack (Application Layer Only)

# Language & Framework

> Python 3.10+
> FastAPI
> Uvicorn

## Core Libraries (Mandatory)

opencv-python → image processing
pyzbar → QR code decoding
pdf2image → PDF → image conversion
Pillow → image loading & format handling

## Database

MySQL


## 4. High-Level Flow (MOST IMPORTANT)

User uploads invoice
        ↓
Check file type
        ↓
If PDF → convert to image
Else → read image directly
        ↓
Preprocess image (OpenCV)
        ↓
Detect QR (pyzbar)
        ↓
Validate QR pattern
        ↓
Store data in MySQL
        ↓
Return response


## 5. Folder Structure

invoice_qr_project/
│
├── app/
│   ├── main.py
│   ├── file_handler.py
│   ├── qr_reader.py
│   ├── qr_validator.py
│   ├── database.py
│
├── requirements.txt
└── README.md


## 6. CORE PSEUDOCODE

 STEP 1: API ENTRY POINT

FUNCTION upload_invoice(file):

    file_type = detect_file_type(file)

    IF file_type == PDF:
        image = convert_pdf_to_image(file)

    ELSE IF file_type == PNG or JPEG:
        image = load_image(file)

    qr_text = extract_qr_from_image(image)

    IF qr_text is NULL:
        RETURN "QR not found"

    is_valid = validate_qr_pattern(qr_text)

    save_result_to_database(qr_text, is_valid)

    RETURN response


## 7. LIBRARY-WISE PSEUDOCODE 

pdf2image – PDF → Image (ONLY THIS)

IF file type == PDF:
    Convert first page of PDF into image
    Save image temporarily
ELSE:
    Skip this step

Actual concept

Convert only first page
Do NOT loop all pages (waste of time)
That’s all pdf2image does.


## 8. Pillow (PIL) – Image Loader (PNG / JPG / PDF image)

Load image file using Pillow
Convert image to RGB format (safe default)
Convert Pillow image to array (for OpenCV)

Why Pillow?

It safely handles PNG, JPG, JPEG
OpenCV sometimes fails on formats directly
That’s it. Nothing more.


## 9. OpenCV – Image Preprocessing (MINIMAL)

Convert image to grayscale
Resize image if too large


## 10. pyzbar – QR Detection (CORE LOGIC)

Send processed image to pyzbar
Get list of QR codes found

IF no QR found:
    Return "QR not found"

Take first QR code

Decode QR text


## 11. QR Validation (PATTERN BASED – NO GOV API)

✅ Pattern-based validation

Example logic:

IF QR text contains:
    - GSTIN pattern
    - Invoice number pattern
    - Date pattern
THEN:
    QR is VALID
ELSE:
    QR is INVALID


## 12. Final Response

Return JSON:
{
  "status": "success / failed",
  "qr_found": true / false,
  "qr_valid": true / false,
  "qr_data": decoded_text
}