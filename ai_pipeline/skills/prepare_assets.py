"""Skill: prepare_assets — Vérifie l'existence des pièces jointes référencées."""

from pathlib import Path

from utils.logger import logger


def prepare_assets(data: dict) -> dict:
    """Vérifie les fichiers attachés listés dans le front-matter."""
    raw_paths = data["metadata"].get("attachments", [])
    if not raw_paths:
        return {"valid": [], "missing": []}

    valid, missing = [], []

    for p in raw_paths:
        path = Path(p).resolve()
        if path.is_file():
            valid.append(str(path))
        else:
            missing.append(str(path))

    if missing:
        logger.warning(f"Assets manquants: {missing}")
    if valid:
        logger.info(f"Assets trouvés: {len(valid)}")

    return {"valid": valid, "missing": missing}
