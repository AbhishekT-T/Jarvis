import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_memory.db")
MAX_TURNS = 20  # Load up to 20 turns (40 messages) into conversation context


def init_db() -> None:
    """Initializes the SQLite database and creates tables if they do not exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Table for general conversational messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Table for explicitly remembered facts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def load_history() -> list:
    """Loads the last MAX_TURNS * 2 messages from the history table."""
    init_db()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Fetch the most recent messages, then reverse them so they are in chronological order
            cursor.execute(
                "SELECT role, content FROM history ORDER BY id DESC LIMIT ?",
                (MAX_TURNS * 2,)
            )
            rows = cursor.fetchall()
            history = []
            for role, content in reversed(rows):
                history.append({"role": role, "content": content})
            return history
    except sqlite3.Error:
        return []


def append_message(role: str, content: str) -> None:
    """Appends a single message to the conversation history database."""
    init_db()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (role, content) VALUES (?, ?)",
                (role, content)
            )
            conn.commit()
    except sqlite3.Error:
        pass


def clear_history() -> None:
    """Deletes all messages from the history table."""
    init_db()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history")
            conn.commit()
    except sqlite3.Error:
        pass


def add_fact(fact: str) -> int:
    """Saves an explicit fact to the database and returns its row ID."""
    init_db()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO facts (fact) VALUES (?)", (fact,))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error:
        return -1


def get_facts(query: str = None) -> list:
    """Retrieves saved facts. If query is provided, searches via LIKE query.

    Returns:
        list of dict: List containing dicts with keys 'id', 'fact', and 'timestamp'.
    """
    init_db()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            if query:
                cursor.execute(
                    "SELECT id, fact, timestamp FROM facts WHERE fact LIKE ? ORDER BY id DESC",
                    (f"%{query}%",)
                )
            else:
                cursor.execute("SELECT id, fact, timestamp FROM facts ORDER BY id DESC")
            
            rows = cursor.fetchall()
            return [{"id": r[0], "fact": r[1], "timestamp": r[2]} for r in rows]
    except sqlite3.Error:
        return []


def delete_fact(fact_id: int) -> bool:
    """Deletes a saved fact by its row ID. Returns True if a row was deleted, False otherwise."""
    init_db()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


# Automatically initialize the database on import
init_db()
