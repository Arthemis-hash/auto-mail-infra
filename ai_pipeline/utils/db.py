"""SQLite — stockage local des tokens OAuth, historique, et configuration réutilisable."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "pipeline.db"


def _conn():
    return sqlite3.connect(str(DB_PATH))


def init():
    con = _conn()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS tokens (
            platform TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at INTEGER,
            scope TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_path TEXT,
            platform TEXT,
            status TEXT,
            metadata TEXT,
            published_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS rapp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'email',
            subject TEXT,
            status TEXT NOT NULL DEFAULT 'sent',
            scheduled_at TEXT,
            sent_at TEXT DEFAULT (datetime('now')),
            note TEXT
        );
    """)
    con.commit()
    con.close()


# ── Tokens ──────────────────────────────────────────────────────────────

def save_token(platform: str, access_token: str, refresh_token: str | None = None,
               expires_at: int | None = None, scope: str = "") -> None:
    init()
    con = _conn()
    con.execute("""
        INSERT INTO tokens (platform, access_token, refresh_token, expires_at, scope)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(platform) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=COALESCE(excluded.refresh_token, refresh_token),
            expires_at=excluded.expires_at,
            scope=excluded.scope
    """, (platform, access_token, refresh_token, expires_at, scope))
    con.commit()
    con.close()


def get_token(platform: str) -> dict | None:
    init()
    con = _conn()
    row = con.execute("SELECT * FROM tokens WHERE platform = ?", (platform,)).fetchone()
    con.close()
    if not row:
        return None
    return {
        "platform": row[0],
        "access_token": row[1],
        "refresh_token": row[2],
        "expires_at": row[3],
        "scope": row[4],
    }


def delete_token(platform: str) -> None:
    init()
    con = _conn()
    con.execute("DELETE FROM tokens WHERE platform = ?", (platform,))
    con.commit()
    con.close()


# ── History ─────────────────────────────────────────────────────────────

def add_history(note_path: str, platform: str, status: str, metadata: dict | None = None) -> int:
    init()
    con = _conn()
    cur = con.execute(
        "INSERT INTO history (note_path, platform, status, metadata) VALUES (?, ?, ?, ?)",
        (note_path, platform, status, json.dumps(metadata or {}, ensure_ascii=False)),
    )
    con.commit()
    con.close()
    return cur.lastrowid


def get_history(limit: int = 20) -> list[dict]:
    init()
    con = _conn()
    rows = con.execute(
        "SELECT * FROM history ORDER BY published_at DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return [
        {
            "id": r[0],
            "note_path": r[1],
            "platform": r[2],
            "status": r[3],
            "metadata": json.loads(r[4] or "{}"),
            "published_at": r[5],
        }
        for r in rows
    ]


# ── Config key/value ────────────────────────────────────────────────────

def set_config(key: str, value: str) -> None:
    init()
    con = _conn()
    con.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    con.commit()
    con.close()


def get_config(key: str, default: str | None = None) -> str | None:
    init()
    con = _conn()
    row = con.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    con.close()
    return row[0] if row else default


# ── Rapp (traçabilité des envois) ──────────────────────────────

def add_rapp(sender: str, recipient: str, platform: str = "email",
             subject: str = "", status: str = "sent",
             scheduled_at: str = "", note: str = "") -> int:
    init()
    con = _conn()
    cur = con.execute(
        "INSERT INTO rapp (sender, recipient, platform, subject, status, scheduled_at, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sender, recipient, platform, subject, status, scheduled_at or None, note),
    )
    con.commit()
    con.close()
    return cur.lastrowid


def get_rapp(limit: int = 20) -> list[dict]:
    init()
    con = _conn()
    rows = con.execute(
        "SELECT * FROM rapp ORDER BY sent_at DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return [
        {
            "id": r[0],
            "sender": r[1],
            "recipient": r[2],
            "platform": r[3],
            "subject": r[4],
            "status": r[5],
            "scheduled_at": r[6],
            "sent_at": r[7],
            "note": r[8],
        }
        for r in rows
    ]


def recap_rapp(limit: int = 5) -> str:
    """Retourne un résumé lisible des derniers envois."""
    rows = get_rapp(limit)
    if not rows:
        return "Aucun envoi enregistré."
    lines = ["📋 **Rapport des derniers envois :**"]
    for r in rows:
        lines.append(
            f"  #{r['id']} | {r['sender']} → {r['recipient']} | "
            f"{r['subject'] or 'sans sujet'} | {r['status']} | {r['sent_at']}"
        )
    return "\n".join(lines)
