"""Tiny SQLite-backed JSON document store (no ORM, thread-safe)."""
import json
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from . import config

_lock = threading.RLock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS docs (kind TEXT NOT NULL, id TEXT NOT NULL, created REAL NOT NULL, "
        "body TEXT NOT NULL, PRIMARY KEY (kind, id))"
    )
    return conn


def put(kind: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    with _lock, _conn() as c:
        row = c.execute("SELECT created FROM docs WHERE kind=? AND id=?", (kind, doc_id)).fetchone()
        created = row[0] if row else time.time()
        c.execute(
            "INSERT OR REPLACE INTO docs (kind,id,created,body) VALUES (?,?,?,?)",
            (kind, doc_id, created, json.dumps(doc)),
        )
    return doc


def get(kind: str, doc_id: str) -> Optional[Dict[str, Any]]:
    with _lock, _conn() as c:
        row = c.execute("SELECT body FROM docs WHERE kind=? AND id=?", (kind, doc_id)).fetchone()
    return json.loads(row[0]) if row else None


def list_docs(kind: str, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT body FROM docs WHERE kind=? ORDER BY created DESC", (kind,)).fetchall()
    docs = [json.loads(r[0]) for r in rows]
    if where:
        docs = [d for d in docs if all(d.get(k) == v for k, v in where.items())]
    return docs


def update(kind: str, doc_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    """Atomic read-modify-write merge of top-level fields."""
    with _lock:
        doc = get(kind, doc_id)
        if doc is None:
            return None
        doc.update(fields)
        put(kind, doc_id, doc)
        return doc


def delete(kind: str, doc_id: str) -> None:
    with _lock, _conn() as c:
        c.execute("DELETE FROM docs WHERE kind=? AND id=?", (kind, doc_id))
