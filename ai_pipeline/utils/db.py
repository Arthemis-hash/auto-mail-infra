"""SQLite — stockage local des tokens OAuth, historique, et configuration réutilisable."""

import sqlite3
import json
import os
import stat
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


def check_database_security() -> dict:
    """Vérifie la sécurité de la base de données.
    
    Retourne un dictionnaire avec les résultats :
    {
        "status": "secure" | "warning" | "danger",
        "db_exists": bool,
        "db_readable": bool,
        "db_world_readable": bool,
        "permissions": str (mode octale),
        "contains_tokens": bool,
        "contains_secrets": bool,
        "size_mb": float,
        "details": [list of findings],
    }
    """
    results = {
        "status": "secure",
        "db_exists": DB_PATH.exists(),
        "db_readable": False,
        "db_world_readable": False,
        "permissions": None,
        "contains_tokens": False,
        "contains_secrets": False,
        "size_mb": 0.0,
        "details": [],
    }
    
    # Vérifier si la DB existe
    if not results["db_exists"]:
        results["details"].append("✅ Base de données non encore créée (OK si première exécution)")
        return results
    
    # Vérifier les permissions d'accès
    try:
        results["db_readable"] = os.access(DB_PATH, os.R_OK)
        if not results["db_readable"]:
            results["status"] = "warning"
            results["details"].append("⚠️ Base de données non lisible (permissions insuffisantes)")
    except Exception as e:
        results["details"].append(f"❌ Erreur lors de la vérification de lecture: {e}")
        results["status"] = "danger"
    
    # Vérifier les permissions fichier (Unix/Linux/macOS)
    try:
        mode = stat.filemode(os.stat(DB_PATH).st_mode)
        mode_octal = oct(os.stat(DB_PATH).st_mode)[-3:]
        results["permissions"] = mode_octal
        
        # Vérifier si le fichier est lisible par d'autres utilisateurs
        file_stat = os.stat(DB_PATH)
        others_can_read = bool(file_stat.st_mode & stat.S_IROTH)
        results["db_world_readable"] = others_can_read
        
        if others_can_read:
            results["status"] = "danger"
            results["details"].append(
                f"🚨 DANGER: La base de données est lisible par d'autres utilisateurs "
                f"(permissions {mode_octal}). Contient des tokens OAuth!"
            )
        else:
            results["details"].append(f"✅ Permissions fichier sécurisées ({mode_octal})")
    except Exception as e:
        results["details"].append(f"⚠️ Impossible de vérifier les permissions: {e}")
    
    # Vérifier la taille du fichier
    try:
        size_bytes = DB_PATH.stat().st_size
        results["size_mb"] = round(size_bytes / (1024 * 1024), 2)
        results["details"].append(f"📊 Taille de la base de données: {results['size_mb']} MB")
    except Exception as e:
        results["details"].append(f"⚠️ Impossible de vérifier la taille: {e}")
    
    # Vérifier le contenu de la DB
    try:
        con = _conn()
        
        # Vérifier la présence de tokens
        token_count = con.execute(
            "SELECT COUNT(*) FROM tokens WHERE access_token IS NOT NULL"
        ).fetchone()[0]
        results["contains_tokens"] = token_count > 0
        
        if token_count > 0:
            results["details"].append(f"🔐 {token_count} token(s) OAuth stocké(s) dans la DB")
            results["status"] = "warning"
        
        # Vérifier la présence de secrets potentiels dans config
        secrets_keywords = ["password", "secret", "key", "token", "credential"]
        secret_count = 0
        
        config_rows = con.execute("SELECT key, value FROM config").fetchall()
        for key, value in config_rows:
            if any(kw in key.lower() for kw in secrets_keywords):
                secret_count += 1
                # Ne pas afficher la valeur réelle!
                results["details"].append(f"🔐 Configuration sensible trouvée: '{key}'")
        
        results["contains_secrets"] = secret_count > 0
        
        # Vérifier la table rapp (envois)
        rapp_count = con.execute("SELECT COUNT(*) FROM rapp").fetchone()[0]
        if rapp_count > 0:
            results["details"].append(f"📧 {rapp_count} envoi(s) enregistré(s) dans la traçabilité")
        
        # Vérifier la table history
        history_count = con.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        if history_count > 0:
            results["details"].append(f"📝 {history_count} événement(s) dans l'historique")
        
        con.close()
        
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            results["details"].append("✅ Tables de la DB non encore créées")
        else:
            results["status"] = "danger"
            results["details"].append(f"❌ Erreur d'accès à la DB: {e}")
    except Exception as e:
        results["status"] = "danger"
        results["details"].append(f"❌ Erreur lors de la vérification du contenu: {e}")
    
    return results


def print_database_security_report():
    """Affiche un rapport formaté de la sécurité de la DB."""
    report = check_database_security()
    
    print("\n" + "=" * 70)
    print("  🔒 VÉRIFICATION DE SÉCURITÉ DE LA BASE DE DONNÉES")
    print("=" * 70)
    
    # Afficher le statut global
    status_emoji = {
        "secure": "✅",
        "warning": "⚠️ ",
        "danger": "🚨",
    }
    status_text = {
        "secure": "Sécurisée",
        "warning": "Attention requise",
        "danger": "Danger!",
    }
    
    print(f"\nStatut: {status_emoji[report['status']]} {status_text[report['status']]}")
    
    # Afficher les détails
    print("\nDétails:")
    for detail in report["details"]:
        print(f"  {detail}")
    
    print("\n" + "=" * 70)
    
    # Recommandations
    if report["status"] == "danger":
        print("\n⚠️  ACTIONS RECOMMANDÉES:")
        if report["db_world_readable"]:
            print("  1. Changez les permissions du fichier:")
            print(f"     chmod 600 {DB_PATH}")
            print("  2. Considérez de supprimer et recréer la DB si compromise")
    elif report["status"] == "warning":
        print("\n💡 SUGGESTIONS:")
        if report["contains_tokens"]:
            print("  - Assurez-vous que pipeline.db est dans .gitignore (✓)")
            print("  - Ne partagez jamais ce fichier")
            print("  - Considérez chiffrer la DB avec cipher de SQLite")
        print("  - Régulez l'accès au fichier (permissions 0600)")
    else:
        print("\n✅ Pas de problèmes de sécurité détectés.")
        print("  - Continuez à protéger le fichier data/pipeline.db")
        print("  - Ne commitez jamais ce fichier dans Git")
    
    print()
    return report


# ── Tokens ────────────────────────────────────────────────────────────[...]

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


# ── History ─────────────────────────────────────────────────────────────[...]

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
