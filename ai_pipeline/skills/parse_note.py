"""Skill: parse_note — Lit une note Obsidian avec front-matter YAML."""

from pathlib import Path
import yaml

from utils.logger import logger


def parse_note(filepath: str) -> dict:
    """Parse une note Obsidian (YAML front-matter + body markdown)."""
    path = Path(filepath).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Note introuvable: {path}")
    if not path.suffix == ".md":
        raise ValueError(f"Fichier non-markdown: {path}")

    content = path.read_text(encoding="utf-8")
    parts = content.split("---")

    if len(parts) < 3:
        raise ValueError("Front-matter YAML manquant (délimiteurs --- attendus)")

    metadata = yaml.safe_load(parts[1])
    body = "---".join(parts[2:]).strip()  # Rejoindre si le body contient des ---

    status = metadata.get("status", "").lower()
    if status != "approved":
        raise ValueError(f"Note non approuvée (status: '{status}')")

    logger.info(f"Note parsée: {path.name} | platform={metadata.get('platform')}")

    return {
        "metadata": metadata,
        "body": body,
        "source_path": str(path),
    }
