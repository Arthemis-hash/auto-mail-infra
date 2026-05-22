# AI Pipeline — Skills.md

## Objectif
Pipeline de publication automatisée de notes Obsidian vers Email / LinkedIn.
OpenCode = LLM. OAuth 2.0. SQLite.

## Structure
```
ai_pipeline/
├── skills/              # Outils déterministes
├── prompts/             # Templates de prompts (OpenCode les exécute)
├── utils/
│   ├── db.py            # SQLite (tokens OAuth, historique, config)
│   ├── auth_gmail.py    # OAuth 2.0 Gmail API (sans mot de passe)
│   ├── auth_linkedin.py # OAuth 2.0 LinkedIn interactif
│   ├── config.py        # .env + validation
│   ├── json_utils.py    # Parsing JSON défensif
│   └── logger.py        # Logs fichier
├── scripts/setup.py     # Assistant de configuration interactif
├── pipeline.py          # Orchestrateur
├── data/pipeline.db     # Base SQLite
└── .env.example         # Template
```

## Pipeline

### Flow complet
```text
1. parse_note(filepath)              → Parse YAML + body
2. generate_content.build_prompt()   → Construit le prompt de génération
   → OpenCode génère le JSON
3. generate_content.save_result()    → Enregistre la réponse
4. validate_content.build_prompt()   → Prompt de validation
   → OpenCode valide
5. validate_content.save_result()    → Verdict
6. prepare_assets(data)              → Vérifie pièces jointes
7. preview(content, metadata)        → Aperçu
8. validation humaine                → "Envoyer ? (o/n)"
9. dispatch(platform, content)       → Envoi (Gmail API ou LinkedIn API)
10. archive(filepath)                → Archive + historique SQLite
```

### Règles
- OpenCode = seul LLM
- OAuth 2.0 pour Gmail et LinkedIn (pas de mot de passe en clair)
- Historique SQLite des publications
- Ne jamais envoyer sans validation humaine
- DRY_RUN=true par défaut

## Configuration

### Assistant interactif (recommandé)
```bash
python scripts/setup.py
```
Guide pas à pas pour Gmail (App Password ou OAuth) et LinkedIn (OAuth).

### Manuellement dans .env
```
# Gmail — Méthode A (App Password)
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Gmail — Méthode B (OAuth 2.0)
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-xxx

# LinkedIn — Méthode A (token direct)
LINKEDIN_TOKEN=AQX...
LINKEDIN_PERSON_ID=abc123

# LinkedIn — Méthode B (OAuth via setup.py)
LINKEDIN_CLIENT_ID=xxx
LINKEDIN_CLIENT_SECRET=xxx

# Mode
DRY_RUN=true
```

## Format attendu de la note
```markdown
---
status: approved
platform: email          # ou linkedin
destinataire: @
tone: professionnel
attachments:
  - /chemin/fichier.pdf
---
Contenu markdown...
```

## SQLite (data/pipeline.db)
| Table | Usage |
|---|---|
| `tokens` | Refresh tokens OAuth Gmail/LinkedIn |
| `history` | Notes publiées (date, plateforme, status) |
| `config` | LinkedIn Person ID, etc. |
