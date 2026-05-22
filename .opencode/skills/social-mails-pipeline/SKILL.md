---
name: social-mails-pipeline
description: Pipeline de publication automatisée de notes Obsidian vers Email/LinkedIn. Parse, génère, valide, envoie et archive via OpenCode (pas d'API LLM externe). OAuth 2.0, SQLite, sécurité intégrée.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: content-publishing
---

## What I do
- Publier une note Obsidian vers Email ou LinkedIn
- OpenCode = seul LLM — pas d'API Anthropic/OpenAI externe
- Gmail : App Password ou OAuth 2.0
- LinkedIn : token direct depuis Developer Portal
- Multi-expéditeur : alias Gmail (contact@, straeton@, etc.)
- Planification : envoi programmé à date fixe
- Table `rapp` : traçabilité de toutes les boîtes utilisées
- Sécurité : validation amont, recap bloquant, whitelist, rate-limit

## Setup initial
```bash
cd ai_pipeline
pip install -r requirements.txt
python scripts/setup.py
```

## Usage workflow
1. Note `.md` avec front-matter YAML :
   ```yaml
   ---
   status: approved
   platform: email              # ou linkedin
   destinataire: @              # requis pour email
   sender: contact@domaine.tech # optionnel — alias Gmail
   tone: professionnel
   attachments: []
   schedule_at: "2026-05-25T09:00:00"  # optionnel — planification
   ---
   ```
2. Étapes : parse → validate_metadata → build_prompt → [OpenCode génère] → save_result → build_prompt validation → [OpenCode valide] → save_result → recap_and_confirm → wait_until (si planifié) → dispatch → archive → log rapp

## Sécurité — Mesures strictes

### Recap + confirmation bloquante
AVANT tout envoi, le pipeline affiche un récapitulatif complet :
```
Plateforme, De, À, Sujet, Planifié le, Pièces jointes, Mode
Aperçu du body
```
L'utilisateur doit taper `o` / `oui` / `yes` explicitement pour débloquer l'envoi.
Pas de valeur par défaut — réponse vide = annulation.

### Validation des métadonnées (`utils/validate.py`)
- `destinataire` : format email valide (regex)
- `sender` : format email valide + whitelist (`SENDERS_WHITELIST` dans .env)
- `schedule_at` : format ISO 8601, pas dans le passé, max 30 jours
- `platform` : email ou linkedin uniquement

### Liste blanche des expéditeurs
Tous les alias doivent être déclarés dans `.env` :
```
SENDERS_WHITELIST=sami@mail.com,contact@domaine.tech,autre@domaine.tech
```

### Rate-limit
30s minimum entre deux envois sur la même plateforme.

### Opérations interdites
DELETE / TRASH / REMOVE / UPDATE / PATCH / PUT / BAN / BLOCK / REPORT.
Toute tentative lève une `SecurityError` et est journalisée.

### Audit trail
Chaque étape est tracée dans SQLite (table `history`).

### DRY_RUN
`DRY_RUN=true` par défaut. L'envoi réel nécessite de passer à `false`.

## Multi-expéditeur (alias Gmail)
Ajoute `sender: contact@jobsacademie.tech` dans le front-matter.
Si absent, utilise `GMAIL_USER` (.env).

## Planification
Ajoute `schedule_at: "2026-05-25T09:00:00"` dans le front-matter.
Le pipeline valide que la date est dans le futur (max 30 jours), affiche un compte à rebours, et envoie automatiquement à l'heure dite.

## Table `rapp` (traçabilité)
Stocke sender, recipient, platform, subject, status, scheduled_at, sent_at.
`add_rapp()` / `get_rapp()` / `recap_rapp()` dans `utils/db.py`.

## LinkedIn — Token
→ https://developer.linkedin.com/ → App → Auth → Create token

## Structure
```
ai_pipeline/
├── skills/            # parse, generate, validate, assets, email, linkedin, archive, dispatch
├── utils/             # security.py, db.py, auth_gmail.py, scheduler.py, validate.py, config, json, logger
├── prompts/           # Templates
├── scripts/setup.py   # Assistant config interactif
├── pipeline.py
├── data/pipeline.db   # SQLite (tokens, history, config, rapp)
└── .env.example
```
