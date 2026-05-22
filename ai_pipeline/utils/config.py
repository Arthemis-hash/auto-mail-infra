"""Configuration centralisée — charge .env depuis la racine du projet."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

OPTIONAL_VARS = {
    "GMAIL_USER": None,
    "GMAIL_APP_PASSWORD": None,
    "GMAIL_CLIENT_ID": None,
    "GMAIL_CLIENT_SECRET": None,
    "LINKEDIN_TOKEN": None,
    "LINKEDIN_PERSON_ID": None,
    "SENDERS_WHITELIST": None,
    "DRY_RUN": "true",
}


def _load() -> dict:
    config = {}
    for var, default in OPTIONAL_VARS.items():
        config[var] = os.getenv(var, default)
    return config


config = _load()
is_dry_run = config.get("DRY_RUN", "true").lower() == "true"
