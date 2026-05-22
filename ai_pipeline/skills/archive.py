"""Skill: archive — Déplace la note traitée vers archive/."""

import shutil
from pathlib import Path

from utils.logger import logger

_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "archive"


def archive(filepath: str) -> str:
    """Archive la note source. Retourne le chemin de destination."""
    _ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    src = Path(filepath).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Fichier à archiver introuvable: {src}")

    dest = _ARCHIVE_DIR / src.name

    # Éviter l'écrasement silencieux
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        counter = 1
        while dest.exists():
            dest = _ARCHIVE_DIR / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.move(str(src), str(dest))
    logger.info(f"Archivé: {src.name} -> {dest}")
    return str(dest)
