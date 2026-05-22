# Worflow Social Mails

Pipeline automatisé de publication de notes Obsidian vers Email et LinkedIn.

- **OpenCode** = seul LLM — aucune dépendance API externe
- **Gmail** : App Password ou OAuth 2.0
- **LinkedIn** : token direct depuis Developer Portal
- **Multi-expéditeur** : support des alias Gmail (`contact@`, `straeton@`, etc.)
- **Planification** : envoi programmé à date fixe avec compte à rebours
- **SQLite** : historique, traçabilité, stockage sécurisé des tokens
- **Sécurité** : whitelist d'expéditeurs, rate-limit, validation bloquante, audit trail

## Structure

```
ai_pipeline/
├── pipeline.py              # Orchestrateur principal
├── skills/                  # Modules métier
│   ├── parse_note.py        # Parsing YAML + body
│   ├── generate_content.py  # Prompt de génération OpenCode
│   ├── validate_content.py  # Prompt de validation OpenCode
│   ├── prepare_assets.py    # Vérification des pièces jointes
│   ├── send_email.py        # Envoi Gmail (SMTP ou OAuth)
│   ├── post_linkedin.py     # Publication LinkedIn
│   ├── dispatcher.py        # Routage vers la plateforme
│   └── archive.py           # Archivage des notes
├── utils/                   # Utilitaires
│   ├── security.py          # Validation, rate-limit, audit
│   ├── db.py                # SQLite (tokens, history, config, rapp)
│   ├── validate.py          # Validation des métadonnées
│   ├── scheduler.py         # Planification avec countdown
│   ├── auth_gmail.py        # OAuth 2.0 Gmail API
│   ├── auth_linkedin.py     # OAuth 2.0 LinkedIn
│   ├── config.py            # Configuration (.env)
│   └── logger.py            # Logging
├── prompts/                 # Templates de prompts OpenCode
│   ├── generator.txt
│   └── validator.txt
├── scripts/
│   └── setup.py             # Assistant de configuration interactif
└── data/
    └── pipeline.db          # SQLite (généré)
```

## Prérequis

- Python 3.10+
- Un compte Gmail avec App Password ou OAuth 2.0
- (Optionnel) Un token LinkedIn Developer Portal

## Installation

```bash
git clone <votre-repo>
cd Worflow-social-mails/ai_pipeline
pip install -r requirements.txt
```

## Configuration

Créez un fichier `.env` à partir de `.env.example` :

```bash
cp .env.example .env
# Éditez .env avec vos identifiants
```

Lancez l'assistant interactif :

```bash
python scripts/setup.py
```

### Variables d'environnement

| Variable | Description |
|---|---|
| `GMAIL_USER` | Adresse Gmail principale (authentification SMTP) |
| `GMAIL_APP_PASSWORD` | App Password Gmail |
| `GMAIL_CLIENT_ID` | (Optionnel) OAuth 2.0 |
| `GMAIL_CLIENT_SECRET` | (Optionnel) OAuth 2.0 |
| `LINKEDIN_TOKEN` | Token LinkedIn Developer Portal |
| `LINKEDIN_PERSON_ID` | Person ID LinkedIn |
| `SENDERS_WHITELIST` | Liste blanche des expéditeurs autorisés |
| `DRY_RUN` | `true` (simulation) / `false` (envoi réel) |

## Utilisation

### 1. Créer une note

```markdown
---
status: approved
platform: email                    # ou linkedin
destinataire: contact@domain.com   # requis pour email
sender: alias@domain.com           # optionnel — alias Gmail
tone: professionnel
attachments: []
schedule_at: "2026-05-25T09:00:00" # optionnel — planification
---

Contenu de votre message...
```

### 2. Lancer le pipeline

```bash
python pipeline.py chemin/vers/note.md
```

Le pipeline guide pas à pas :
1. Parse la note → validation des métadonnées
2. Génération du contenu par OpenCode
3. Validation du contenu par OpenCode
4. **Récapitulatif complet** → confirmation utilisateur requise
5. Planification (si `schedule_at` défini)
6. Envoi vers la plateforme
7. Archivage + traçabilité SQLite

## Sécurité

- **Recap bloquant** : affiche tous les détails avant l'envoi, exige `o` / `oui` / `yes`
- **Whitelist expéditeurs** : seuls les alias déclarés dans `.env` sont autorisés
- **Rate-limit** : 30 secondes minimum entre deux envois sur une même plateforme
- **Opérations interdites** : DELETE, TRASH, UPDATE, PATCH, PUT — bloquées au niveau code
- **Audit trail** : toutes les opérations sont journalisées dans SQLite
- **DRY_RUN** : mode simulation par défaut

## Fonctionnalités avancées

### Multi-expéditeur

Utilisez le champ `sender` dans le front-matter pour envoyer depuis un alias Gmail. L'alias doit être configuré dans Gmail (Settings → Accounts → Send mail as) et déclaré dans `SENDERS_WHITELIST`.

### Planification

Ajoutez `schedule_at: "2026-05-25T09:00:00"` pour programmer l'envoi. Le pipeline valide que la date est dans le futur (maximum 30 jours) et affiche un compte à rebours.

### Traçabilité (table `rapp`)

Chaque envoi est enregistré dans SQLite avec l'expéditeur, le destinataire, le sujet, la date planifiée et la date d'envoi effective.

```python
from utils.db import recap_rapp
print(recap_rapp(10))
```

## Tests

```bash
cd ai_pipeline
python pipeline.py test_note.md
```

Passez `DRY_RUN=false` dans `.env` pour des envois réels (après validation).

## Licence

MIT
