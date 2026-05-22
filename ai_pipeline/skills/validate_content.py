"""Skill: validate_content — Construit le prompt de validation pour OpenCode."""

from pathlib import Path
import json

from utils.logger import logger


def build_prompt(content: dict) -> str:
    """Construit le prompt de validation formaté."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "validator.txt"
    template = prompt_path.read_text(encoding="utf-8")

    content_json = json.dumps(content, ensure_ascii=False, indent=2)
    return template.format(content_json=content_json)


def save_result(result: dict) -> dict:
    """Enregistre le résultat de validation produit par OpenCode."""
    approved = result.get("approved", False)
    issues = result.get("issues", [])

    if approved:
        logger.info("Validation OK")
    else:
        logger.warning(f"Validation refusée: {issues}")

    return {"approved": approved, "issues": issues}
