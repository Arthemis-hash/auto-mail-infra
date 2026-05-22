"""LinkedIn OAuth 2.0 — flow interactif pour obtenir token + Person ID."""

import webbrowser
from urllib.parse import urlencode

import requests

from utils.db import save_token, get_token, set_config, get_config
from utils.logger import logger

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "openid profile email w_member_social"


def is_configured() -> bool:
    """Vérifie si un token LinkedIn est enregistré dans la DB."""
    tok = get_token("linkedin")
    return bool(tok and tok.get("access_token"))


def generate_auth_url(client_id: str, redirect_uri: str = "http://localhost:3000") -> str:
    """Génère l'URL d'autorisation LinkedIn OAuth 2.0."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": "social_mails_pipeline",
        "scope": SCOPES,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(client_id: str, client_secret: str, code: str,
                  redirect_uri: str = "http://localhost:3000") -> dict | None:
    """Échange un code d'autorisation contre un token LinkedIn."""
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }, timeout=30)
    data = resp.json()

    if "error" in data:
        print(f"❌ Erreur LinkedIn: {data.get('error')} — {data.get('error_description', '')}")
        return None

    return data


def fetch_person_id(access_token: str) -> str | None:
    """Récupère le Person ID LinkedIn depuis l'API userinfo."""
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    data = resp.json()
    return data.get("sub")


def authorize_interactive(client_id: str, client_secret: str,
                          redirect_uri: str = "http://localhost:3000") -> bool:
    """Lance le flow OAuth 2.0 interactif complet pour LinkedIn.

    Affiche l'URL → récupère le code → échange contre token → récupère Person ID.
    """
    url = generate_auth_url(client_id, redirect_uri)

    print(f"\n🔗 URL d'autorisation LinkedIn :\n{url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    code = input("Colle le code d'autorisation (paramètre 'code=' dans l'URL) : ").strip()
    if not code:
        print("❌ Code requis.")
        return False

    data = exchange_code(client_id, client_secret, code, redirect_uri)
    if not data:
        return False

    access_token = data["access_token"]
    save_token(platform="linkedin", access_token=access_token,
               refresh_token=data.get("refresh_token"),
               scope=SCOPES)

    person_id = fetch_person_id(access_token)
    if person_id:
        set_config("linkedin_person_id", person_id)
        print(f"✅ LinkedIn configuré — Person ID: {person_id}")
    else:
        print("⚠️ Token obtenu mais impossible de récupérer le Person ID.")

    return True


def test_token() -> bool:
    """Teste que le token LinkedIn est valide en appelant l'API userinfo."""
    token, person_id = get_credentials()
    if not token:
        print("❌ Aucun token LinkedIn trouvé.")
        return False

    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )

    if resp.status_code == 200:
        data = resp.json()
        name = f"{data.get('given_name', '')} {data.get('family_name', '')}".strip()
        print(f"✅ Token LinkedIn valide — connecté en tant que {name or data.get('sub', 'inconnu')}")
        return True
    else:
        print(f"❌ Token LinkedIn invalide: {resp.status_code}")
        return False


def get_credentials() -> tuple[str, str] | tuple[None, None]:
    """Retourne (access_token, person_id) depuis la DB."""
    tok = get_token("linkedin")
    if not tok:
        return None, None
    person_id = get_config("linkedin_person_id")
    return tok["access_token"], person_id
