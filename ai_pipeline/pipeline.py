"""Pipeline — Workflow de publication conçu pour être orchestré par OpenCode.

SÉCURITÉ :
  - Validation de tous les champs AVANT de demander confirmation
  - Recap complet affiché AVANT l'envoi — confirmation impérative bloquante
  - Aucune valeur par défaut pour l'envoi
  - Opérations destructives interdites
  - Rate-limit par plateforme
  - Audit trail dans SQLite
  - Vérification de sécurité de la base de données au démarrage

Flow :
  1. parse_note(filepath)           → parse la note (YAML + body)
  2. validate_metadata(data)         → valide tous les champs
  3. generate_content.build_prompt   → construit le prompt de génération
  [OpenCode génère le contenu]
  4. generate_content.save_result    → enregistre le résultat OpenCode
  5. validate_content.build_prompt   → construit le prompt de validation
  [OpenCode valide]
  6. validate_content.save_result    → enregistre la validation
  7. prepare_assets(data)            → vérifie les pièces jointes
  8. recap_and_confirm(...)          → affiche tout + confirmation bloquante
  9. wait_until(schedule_at)         → si planifié, attend jusqu'à la date
  10. dispatch(platform, content)    → envoie vers la plateforme
  11. archive(filepath)              → archive la note
  12. add_rapp(...)                  → log de traçabilité
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skills.parse_note import parse_note
from skills.generate_content import build_prompt as gen_build_prompt
from skills.generate_content import save_result as gen_save_result
from skills.validate_content import build_prompt as val_build_prompt
from skills.validate_content import save_result as val_save_result
from skills.prepare_assets import prepare_assets
from skills.dispatcher import dispatch
from skills.archive import archive
from utils.logger import logger
from utils.db import init as db_init, add_history, add_rapp, print_database_security_report
from utils.security import require_confirmation, audit
from utils.scheduler import wait_until
from utils.validate import validate_metadata
from utils.config import config, is_dry_run


def recap_and_confirm(content: dict, metadata: dict, assets: dict) -> bool:
    """Affiche un récapitulatif complet et demande confirmation.
    Bloquant — impossible de contourner.
    """
    platform = content.get("platform", "?")
    sender = metadata.get("sender")
    recipient = metadata.get("destinataire", "N/A")
    subject = content.get("subject", "")
    schedule = metadata.get("schedule_at")

    mode = "🔶 DRY RUN (simulation)" if is_dry_run else "🔴 ENVOI RÉEL"

    print("\n" + "=" * 62)
    print("  RÉCAPITULATIF AVANT ENVOI")
    print("=" * 62)
    print(f"  Plateforme:    {platform}")
    print(f"  De:            {sender or '(compte principal)'}")
    print(f"  À:             {recipient}")
    print(f"  Sujet:         {subject}")
    if schedule:
        print(f"  Planifié le:   {schedule}")
    print(f"  Pièces jointes: {len(assets.get('valid', []))}")
    if assets.get("missing"):
        print(f"  ⚠ Fichiers manquants: {', '.join(assets['missing'])}")
    print(f"  Mode:          {mode}")
    print("-" * 62)
    body = content.get("body", "")
    print(body[:500] + ("..." if len(body) > 500 else ""))
    print("-" * 62)
    print("  ATTENTION : Cette action est irréversible." if not is_dry_run else "  Mode simulation — aucun envoi réel.")
    print("=" * 62)

    return require_confirmation(
        "Confirmer l'envoi",
        None,  # Contexte déjà affiché dans le recap
    )


def run(filepath: str) -> None:
    """Exécution autonome du pipeline."""
    db_init()
    logger.info(f"Pipeline démarré: {filepath}")

    # ── Vérification de sécurité de la DB ───────────────────────────
    print_database_security_report()

    data = parse_note(filepath)

    # ── Validation des métadonnées ─────────────────────────────────
    errors = validate_metadata(data["metadata"])
    if errors:
        for err in errors:
            print(f"  ❌ {err}")
        logger.error(f"Validation échouée: {errors}")
        return

    # ── Génération ──────────────────────────────────────────────────
    prompt = gen_build_prompt(data)
    print(f"\n--- PROMPT GÉNÉRATION (à donner à OpenCode) ---\n{prompt}\n---\n")
    raw = input("Colle la réponse JSON d'OpenCode : ")
    content = gen_save_result(data, json.loads(raw))

    # ── Validation du contenu ───────────────────────────────────────
    val_prompt = val_build_prompt(content)
    print(f"\n--- PROMPT VALIDATION (à donner à OpenCode) ---\n{val_prompt}\n---\n")
    raw = input("Colle la réponse JSON d'OpenCode (validation) : ")
    validation = val_save_result(json.loads(raw))

    if not validation["approved"]:
        issues = "\n  - ".join(validation["issues"])
        print(f"\n[REFUSÉ] {issues}")
        add_history(filepath, data["metadata"].get("platform", "?"), "refused", {"issues": validation["issues"]})
        audit("pipeline", "validation", "refused", note_path=filepath, details={"issues": validation["issues"]})
        return

    # ── Assets ──────────────────────────────────────────────────────
    assets = prepare_assets(data)

    # ── Recap + confirmation bloquante ─────────────────────────────
    if not recap_and_confirm(content, data["metadata"], assets):
        platform = data["metadata"].get("platform", "?")
        add_history(filepath, platform, "cancelled", {"reason": "user cancelled"})
        audit("pipeline", platform, "cancelled", note_path=filepath, details={"reason": "user refused recap"})
        print("Pipeline annulé.")
        return

    # ── Planification (wait_until) ──────────────────────────────────
    platform = data["metadata"].get("platform", "email")
    schedule_at = data["metadata"].get("schedule_at")
    if schedule_at:
        try:
            wait_until(schedule_at)
        except ValueError as e:
            logger.error(f"Planification impossible: {e}")
            print(f"\nErreur de planification: {e}")
            return

    # ── Dispatch + Archive ──────────────────────────────────────────
    dispatch(platform, content, data["metadata"], assets.get("valid"))
    archive(filepath)

    # ── Log ─────────────────────────────────────────────────────────
    add_history(filepath, platform, "published", {
        "subject": content.get("subject"),
        "recipient": data["metadata"].get("destinataire"),
    })
    add_rapp(
        sender=data["metadata"].get("sender") or config.get("GMAIL_USER", "unknown"),
        recipient=data["metadata"].get("destinataire", "unknown"),
        platform=platform,
        subject=content.get("subject", ""),
        status="sent",
        scheduled_at=schedule_at or "",
    )
    audit("pipeline", platform, "success", note_path=filepath)
    logger.info("Pipeline terminé avec succès")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <chemin_note.md>")
        sys.exit(1)
    run(sys.argv[1])
