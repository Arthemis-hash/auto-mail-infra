"""Validation centralisée des métadata et champs utilisateur.

Valide avant recap pour garantir que tout est correct AVANT
de demander la confirmation utilisateur.
"""

import re
from datetime import datetime, timezone, timedelta

from utils.config import config


SCHEDULE_MAX_DAYS = 30


def validate_metadata(metadata: dict) -> list[str]:
    """Valide tous les champs du front-matter YAML.
    Retourne une liste d'erreurs (vide si tout est OK).
    """
    errors = []

    # Platform
    platform = metadata.get("platform", "").lower()
    if platform not in ("email", "linkedin"):
        errors.append(f"Plateforme '{platform}' non supportée (email ou linkedin)")

    # Destinataire (requis pour email)
    if platform == "email":
        recipient = metadata.get("destinataire", "")
        err = validate_recipient(recipient)
        if err:
            errors.append(err)

    # Sender (alias Gmail)
    sender = metadata.get("sender")
    if sender:
        err = validate_sender(sender)
        if err:
            errors.append(err)

    # Schedule
    schedule = metadata.get("schedule_at")
    if schedule:
        err = validate_schedule(schedule)
        if err:
            errors.append(err)

    return errors


def validate_recipient(recipient: str) -> str | None:
    """Valide le format d'un email destinataire."""
    if not recipient or not recipient.strip():
        return "Champ 'destinataire' manquant"
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, recipient.strip()):
        return f"Format email invalide pour 'destinataire': {recipient}"
    return None


def validate_sender(sender: str) -> str | None:
    """Valide que l'expéditeur est un alias autorisé."""
    if not sender or not sender.strip():
        return None  # Optionnel, GMAIL_USER sera utilisé

    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, sender.strip()):
        return f"Format email invalide pour 'sender': {sender}"

    whitelist_raw = config.get("SENDERS_WHITELIST", "")
    if whitelist_raw:
        whitelist = [a.strip().lower() for a in whitelist_raw.split(",") if a.strip()]
        if sender.strip().lower() not in whitelist:
            allowed = ", ".join(whitelist)
            return (
                f"Expéditeur '{sender}' non autorisé. "
                f"Expéditeurs autorisés: {allowed}"
            )

    return None


def validate_schedule(schedule_at: str) -> str | None:
    """Valide la date de planification (futur, max 30 jours)."""
    if not schedule_at or not schedule_at.strip():
        return None

    try:
        target = datetime.fromisoformat(schedule_at.strip())
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return (
            f"Format date invalide pour 'schedule_at': '{schedule_at}'. "
            f"Format attendu: YYYY-MM-DDTHH:MM:SS (ex: 2026-05-25T09:00:00)"
        )

    now = datetime.now(timezone.utc)
    delta = (target - now).total_seconds()

    if delta <= 0:
        return (
            f"La date de planification est dans le passé: {schedule_at}. "
            f"Veuillez choisir une date future."
        )

    max_delta = timedelta(days=SCHEDULE_MAX_DAYS).total_seconds()
    if delta > max_delta:
        return (
            f"La date de planification dépasse {SCHEDULE_MAX_DAYS} jours: {schedule_at}. "
            f"Maximum autorisé: dans {SCHEDULE_MAX_DAYS} jours."
        )

    return None
