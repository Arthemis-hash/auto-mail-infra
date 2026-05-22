"""Sécurité — validation impérative, audit, rate-limit, protection anti-suppression.

Toute opération externe (email, LinkedIn) est :
  - Bloquée jusqu'à confirmation explicite du user
  - Limitée en fréquence (rate-limit)
  - Journalisée dans SQLite
  - Restreinte aux actions SEND uniquement (pas de DELETE/UPDATE)
"""

import time
from datetime import datetime, timedelta

from utils.logger import logger
from utils.db import init as db_init, add_history, get_config, set_config

# Opérations DANGEREUSES interdites — le code ne doit JAMAIS les appeler
FORBIDDEN_OPERATIONS = [
    "delete", "trash", "remove", "destroy",
    "update", "patch", "put",
    "ban", "block", "report",
]

# Actions autorisées par plateforme
ALLOWED_ACTIONS = {
    "email": ["send"],
    "linkedin": ["post"],
}

# Rate-limit : nombre de secondes minimum entre deux envois sur une même plateforme
RATE_LIMIT_SECONDS = 30


def require_confirmation(prompt: str, context: dict | None = None) -> bool:
    """Bloque jusqu'à ce que l'utilisateur tape 'o' ou 'oui' ou 'yes'.
    N'accepte PAS de valeur par défaut — le user doit répondre explicitement.
    """
    if context:
        print(f"\n── Contexte ──────────────────────────────")
        for k, v in context.items():
            if v:
                print(f"  {k}: {v}")
        print("───────────────────────────────────────────\n")

    while True:
        resp = input(f"{prompt} (o/N): ").strip().lower()
        if resp in ("o", "oui", "yes", "y"):
            return True
        if resp in ("n", "non", "no", ""):
            return False
        print("  Réponse invalide. Tape 'o' pour confirmer, 'n' pour annuler.")


def validate_operation(platform: str, action: str, content: dict, metadata: dict) -> None:
    """Valide qu'une opération est autorisée avant exécution.

    Lève une SecurityError si l'opération est interdite.
    """
    action_lower = action.lower()

    # Vérifier que ce n'est pas une action destructive
    for forbidden in FORBIDDEN_OPERATIONS:
        if forbidden in action_lower:
            _reject(
                f"Opération interdite: '{action}' "
                f"(contient le mot-clé dangereux '{forbidden}')"
            )

    # Vérifier que l'action est autorisée pour cette plateforme
    allowed = ALLOWED_ACTIONS.get(platform.lower(), [])
    if allowed and action_lower not in allowed:
        _reject(
            f"Action '{action}' non autorisée pour '{platform}'. "
            f"Actions permises: {', '.join(allowed)}"
        )

    # Vérifier rate-limit
    _check_rate_limit(platform)

    # Vérifier DRY_RUN — ne pas envoyer si c'est le cas
    from utils.config import is_dry_run
    if is_dry_run:
        logger.info(f"[DRY RUN] Opération '{action}' sur {platform} — non exécutée")
        return

    logger.info(f"Opération validée: {action} sur {platform}")


def audit(operation: str, platform: str, status: str,
          note_path: str | None = None, details: dict | None = None) -> None:
    """Journalise une opération dans SQLite."""
    db_init()
    add_history(
        note_path or "unknown",
        platform,
        status,
        {"operation": operation, **(details or {})},
    )
    logger.info(f"AUDIT: {operation}/{platform} → {status}")


def _reject(msg: str):
    """Lève une exception de sécurité."""
    logger.error(f"SÉCURITÉ: {msg}")
    raise SecurityError(msg)


def _check_rate_limit(platform: str):
    """Vérifie qu'on n'envoie pas trop vite sur la même plateforme."""
    db_init()
    last_key = f"last_{platform}_at"
    last_time = get_config(last_key)
    if last_time:
        elapsed = time.time() - float(last_time)
        if elapsed < RATE_LIMIT_SECONDS:
            remaining = int(RATE_LIMIT_SECONDS - elapsed)
            _reject(
                f"Rate-limit: attendre {remaining}s avant un nouvel envoi sur {platform}"
            )
    set_config(last_key, str(time.time()))


class SecurityError(Exception):
    """Exception levée pour toute violation de sécurité."""
    pass
