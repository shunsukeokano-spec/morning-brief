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
from datetime import datetime, timezone

from anthropic import Anthropic

import db
import prompts

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


def collect_category(client: Anthropic, category_key: str, today: str) -> dict:
    log.info("Collecting category: %s", category_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system=prompts.system_prompt(category_key, today),
        messages=[{"role": "user", "content": prompts.user_prompt(category_key)}],
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
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_human = prompts.get_today()

    targets = (
        list(prompts.CATEGORIES.keys()) if args.category == "all" else [args.category]
    )

    failures = []
    for cat in targets:
        try:
            data = collect_category(client, cat, today_human)
            db.save_brief(today_iso, cat, data)
        except Exception as e:
            log.error("Failed %s: %s", cat, e)
            failures.append(cat)

    if failures:
        log.warning("Failed categories: %s", failures)
        return 1 if len(failures) == len(targets) else 0
    log.info("All categories collected successfully for %s", today_iso)
    return 0


if __name__ == "__main__":
    sys.exit(main())
