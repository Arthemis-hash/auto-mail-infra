#!/usr/bin/env python3
"""Assistant interactif de configuration du pipeline.

Usage:
    python scripts/setup.py

Configure : Gmail (App Password ou OAuth), LinkedIn (token direct depuis Dev Portal).
"""

import sys
import os
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import init, get_history


def _banner():
    print("=" * 60)
    print("  AI Pipeline — Assistant de configuration")
    print("  social-mails-pipeline")
    print("=" * 60)


def _load_env() -> dict:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    return {k: os.getenv(k, "") for k in [
        "GMAIL_USER", "GMAIL_APP_PASSWORD",
        "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET",
        "LINKEDIN_TOKEN", "LINKEDIN_PERSON_ID",
        "DRY_RUN",
    ]}


def _save_env(key: str, value: str):
    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines = []
    found = False
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    with env_path.open("w") as f:
        for line in lines:
            if line.strip().startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line + "\n")
        if not found:
            f.write(f"{key}={value}\n")
    print(f"  ✓ {key} sauvegardé dans .env")


def _prompt(label: str, secret: bool = False, hint: str = "") -> str:
    while True:
        val = input(f"  {label} : ").strip()
        if not val:
            print("  ❌ Ce champ est requis.")
            continue
        if "your_" in val or "xxxx" in val or "AQX" in val[:4] == val:
            print(f"  ❌ Valeur par défaut. Remplace par ta vraie valeur.{hint}")
            continue
        return val


# ── Gmail ─────────────────────────────────────────────────────────────

def configure_gmail(env: dict):
    print("\n── Gmail ────────────────────────────────────────────")

    user = env.get("GMAIL_USER")
    if not user or "your_" in user or "you@" in user:
        user = _prompt("Adresse Gmail", hint=" (ex: moncompte@gmail.com)")
    _save_env("GMAIL_USER", user)

    print("\n  Méthode d'envoi :")
    print("  1) App Password")
    print("     → https://myaccount.google.com/apppasswords")
    print("  2) OAuth 2.0 (recommandé)")
    print("     → https://console.cloud.google.com (Gmail API)")
    choice = input("\n  Choix [1/2] (défaut: 1) : ").strip() or "1"

    if choice == "2":
        _configure_gmail_oauth(env)
    else:
        _configure_gmail_app_password(env)


def _configure_gmail_app_password(env: dict):
    print("\n  ℹ️  Pour créer un App Password :")
    print("     1. Active la validation 2 étapes")
    print("     2. https://myaccount.google.com/apppasswords")
    print("     3. Génére un mot de passe pour 'AI Pipeline'")
    print()

    pw = env.get("GMAIL_APP_PASSWORD")
    if pw and "xxxx" not in pw:
        print(f"  ✓ Déjà configuré ({pw[:4]}...{pw[-4:]})")
        return

    pw = _prompt("App Password (16 caractères, format: xxxx-xxxx-xxxx-xxxx)")
    _save_env("GMAIL_APP_PASSWORD", pw)
    print("  ✅ App Password enregistré")


def _configure_gmail_oauth(env: dict):
    print("\n  ℹ️  Prérequis Google Cloud :")
    print("     1. https://console.cloud.google.com → projet → Gmail API")
    print("     2. Crée un OAuth 2.0 Client ID (type: Desktop app)")
    print("     3. Ajoute http://localhost:8080 comme Redirect URI")
    print()

    cid = env.get("GMAIL_CLIENT_ID")
    if not cid or "xxx" in cid:
        cid = _prompt("Google Client ID",
                      hint=" (finit par .apps.googleusercontent.com)")
        _save_env("GMAIL_CLIENT_ID", cid)

    csec = env.get("GMAIL_CLIENT_SECRET")
    if not csec or "xxx" in csec:
        csec = _prompt("Google Client Secret")
        _save_env("GMAIL_CLIENT_SECRET", csec)

    from utils.auth_gmail import generate_auth_url, exchange_code, test_token, save_token
    import time

    url = generate_auth_url(cid)
    print(f"\n  🔗 Ouvre ce lien dans ton navigateur :")
    print(f"  {url}")
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass

    code = input("\n  Colle le code d'autorisation (paramètre 'code=') : ").strip()
    if not code:
        print("  ❌ Code requis.")
        return

    data = exchange_code(cid, csec, code)
    if not data:
        return

    save_token(platform="gmail", access_token=data["access_token"],
               refresh_token=data.get("refresh_token"),
               expires_at=int(time.time()) + data.get("expires_in", 3600),
               scope="https://www.googleapis.com/auth/gmail.send")
    print("  ✅ Tokens OAuth enregistrés dans SQLite")

    print("\n  🔍 Test du token Gmail...")
    if test_token():
        print("  ✅ Gmail OK")
    else:
        print("  ⚠️  Token enregistré mais test API échoué.")


