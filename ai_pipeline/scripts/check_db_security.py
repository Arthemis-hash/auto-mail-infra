#!/usr/bin/env python3
"""Script autonome pour vérifier la sécurité de la base de données.

Utilisation:
    python scripts/check_db_security.py

Ce script :
  - Vérifie l'existence et la taille de pipeline.db
  - Contrôle les permissions fichier (danger si world-readable)
  - Compte les tokens OAuth stockés
  - Audite les secrets en configuration
  - Génère un rapport détaillé
"""

import sys
from pathlib import Path

# Ajouter ai_pipeline au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.db import print_database_security_report, check_database_security


def main():
    print("\n🔐 Vérification de sécurité — Base de données pipeline\n")
    
    report = print_database_security_report()
    
    # Retourner un code d'erreur approprié
    if report["status"] == "danger":
        sys.exit(1)  # Erreur critique
    elif report["status"] == "warning":
        sys.exit(0)  # Attention mais OK
    else:
        sys.exit(0)  # Succès


if __name__ == "__main__":
    main()
