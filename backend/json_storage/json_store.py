import json
from pathlib import Path


BASE_PATH = Path(__file__).parent
VERIFIED_FILE = BASE_PATH / "verified.json"
NON_VERIFIED_FILE = BASE_PATH / "non_verified.json"


# -------------------------------------------------
# INTERNAL: SAFE JSON LOAD
# -------------------------------------------------
def _safe_load_json(file_path: Path) -> list:
    """
    Safely load JSON array from file.
    Handles:
    - missing file
    - empty file
    - corrupted JSON
    """
    if not file_path.exists():
        return []

    try:
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return json.loads(content)
    except Exception:
        print(f"⚠️ Corrupted or empty JSON detected, resetting: {file_path.name}")
        return []


# -------------------------------------------------
# SAVE INVOICE RECORD
# -------------------------------------------------
def save_invoice_to_json(record: dict):
    try:
        status = record.get("validation_result", {}).get("status", "UNKNOWN")

        file_path = (
            VERIFIED_FILE
            if status == "GOVERNMENT_VERIFIED"
            else NON_VERIFIED_FILE
        )

        BASE_PATH.mkdir(parents=True, exist_ok=True)

        data = _safe_load_json(file_path)
        data.append(record)

        file_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

        print("✅ JSON appended:", file_path)

    except Exception as e:
        print("⚠️ JSON save failed (ignored):", e)


# -------------------------------------------------
# DUPLICATE CHECK (JSON)
# -------------------------------------------------
def is_duplicate_invoice_json(invoice_hash: str) -> bool:
    records = _safe_load_json(VERIFIED_FILE)

    for record in records:
        if record.get("invoice_hash") == invoice_hash:
            return True

    return False

