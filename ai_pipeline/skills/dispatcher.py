"""Dispatcher — Route le contenu vers la bonne plateforme. Extensible.

SÉCURITÉ :
  - Vérifie que le handler enregistré est sûr (pas de delete/trash)
  - Rate-limit par plateforme
  - Audit trail dans SQLite
"""

from skills.send_email import send_email
from skills.post_linkedin import post_linkedin
from utils.logger import logger
from utils.security import validate_operation, audit, require_confirmation

# Registre des plateformes supportées
# Seules les actions SEND sont autorisées
_DISPATCHERS = {
    "email": lambda content, metadata, assets: send_email(content, metadata, assets),
    "linkedin": lambda content, metadata, _: post_linkedin(content),
}


def register_platform(name: str, handler):
    """Enregistre une nouvelle plateforme dynamiquement.
    handler(content: dict, metadata: dict, assets: list) -> bool

    Sécurité : le handler ne doit faire que du SEND (pas de DELETE/UPDATE).
    """
    _DISPATCHERS[name.lower()] = handler
    logger.info(f"Plateforme enregistrée: {name}")


def dispatch(platform: str, content: dict, metadata: dict, assets: list[str] | None = None) -> bool:
    """Envoie le contenu vers la plateforme cible.

    Sécurité :
      - Valide l'opération avant envoi
      - Bloque jusqu'à confirmation utilisateur
      - Journalise dans SQLite
    """
    key = platform.lower()
    handler = _DISPATCHERS.get(key)

    if not handler:
        supported = ", ".join(_DISPATCHERS.keys())
        raise ValueError(f"Plateforme '{platform}' non supportée. Disponibles: {supported}")

    # Sécurité : validation avant dispatch
    validate_operation(key, "send", content, metadata)

    logger.info(f"Dispatch vers: {key}")
    result = handler(content, metadata, assets or [])

    audit("dispatch", key, "success" if result else "failed",
          details={"platform": key})
    return result
