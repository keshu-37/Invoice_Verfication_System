import mysql.connector
from mysql.connector import Error
from backend.models import InvoiceRecord


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Keshav@1518",
    "database": "invoice_db"
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)



# DUPLICATE CHECK (DATABASE)

def is_duplicate_invoice_db(invoice_hash: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT id FROM invoices
            WHERE invoice_hash = %s
            LIMIT 1
        """

        cursor.execute(query, (invoice_hash,))
        return cursor.fetchone() is not None

    except Error as e:
        print("❌ DB duplicate check error:", e)
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



# SAVE INVOICE

def save_invoice(record: InvoiceRecord):
    try:
        print(">>> Saving invoice to database...")

        conn = get_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO invoices
            (file_name, file_type, invoice_hash, qr_data, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            record.file_name,
            record.file_type,
            record.invoice_hash,
            record.qr_data,
            record.created_at
        )

        cursor.execute(query, values)
        conn.commit()

        print(">>> Insert successful | ID:", cursor.lastrowid)

    except mysql.connector.IntegrityError as e:
        #  Duplicate invoice_hash (UNIQUE constraint)
        if e.errno == 1062:
            print("⚠️ Duplicate invoice detected (DB level) — insert skipped")
        else:
            print("❌ Database integrity error:", e)

    except Error as e:
        print("❌ Database insert error:", e)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
