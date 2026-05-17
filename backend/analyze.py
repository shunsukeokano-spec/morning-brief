"""Monthly and annual analysis of Shun's daily notes.

Monthly (run on 1st of each month):
  - Reads data/notes/YYYY-MM-*.md from last month
  - Generates a compressed interest profile + persistent questions
  - Saves to data/summaries/YYYY-MM.md

Annual (run on Jan 1st):
  - Reads all data/summaries/YYYY-MM.md from last year
  - Generates a deep analysis of information needs and brief gaps
  - Saves to data/summaries/YYYY-annual.md

Usage:
    python analyze.py --monthly
    python analyze.py --annual
"""

import argparse
import logging
import sys
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("analyze")

REPO_ROOT = Path(__file__).parent.parent
NOTES_DIR = REPO_ROOT / "data" / "notes"
SUMMARIES_DIR = REPO_ROOT / "data" / "summaries"


def load_notes_for_month(year: int, month: int) -> list[tuple[str, str]]:
    prefix = f"{year:04d}-{month:02d}-"
    files = sorted(NOTES_DIR.glob(f"{prefix}*.md"))
    result = []
    for f in files:
        text = f.read_text(encoding="utf-8").strip()
        if text:
            result.append((f.stem, text))
    return result


def load_monthly_summaries_for_year(year: int) -> list[tuple[str, str]]:
    result = []
    for month in range(1, 13):
        path = SUMMARIES_DIR / f"{year:04d}-{month:02d}.md"
        if path.exists():
            result.append((path.stem, path.read_text(encoding="utf-8").strip()))
    return result


def run_monthly(client: Anthropic, year: int, month: int) -> Path:
    notes = load_notes_for_month(year, month)
    month_str = f"{year:04d}-{month:02d}"

    if not notes:
        log.warning("No notes found for %s — skipping", month_str)
        return None

    log.info("Analyzing %d notes for %s", len(notes), month_str)

    notes_text = "\n\n".join(f"[{date}]\n{text}" for date, text in notes)

    prompt = f"""You are analyzing Shun's daily notes from {month_str}.

Shun is a Japanese embedded engineer who reads a daily news brief covering Tech, Geopolitics, Economy, Startups, and AI Forecast. After reading each brief, he sometimes writes a short question or comment. These are his notes from this month:

---
{notes_text}
---

Analyze these notes and produce a concise markdown report with these sections:

## Recurring Themes
What topics, companies, or questions kept coming up? List 3–6 themes with brief explanations.

## Persistent Questions
Questions Shun asked that were not clearly resolved. These should be carried into next month's brief focus. List as bullet points.

## Interest Shift
Did Shun's focus change over the month? Note any emerging or fading interests.

## Brief Focus for Next Month
2–3 concrete suggestions for what next month's brief should emphasize based on these patterns. Be specific (e.g. "cover TSMC's Q2 earnings and capacity expansion" not just "more semiconductor news").

Keep the report concise — under 400 words total."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    summary = response.content[0].text.strip()

    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    out = SUMMARIES_DIR / f"{month_str}.md"
    out.write_text(f"# Monthly Summary: {month_str}\n\n{summary}\n", encoding="utf-8")
    log.info("Saved monthly summary to %s", out)
    return out


def run_annual(client: Anthropic, year: int) -> Path:
    summaries = load_monthly_summaries_for_year(year)

    if not summaries:
        log.warning("No monthly summaries found for %d — skipping annual analysis", year)
        return None

    log.info("Running annual analysis for %d (%d monthly summaries)", year, len(summaries))

    summaries_text = "\n\n---\n\n".join(f"### {m}\n{text}" for m, text in summaries)

    prompt = f"""You are doing a deep analysis of Shun's information needs and curiosity patterns over {year}.

Shun is a Japanese embedded engineer who reads a daily news brief (Tech, Geopolitics, Economy, Startups, AI Forecast) and writes short daily notes about what interests or puzzles him. Here are the monthly compressed summaries of those notes:

---
{summaries_text}
---

Write a structured annual analysis with these sections:

## Core Stable Interests
Topics that appeared consistently across many months. These are Shun's bedrock interests.

## Growing Interests
Topics that gained importance over the year.

## Fading Interests
Topics that were prominent early but trailed off.

## Persistent Unanswered Questions
Questions or themes that appeared repeatedly but were never clearly resolved. These represent gaps in the brief.

## Brief Performance Assessment
Which of the 5 categories (Tech, Geopolitics, Economy, Startups, AI Forecast) delivered the most value to Shun based on his engagement? Which underperformed?

## Recommendations for Next Year
3–5 specific, actionable changes to improve the brief for Shun next year. Could include: new sources to add, topics to deprioritize, a new category, or a change in the signal/forecast framing.

Be direct and specific. This report will be used to tune the brief for next year."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    analysis = response.content[0].text.strip()

    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    out = SUMMARIES_DIR / f"{year:04d}-annual.md"
    out.write_text(f"# Annual Analysis: {year}\n\n{analysis}\n", encoding="utf-8")
    log.info("Saved annual analysis to %s", out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--monthly", action="store_true")
    group.add_argument("--annual", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    client = Anthropic()

    if args.monthly:
        # Analyze last month
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1
        result = run_monthly(client, year, month)
        return 0 if result else 1

    if args.annual:
        # Analyze last year
        result = run_annual(client, now.year - 1)
        return 0 if result else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
