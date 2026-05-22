"""Skill: generate_content — Construit le prompt pour OpenCode."""

from pathlib import Path
from utils.logger import logger


def build_prompt(data: dict) -> str:
    """Construit et retourne le prompt de génération formaté."""
    platform = data["metadata"].get("platform", "email")
    tone = data["metadata"].get("tone", "professionnel")

    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "generator.txt"
    template = prompt_path.read_text(encoding="utf-8")

    prompt = template.format(platform=platform, tone=tone, body=data["body"])
    logger.info(f"Prompt généré pour {platform}")
    return prompt


def save_result(data: dict, llm_json: dict) -> dict:
    """Enregistre le résultat JSON produit par OpenCode dans le contexte."""
    llm_json.setdefault("platform", data["metadata"].get("platform", "email"))
    logger.info(f"Contenu reçu pour {llm_json['platform']} | sujet: {llm_json.get('subject', 'N/A')}")
    return llm_json
