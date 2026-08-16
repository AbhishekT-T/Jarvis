import os
import sqlite3

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_project", "jarvis_memory.db")

if os.path.exists(DB_FILE):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history;")
            conn.commit()
            print("Successfully wiped JARVIS's conversation history from jarvis_memory.db!")
    except Exception as e:
        print(f"Error wiping database: {e}")
else:
    print(f"Database file not found at {DB_FILE}")
