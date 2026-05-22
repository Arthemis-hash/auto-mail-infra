"""Logger minimal — un fichier par jour dans logs/, pas de bruit."""

import logging
from datetime import datetime
from pathlib import Path

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOGS_DIR.mkdir(exist_ok=True)

_log_file = _LOGS_DIR / f"{datetime.now():%Y-%m-%d}.log"

_handler = logging.FileHandler(_log_file, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))

logger = logging.getLogger("ai_pipeline")
logger.setLevel(logging.INFO)
logger.addHandler(_handler)

# Pas de propagation vers le root logger
logger.propagate = False
