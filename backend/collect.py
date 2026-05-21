"""Daily news collection.

Run via GitHub Actions every morning. For each category, calls Claude with web_search,
parses JSON, saves to SQLite.

Usage:
    ANTHROPIC_API_KEY=sk-... python collect.py [--category tech]
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
from pathlib import Path

from anthropic import Anthropic

import db
import prompts

NOTE_PATH = Path(__file__).parent.parent / "daily_note.md"
NOTES_DIR = Path(__file__).parent.parent / "data" / "notes"
SUMMARIES_DIR = Path(__file__).parent.parent / "data" / "summaries"
PROFILE_PATH = Path(__file__).parent.parent / "data" / "profile.md"
NOTE_TEMPLATE = (
    "<!-- 今日のブリーフを読んで気になったこと・質問を1行ここに書く。翌朝のブリーフに反映される。 -->\n"
    "<!-- 例: \"TSMCの半導体予測、$1.5T市場になる根拠は？\" -->\n"
    "<!-- 書いたらGitHubでコミットするだけ。使用後は自動でdata/notes/に保存されてリセットされる。 -->\n\n"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("collect")


def extract_json(text: str) -> dict:
    """Strip markdown fences and extract the first JSON object."""
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:200]}...")
    return json.loads(match.group(0))


def read_latest_monthly_summary() -> str:
    summaries = sorted(SUMMARIES_DIR.glob("????-??.md"), reverse=True)
    if not summaries:
        return ""
    text = summaries[0].read_text(encoding="utf-8").strip()
    log.info("Loaded monthly summary context: %s", summaries[0].name)
    return text


def read_profile() -> str:
    if not PROFILE_PATH.exists():
        return ""
    return PROFILE_PATH.read_text(encoding="utf-8").strip()


def read_user_note() -> str:
    if not NOTE_PATH.exists():
        return ""
    lines = [
        l for l in NOTE_PATH.read_text().splitlines()
        if not l.strip().startswith("<!--")
    ]
    return "\n".join(lines).strip()


def archive_note(note: str, date: str) -> None:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    (NOTES_DIR / f"{date}.md").write_text(note, encoding="utf-8")
    NOTE_PATH.write_text(NOTE_TEMPLATE, encoding="utf-8")
    log.info("Archived note to data/notes/%s.md", date)


def collect_category(client: Anthropic, category_key: str, today: str, user_note: str = "", monthly_summary: str = "", profile: str = "") -> dict:
    log.info("Collecting category: %s", category_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system=prompts.system_prompt(category_key, today),
        messages=[{"role": "user", "content": prompts.user_prompt(category_key, user_note, monthly_summary, profile)}],
    )
    text_blocks = [b.text for b in response.content if b.type == "text"]
    full_text = "\n".join(text_blocks)
    data = extract_json(full_text)
    log.info(
        "  %s: %d stories, headline: %s",
        category_key,
        len(data.get("stories", [])),
        (data.get("headline") or "")[:60],
    )
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--category",
        choices=list(prompts.CATEGORIES.keys()) + ["all"],
        default="all",
    )
    args = parser.parse_args()

    db.init_db()
    client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    today_iso = datetime.now(JST).strftime("%Y-%m-%d")
    today_human = prompts.get_today()

    user_note = read_user_note()
    if user_note:
        log.info("User note found: %s", user_note[:80])
    else:
        log.info("No user note today")

    monthly_summary = read_latest_monthly_summary()
    profile = read_profile()
    if profile:
        log.info("Profile loaded (%d chars)", len(profile))

    targets = (
        list(prompts.CATEGORIES.keys()) if args.category == "all" else [args.category]
    )

    failures = []
    for cat in targets:
        try:
            data = collect_category(client, cat, today_human, user_note, monthly_summary, profile)
            db.save_brief(today_iso, cat, data)
        except Exception as e:
            log.error("Failed %s: %s", cat, e)
            failures.append(cat)

    if user_note and not failures:
        archive_note(user_note, today_iso)

    if failures:
        log.warning("Failed categories: %s", failures)
        return 1 if len(failures) == len(targets) else 0
    log.info("All categories collected successfully for %s", today_iso)
    return 0


if __name__ == "__main__":
    sys.exit(main())
