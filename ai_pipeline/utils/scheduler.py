"""scheduler — Attente jusqu'à une date planifiée avec compte à rebours."""

import time
from datetime import datetime, timezone

from utils.logger import logger


def wait_until(iso_date: str) -> None:
    """Bloque jusqu'à la date ISO donnée. Affiche un compte à rebours.

    Args:
        iso_date: Format ISO 8601, ex: '2026-05-25T09:00:00'

    Raise:
        ValueError: si la date est dans le passé ou mal formatée.
    """
    try:
        target = datetime.fromisoformat(iso_date)
        if target.tzinfo is None:
            # Si pas de fuseau horaire, on suppose UTC
            target = target.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Format date invalide '{iso_date}'. Attendu: YYYY-MM-DDTHH:MM:SS") from e

    now = datetime.now(timezone.utc)
    delta = (target - now).total_seconds()

    if delta <= 0:
        raise ValueError(
            f"La date planifiée est dans le passé "
            f"({iso_date}, {int(abs(delta))}s de retard)"
        )

    days = int(delta // 86400)
    hours = int((delta % 86400) // 3600)
    minutes = int((delta % 3600) // 60)
    seconds = int(delta % 60)

    print(f"\n⏳ Envoi planifié dans {days}d {hours:02d}h {minutes:02d}m {seconds:02d}s")
    logger.info(f"Planifié: attente de {delta:.0f}s jusqu'à {iso_date}")

    _countdown(delta)


def _countdown(total_seconds: float) -> None:
    """Boucle d'attente avec affichage toutes les 5s puis final 5s seconde par seconde."""
    remaining = total_seconds
    interval = min(5.0, remaining / 2)

    while remaining > 5:
        time.sleep(interval)
        remaining -= interval
        mins, secs = divmod(int(remaining), 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        if days > 0:
            print(f"  ⏳ {days}j {hours:02d}h {mins:02d}m {secs:02d}s restantes")
        elif hours > 0:
            print(f"  ⏳ {hours:02d}h {mins:02d}m {secs:02d}s restantes")
        else:
            print(f"  ⏳ {mins:02d}m {secs:02d}s restantes")
        interval = min(5.0, remaining / 2)

    # Dernières 5 secondes : tick toutes les secondes
    for s in range(int(remaining), 0, -1):
        time.sleep(1)
        print(f"  ⏳ {s}s...")

    print("  ▶ Envoi en cours...\n")
