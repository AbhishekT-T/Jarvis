import os
import sqlite3

import numpy as np
import ollama

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_rag.db")
EMBED_MODEL = "nomic-embed-text"
CHUNK_CHARS = 500
CHUNK_OVERLAP = 50
SUPPORTED_EXTENSIONS = (".txt", ".md", ".py", ".json", ".csv")
PDF_EXTENSION = ".pdf"
SKIP_DIRS = {".venv", ".git", "__pycache__", ".jarvis_backups", "voices"}


def init_db() -> None:
    """Creates the RAG database and tables if they do not exist."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL
            )
        """)
        conn.commit()


def _embed(text: str) -> np.ndarray:
    """Embeds text with a lightweight local Ollama embedding model (CPU)."""
    res = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return np.asarray(res["embedding"], dtype=np.float32)


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_pdf(path: str) -> str | None:
    """Extracts text from a PDF. Returns None if pypdf is unavailable."""
    try:
        import pypdf
    except ImportError:
        return None
    reader = pypdf.PdfReader(path)
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(text)
    return "\n".join(pages)


def _chunk_text(text: str) -> list:
    """Splits text into overlapping chunks for embedding."""
    text = " ".join(text.split())
    if len(text) <= CHUNK_CHARS:
        return [text] if text.strip() else []
    step = CHUNK_CHARS - CHUNK_OVERLAP
    chunks = []
    for i in range(0, len(text), step):
        chunk = text[i : i + CHUNK_CHARS]
        if chunk.strip():
            chunks.append(chunk)
        if i + step >= len(text):
            break
    return chunks


def index_documents(folder_path: str) -> str:
    """Walks a folder (recursively), chunks, embeds, and stores every supported document."""
    folder = os.path.abspath(folder_path)
    if not os.path.isdir(folder):
        return f"Failed: '{folder_path}' is not a directory."

    files = []
    for root, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS or ext == PDF_EXTENSION:
                files.append(os.path.join(root, name))
    files.sort()
    if not files:
        return (
            "No supported files found in that folder. Supported: "
            + ", ".join(SUPPORTED_EXTENSIONS[1:] + (PDF_EXTENSION,))
            + "."
        )

    init_db()
    indexed = 0
    total_chunks = 0
    skipped_pdf = 0
    for path in files:
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == PDF_EXTENSION:
                text = _read_pdf(path)
                if text is None:
                    skipped_pdf += 1
                    continue
            else:
                text = _read_text_file(path)
            chunks = _chunk_text(text)
            if not chunks:
                continue
        except Exception:
            continue

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.execute("INSERT INTO documents (source) VALUES (?)", (path,))
            doc_id = cur.lastrowid
            for chunk in chunks:
                emb = _embed(chunk)
                conn.execute(
                    "INSERT INTO chunks (doc_id, text, embedding) VALUES (?, ?, ?)",
                    (doc_id, chunk, emb.tobytes()),
                )
            conn.commit()
        indexed += 1
        total_chunks += len(chunks)

    if indexed == 0 and skipped_pdf == 0:
        return "No readable content was found in those files."

    msg = f"Indexed {indexed} documents ({total_chunks} chunks) from '{folder_path}' into the local knowledge base."
    if skipped_pdf:
        msg += (
            f" Skipped {skipped_pdf} PDF(s) because 'pypdf' is not installed. "
            f"Run: pip install pypdf"
        )
    return msg


def search_documents(query: str, top_k: int = 5) -> str:
    """Finds the most relevant local-document chunks for a query (cosine similarity)."""
    init_db()
    try:
        top_k = max(1, min(int(top_k), 10))
    except (TypeError, ValueError):
        top_k = 5
    if not query.strip():
        return "Refused: no search query provided."

    try:
        qemb = _embed(query.strip())
    except Exception as e:
        return f"Failed to embed the query (is '{EMBED_MODEL}' pulled?): {e}"

    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT c.text, d.source, c.embedding FROM chunks c JOIN documents d ON c.doc_id = d.id"
        ).fetchall()
    if not rows:
        return "The knowledge base is empty. Use index_documents on a folder first."

    qnorm = float(np.linalg.norm(qemb))
    scored = []
    for text, source, emb_bytes in rows:
        emb = np.frombuffer(emb_bytes, dtype=np.float32)
        denom = qnorm * float(np.linalg.norm(emb))
        if denom == 0.0:
            continue
        sim = float(np.dot(qemb, emb)) / denom
        scored.append((sim, text, source))
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return "No matching content found in the knowledge base."

    lines = [f"Top {top_k} results from your local knowledge base:"]
    for sim, text, source in scored[:top_k]:
        snippet = text if len(text) <= 300 else text[:300] + "..."
        lines.append(f"\n[{sim:.2f}] {source}\n{snippet}")
    return "\n".join(lines)


def clear_index() -> str:
    """Wipes the entire RAG knowledge base."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM chunks")
        conn.execute("DELETE FROM documents")
        conn.commit()
    return "Local knowledge base cleared."


def get_index_stats() -> str:
    """Returns how many documents and chunks are currently indexed."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    return f"Knowledge base: {docs} documents, {chunks} chunks indexed."


init_db()