# ── LinkedIn (token direct depuis Dev Portal) ─────────────────────────

def configure_linkedin(env: dict):
    print("\n── LinkedIn ─────────────────────────────────────────")

    print("  ℹ️  Génère ton token directement dans le Developer Portal :")
    print("     1. Va sur https://developer.linkedin.com/")
    print("     2. OuvRE ta app → onglet Auth")
    print("     3. Dans 'OAuth 2.0 tools' → clique sur Create token")
    print("     4. Coche le scope 'w_member_social' → Generate")
    print("     5. Copie le token généré")
    print()
    print("  ℹ️  Pour le Person ID :")
    print("     Dans le même portail, va sur l'API '/v2/userinfo'")
    print("     ou cherche 'sub' dans les infos de ton profil")
    print()

    token = env.get("LINKEDIN_TOKEN")
    pid = env.get("LINKEDIN_PERSON_ID")

    if token and pid and "AQX" not in token:
        print(f"  ✓ Déjà configuré ({token[:10]}...{token[-6:]})")
        return

    if not token or "AQX" in token:
        token = _prompt("Token LinkedIn (depuis Dev Portal)")
        _save_env("LINKEDIN_TOKEN", token)

    if not pid:
        pid = _prompt("LinkedIn Person ID (le 'sub' du userinfo)")
        _save_env("LINKEDIN_PERSON_ID", pid)

    print("  ✅ LinkedIn configuré")


# ── Statut ───────────────────────────────────────────────────────────

def show_status():
    print("\n── Statut ───────────────────────────────────────────")
    from utils.config import config

    gmail = config.get("GMAIL_APP_PASSWORD")
    gmail_oauth = config.get("GMAIL_CLIENT_ID")
    linkedin_token = config.get("LINKEDIN_TOKEN")
    linkedin_pid = config.get("LINKEDIN_PERSON_ID")
    dr = config.get("DRY_RUN", "true")

    if gmail and "xxxx" not in gmail:
        print(f"  Gmail App Pass: ✅ OK ({gmail[:4]}...{gmail[-4:]})")
    elif gmail_oauth and "xxx" not in gmail_oauth:
        from utils.auth_gmail import is_configured
        if is_configured():
            print("  Gmail OAuth:    ✅ OK (token dans SQLite)")
        else:
            print("  Gmail OAuth:    ⚠️  Client ID OK, token manquant")
    else:
        print("  Gmail:          ❌ Non configuré")

    if linkedin_token and "AQX" not in linkedin_token and linkedin_pid:
        print(f"  LinkedIn:       ✅ OK (token: {linkedin_token[:10]}... | ID: {linkedin_pid})")
    else:
        print("  LinkedIn:       ❌ Non configuré")

    print(f"  DRY_RUN:        {'🔒 ON (sécurisé)' if dr == 'true' else '⚠️  OFF (production)'}")

    hist = get_history(5)
    if hist:
        print(f"\n  Dernières publications :")
        for h in hist:
            print(f"    • {h['published_at']} | {h['platform']:8s} | {h['status']}")
    else:
        print("\n  Aucune publication dans l'historique")


# ── Menu ─────────────────────────────────────────────────────────────

def main():
    _banner()
    init()

    print("\n  Que veux-tu configurer ?")
    print("  1) Gmail (App Password ou OAuth)")
    print("  2) LinkedIn (token depuis Developer Portal)")
    print("  3) Les deux")
    print("  4) Voir le statut")
    choice = input("\n  Choix [1/2/3/4] (défaut: 3) : ").strip() or "3"

    env = _load_env()

    if choice == "1":
        configure_gmail(env)
    elif choice == "2":
        configure_linkedin(env)
    elif choice == "3":
        configure_gmail(env)
        configure_linkedin(env)
    elif choice == "4":
        show_status()
        return

    print()
    show_status()
    print("\n  ✅ Configuration terminée.")


if __name__ == "__main__":
    main()
