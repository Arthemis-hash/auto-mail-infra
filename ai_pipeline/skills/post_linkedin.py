"""Skill: post_linkedin — Publication via LinkedIn API (token depuis .env).

SÉCURITÉ :
  - Post SEULEMENT. Pas de delete, update, trash.
  - Validation impérative avant envoi.
  - Audit trail dans SQLite.
"""

import requests

from utils.config import config, is_dry_run
from utils.logger import logger
from utils.security import validate_operation, audit, require_confirmation


def post_linkedin(content: dict) -> bool:
    """Publie un post LinkedIn via l'API REST.

    Token LinkedIn généré depuis Developer Portal (create token).
    """
    body_text = content.get("body", "")
    hashtags = content.get("hashtags", [])
    if hashtags:
        body_text += "\n\n" + " ".join(f"#{h}" for h in hashtags)

    if is_dry_run:
        logger.info("[DRY RUN] Post LinkedIn")
        print(f"\n--- DRY RUN LINKEDIN ---")
        print(f"Post:\n{body_text[:500]}")
        print("--- FIN DRY RUN ---\n")
        return True

    if not require_confirmation(
        "Confirmer la publication sur LinkedIn ?",
        {"Aperçu": body_text[:200] + "..." if len(body_text) > 200 else body_text},
    ):
        audit("post_linkedin", "linkedin", "cancelled", details={"preview": body_text[:100]})
        print("Publication annulée.")
        return False

    token, person_id = _get_credentials()

    payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": body_text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Post LinkedIn publié")
        audit("post_linkedin", "linkedin", "success", details={"preview": body_text[:100]})
        return True
    except requests.RequestException as e:
        audit("post_linkedin", "linkedin", "error", details={"error": str(e)})
        logger.error(f"Échec LinkedIn: {e}")
        raise RuntimeError(f"Échec LinkedIn API: {e}") from e


def _get_credentials() -> tuple[str, str]:
    token = config.get("LINKEDIN_TOKEN")
    pid = config.get("LINKEDIN_PERSON_ID")
    if not token or not pid:
        raise ValueError("LINKEDIN_TOKEN et LINKEDIN_PERSON_ID requis dans .env")
    return token, pid
