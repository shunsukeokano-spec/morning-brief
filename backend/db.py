"""SQLite access layer for Morning Brief.

Schema is defined in docs/ARCHITECTURE.md and docs/IMPROVEMENT.md.
All tables created upfront; later phases populate them progressively.
Migrations should be additive only.
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "data" / "briefs.db"

SCHEMA = """
-- Phase 1: Core brief storage
CREATE TABLE IF NOT EXISTS briefs (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    headline TEXT,
    tldr TEXT,
    signal TEXT,
    bias_note TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(date, category)
);

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY,
    brief_id INTEGER REFERENCES briefs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    source TEXT,
    source_region TEXT,
    source_url TEXT,
    significance TEXT,
    trend_signal TEXT,
    route TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_briefs_date ON briefs(date);
CREATE INDEX IF NOT EXISTS idx_stories_brief ON stories(brief_id);

-- Phase 2: Passive signals from user behavior
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY,
    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    weight REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_story ON signals(story_id);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);

-- Phase 3: Entities and clusters
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT,
    first_seen TEXT,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS story_entities (
    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (story_id, entity_id)
);

CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY,
    theme TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    total_stories INTEGER DEFAULT 0,
    status TEXT
);

CREATE TABLE IF NOT EXISTS story_clusters (
    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
    cluster_id INTEGER REFERENCES clusters(id) ON DELETE CASCADE,
    PRIMARY KEY (story_id, cluster_id)
);

-- Phase 4: Preference model + predictions tracking
CREATE TABLE IF NOT EXISTS entity_interests (
    entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    score REAL DEFAULT 0,
    last_updated TEXT NOT NULL,
    signal_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY,
    brief_id INTEGER REFERENCES briefs(id) ON DELETE CASCADE,
    prediction_text TEXT NOT NULL,
    timeframe TEXT,
    made_at TEXT NOT NULL,
    resolved_at TEXT,
    outcome TEXT
);

-- Phase 5: Prompt improvement history with rollback
CREATE TABLE IF NOT EXISTS prompts_history (
    id INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    category TEXT NOT NULL,
    old_prompt TEXT NOT NULL,
    new_prompt TEXT NOT NULL,
    reason TEXT NOT NULL,
    metrics_before TEXT,
    metrics_7d_after TEXT,
    rolled_back_at TEXT
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Additive migrations
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(stories)")}
        if "route" not in existing_cols:
            conn.execute("ALTER TABLE stories ADD COLUMN route TEXT")
        # Set cold start end date if not already set (14 days from first run)
        existing = conn.execute(
            "SELECT value FROM config WHERE key = 'cold_start_end_date'"
        ).fetchone()
        if not existing:
            end = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
            conn.execute(
                "INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?)",
                ("cold_start_end_date", end, datetime.now(timezone.utc).isoformat()),
            )


def save_brief(date: str, category: str, data: dict[str, Any]) -> int:
    """Save a brief and its stories. Replaces if date+category already exists."""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM briefs WHERE date = ? AND category = ?", (date, category)
        )
        cur = conn.execute(
            """INSERT INTO briefs (date, category, headline, tldr, signal, bias_note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                date,
                category,
                data.get("headline"),
                data.get("tldr"),
                data.get("signal"),
                data.get("bias_note"),
                now,
            ),
        )
        brief_id = cur.lastrowid
        for story in data.get("stories", []):
            conn.execute(
                """INSERT INTO stories
                   (brief_id, title, summary, source, source_region, source_url,
                    significance, trend_signal, route, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    brief_id,
                    story.get("title"),
                    story.get("summary"),
                    story.get("source"),
                    story.get("source_region"),
                    story.get("source_url"),
                    story.get("significance"),
                    story.get("trend_signal"),
                    story.get("route"),
                    now,
                ),
            )
        return brief_id


def get_briefs_by_date(date: str) -> list[dict[str, Any]]:
    """Return all briefs for a given date with their stories."""
    with get_conn() as conn:
        briefs = conn.execute(
            "SELECT * FROM briefs WHERE date = ? ORDER BY category", (date,)
        ).fetchall()
        result = []
        for b in briefs:
            stories = conn.execute(
                "SELECT * FROM stories WHERE brief_id = ?", (b["id"],)
            ).fetchall()
            result.append({**dict(b), "stories": [dict(s) for s in stories]})
        return result


def is_cold_start_active() -> bool:
    """Check if we're still in the 14-day cold start period."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM config WHERE key = 'cold_start_end_date'"
        ).fetchone()
        if not row:
            return False
        return datetime.now(timezone.utc).strftime("%Y-%m-%d") <= row["value"]
