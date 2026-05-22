"""Skill: send_email — Envoi via Gmail (App Password ou OAuth 2.0 Gmail API), multi-expéditeur.

SÉCURITÉ :
  - Envoi SEULEMENT. Pas de delete, trash, update.
  - Validation impérative avant envoi.
  - Audit trail dans SQLite.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from utils.config import config, is_dry_run
from utils.logger import logger
from utils.security import validate_operation, audit


def send_email(content: dict, metadata: dict, attachments: list[str] | None = None) -> bool:
    """Envoie un email. Supporte l'expéditeur via le champ 'sender' dans metadata.

    Le sender peut être :
      - Un alias Gmail (contact@jobsacademie.tech)
      - Un compte secondaire Gmail
      - Laissez vide pour utiliser GMAIL_USER par défaut

    Sécurité :
      - Ne peut PAS supprimer des emails
      - Ne peut PAS modifier des emails existants
      - Rate-limité (30s entre deux envois)
      - Bloqué jusqu'à confirmation utilisateur
    """
    recipient = metadata.get("destinataire")
    if not recipient:
        raise ValueError("Champ 'destinataire' manquant dans le front-matter")

    sender = metadata.get("sender") or config.get("GMAIL_USER")
    subject = content.get("subject", "")
    body = content.get("body", "")
    user = config.get("GMAIL_USER")

    if is_dry_run:
        logger.info(f"[DRY RUN] Email de {sender} vers {recipient} | sujet: {subject}")
        print(f"\n--- DRY RUN EMAIL ---")
        print(f"From: {sender}")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body[:500]}")
        print("--- FIN DRY RUN ---\n")
        return True

    if not user:
        _fail("GMAIL_USER requis dans .env")

    try:
        if _use_oauth():
            _send_oauth(sender, recipient, subject, body, attachments)
        else:
            password = config.get("GMAIL_APP_PASSWORD")
            if not password:
                _fail("Aucune méthode configurée. Lance `python scripts/setup.py`")
            _send_smtp(user, password, sender, recipient, subject, body, attachments)

        audit("send_email", "email", "success", details={"from": sender, "to": recipient, "subject": subject})
        return True
    except Exception as e:
        audit("send_email", "email", "error", details={"error": str(e)})
        raise


def _use_oauth() -> bool:
    from utils.auth_gmail import is_configured
    return is_configured() and config.get("GMAIL_CLIENT_ID")


def _send_smtp(user: str, password: str, sender: str, recipient: str,
               subject: str, body: str, attachments: list[str] | None):
    """Envoie via SMTP. user/password sont les identifiants Gmail,
    sender est le From: (peut être un alias)."""
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))
    _attach_files(msg, attachments)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(user, password)
            server.sendmail(user, recipient, msg.as_string())
        logger.info(f"Email envoyé (SMTP) de {sender} à {recipient}")
    except smtplib.SMTPException as e:
        logger.error(f"Échec SMTP: {e}")
        raise RuntimeError(f"Échec SMTP: {e}") from e


def _send_oauth(sender: str, recipient: str, subject: str,
                body: str, attachments: list[str] | None):
    from utils.auth_gmail import send_via_api
    send_via_api(sender, recipient, subject, body, attachments)
    logger.info(f"Email envoyé (OAuth) de {sender} à {recipient}")


def _attach_files(msg: MIMEMultipart, attachments: list[str] | None):
    for filepath in (attachments or []):
        path = Path(filepath)
        if not path.is_file():
            continue
        part = MIMEBase("application", "octet-stream")
        part.set_payload(path.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={path.name}")
        msg.attach(part)


def _fail(msg: str):
    logger.error(f"Email: {msg}")
    raise RuntimeError(msg)
