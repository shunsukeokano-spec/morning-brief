"""Export today's briefs to data/exports/YYYY-MM-DD.json for Git tracking."""

import json
import logging
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
from pathlib import Path

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("export")

EXPORTS_DIR = Path(__file__).parent.parent / "data" / "exports"


def export_date(date: str) -> Path:
    briefs = db.get_briefs_by_date(date)
    if not briefs:
        log.warning("No briefs found for %s", date)
        return None
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / f"{date}.json"
    path.write_text(json.dumps(briefs, indent=2, ensure_ascii=False))
    log.info("Exported %d briefs to %s", len(briefs), path)
    return path


if __name__ == "__main__":
    today = datetime.now(JST).strftime("%Y-%m-%d")
    export_date(today)
