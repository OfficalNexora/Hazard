import sqlite3
import json

DB_PATH = "system.db"

def query_contacts():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gsm_contacts")
        rows = cursor.fetchall()
        print(f"Total contacts: {len(rows)}")
        for row in rows:
            print(dict(row))
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query_contacts()
