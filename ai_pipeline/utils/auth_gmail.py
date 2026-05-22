"""Gmail OAuth 2.0 — flow interactif pour utiliser la Gmail API (sans mot de passe)."""

import base64, json, time, webbrowser
from email.message import EmailMessage
from urllib.parse import urlencode
from pathlib import Path

import requests

from utils.db import save_token, get_token
from utils.logger import logger

SCOPE = "https://www.googleapis.com/auth/gmail.send"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def _config_get(key: str) -> str | None:
    from utils.config import config
    val = config.get(key)
    if val and "your_" not in val and "xxxx" not in val:
        return val
    return None


def is_configured() -> bool:
    """Vérifie si un refresh_token Gmail est enregistré dans la DB."""
    tok = get_token("gmail")
    return bool(tok and tok.get("refresh_token"))


def generate_auth_url(client_id: str) -> str:
    """Génère l'URL d'autorisation Google OAuth 2.0."""
    params = {
        "client_id": client_id,
        "redirect_uri": "http://localhost:8080",
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(client_id: str, client_secret: str, code: str) -> dict | None:
    """Échange un code d'autorisation contre des tokens."""
    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8080",
    }, timeout=30)
    data = resp.json()

    if "error" in data:
        print(f"❌ Erreur OAuth: {data.get('error')} — {data.get('error_description', '')}")
        return None

    return data


def authorize_interactive(client_id: str, client_secret: str) -> bool:
    """Lance le flow OAuth 2.0 interactif complet pour Gmail."""
    url = generate_auth_url(client_id)

    print(f"\n🔗 URL d'autorisation Gmail :\n{url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    code = input("Colle le code d'autorisation (paramètre 'code=' dans l'URL) : ").strip()
    if not code:
        print("❌ Code requis.")
        return False

    data = exchange_code(client_id, client_secret, code)
    if not data:
        return False

    import time
    expires_at = int(time.time()) + data.get("expires_in", 3600)
    save_token(
        platform="gmail",
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=expires_at,
        scope=SCOPE,
    )

    print("✅ OAuth Gmail configuré avec succès (refresh token enregistré)")
    return True


def test_token() -> bool:
    """Teste que le token Gmail est valide en appelant l'API."""
    tok = get_token("gmail")
    if not tok:
        print("❌ Aucun token Gmail trouvé.")
        return False

    access = _refresh_access()
    if not access:
        print("❌ Impossible de rafraîchir le token Gmail.")
        return False

    resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        headers={"Authorization": f"Bearer {access}"},
        timeout=10,
    )

    if resp.status_code == 200:
        email = resp.json().get("emailAddress", "inconnu")
        print(f"✅ Token Gmail valide — connecté en tant que {email}")
        return True
    else:
        print(f"❌ Token Gmail invalide: {resp.status_code} {resp.text}")
        return False


def _refresh_access() -> str | None:
    tok = get_token("gmail")
    if not tok or not tok.get("refresh_token"):
        return None

    client_id = _config_get("GMAIL_CLIENT_ID")
    client_secret = _config_get("GMAIL_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    }, timeout=30)
    data = resp.json()

    if "access_token" not in data:
        return None

    save_token(
        platform="gmail",
        access_token=data["access_token"],
        expires_at=int(time.time()) + data.get("expires_in", 3600),
    )
    return data["access_token"]


def send_via_api(sender: str, to: str, subject: str, body_text: str,
                 attachments: list[str] | None = None) -> bool:
    """Envoie un email via la Gmail API REST (OAuth)."""
    access = _refresh_access()
    if not access:
        raise RuntimeError("Aucun token OAuth Gmail valide. Lance setup.py d'abord.")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)

    for filepath in (attachments or []):
        path = Path(filepath)
        if path.is_file():
            data = path.read_bytes()
            msg.add_attachment(data, maintype="application", subtype="octet-stream",
                               filename=path.name)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    def _do_send(token):
        return requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"raw": raw},
            timeout=30,
        )

    resp = _do_send(access)
    if resp.status_code == 401:
        access = _refresh_access()
        if not access:
            raise RuntimeError("Token Gmail expiré et refresh impossible.")
        resp = _do_send(access)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Gmail API error {resp.status_code}: {resp.text}")

    logger.info(f"Email envoyé via Gmail API à {to}")
    return True
