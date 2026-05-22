"""Parsing JSON défensif — gère les réponses LLM avec backticks, texte parasite, etc."""

import json
import re


def extract_json(text: str) -> dict:
    """Extrait un objet JSON depuis une réponse LLM potentiellement sale."""
    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned.strip(), flags=re.MULTILINE)

    # Tente le parse direct
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback : cherche le premier { ... } ou [ ... ] valide
    for match in re.finditer(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned):
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

    raise ValueError(f"Impossible d'extraire du JSON valide depuis la réponse LLM:\n{text[:200]}")
