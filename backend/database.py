import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Keshav@1518",   
    "database": "invoice_db"
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def save_invoice(record):
    try:
        print(">>> Saving invoice to database...")

        conn = get_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO invoices (file_name, file_type, qr_data, created_at)
            VALUES (%s, %s, %s, %s)
        """

        values = (
            record.file_name,
            record.file_type,
            record.qr_data,
            record.created_at
        )

        cursor.execute(query, values)

        conn.commit()  # ✅ VERY IMPORTANT

        print(">>> Insert successful | ID:", cursor.lastrowid)

    except Error as e:
        print("❌ Database error:", e)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

