from datetime import datetime


class InvoiceRecord:
    def __init__(
        self,
        file_name: str,
        file_type: str,
        invoice_hash: str,
        qr_data: str | None = None,
        created_at: datetime | None = None
    ):
        self.file_name = file_name
        self.file_type = file_type
        self.invoice_hash = invoice_hash  # 🔑 UNIQUE invoice fingerprint
        self.qr_data = qr_data
        self.created_at = created_at or datetime.now()
