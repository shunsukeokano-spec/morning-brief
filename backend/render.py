"""Generate docs/index.html from today's export JSON.

Run after export.py. Embeds the JSON data directly so the page works
from GitHub Pages without any runtime API calls.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("render")

REPO_ROOT = Path(__file__).parent.parent
EXPORTS_DIR = REPO_ROOT / "data" / "exports"
OUTPUT = REPO_ROOT / "docs" / "index.html"

CATEGORY_META = {
    "tech":        {"label": "Technology",  "icon": "⬡", "color": "#00D4FF"},
    "politics":    {"label": "Geopolitics", "icon": "◈", "color": "#FF6B35"},
    "economy":     {"label": "Economy",     "icon": "◎", "color": "#FFD700"},
    "startups":    {"label": "Startups",    "icon": "△", "color": "#A8FF78"},
    "ai_forecast": {"label": "AI Forecast", "icon": "✦", "color": "#C77DFF"},
}

SIGNAL_COLORS = {"bull": "#A8FF78", "bear": "#FF6B6B", "neutral": "#888", "watch": "#FFD700"}
SIGNAL_LABELS = {"bull": "↑", "bear": "↓", "neutral": "–", "watch": "◉"}


def load_latest_export() -> tuple[str, list[dict]]:
    exports = sorted(EXPORTS_DIR.glob("*.json"), reverse=True)
    if not exports:
        log.error("No export files found in %s", EXPORTS_DIR)
        sys.exit(1)
    path = exports[0]
    date_str = path.stem
    data = json.loads(path.read_text())
    log.info("Loaded %s (%d categories)", path.name, len(data))
    return date_str, data


def format_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A, %B %-d, %Y")


def render_story(story: dict, color: str) -> str:
    has_url = bool(story.get("source_url", "").startswith("http"))
    signal = story.get("trend_signal", "neutral")
    sig_color = SIGNAL_COLORS.get(signal, "#888")
    sig_label = SIGNAL_LABELS.get(signal, "–")
    region = story.get("source_region", "")
    source = story.get("source", "")
    title = story.get("title", "")
    summary = story.get("summary", "")
    significance = story.get("significance", "")

    if has_url:
        title_html = f'<a href="{story["source_url"]}" target="_blank" rel="noopener noreferrer" class="story-title">{title} <span class="ext-icon">↗</span></a>'
    else:
        title_html = f'<span class="story-title-plain">{title}</span>'

    return f"""
    <div class="story" style="border-left-color:{color}">
      <div class="story-meta">
        <span class="region" style="color:{color}">{region}</span>
        <span class="dot">·</span>
        <span class="source-name">{source}</span>
        <span class="signal" style="color:{sig_color}">{sig_label}</span>
      </div>
      {title_html}
      <div class="summary">{summary}</div>
      <div class="significance">↳ {significance}</div>
    </div>"""


def render_panel(brief: dict) -> str:
    cat_key = brief.get("category", "")
    meta = CATEGORY_META.get(cat_key, {"label": cat_key, "icon": "●", "color": "#888"})
    color = meta["color"]
    stories_html = "".join(render_story(s, color) for s in brief.get("stories") or [])

    signal_html = ""
    if brief.get("signal"):
        signal_html = f"""
      <div class="signal-box" style="border-left-color:{color}">
        <div class="signal-label">30–90 Day Signal</div>
        <div class="signal-text">{brief["signal"]}</div>
      </div>"""

    bias_html = ""
    if brief.get("bias_note"):
        bias_html = f'<div class="bias-note">Coverage note: {brief["bias_note"]}</div>'

    return f"""
  <div class="panel" style="border-top-color:{color}">
    <div class="panel-header">
      <span class="cat-icon" style="color:{color}">{meta["icon"]}</span>
      <span class="cat-label" style="color:{color}">{meta["label"]}</span>
    </div>
    <div class="headline">{brief.get("headline", "")}</div>
    <div class="tldr">{brief.get("tldr", "")}</div>
    <div class="stories">{stories_html}</div>
    {signal_html}
    {bias_html}
  </div>"""


def render_html(date_str: str, briefs: list[dict]) -> str:
    date_human = format_date(date_str)
    panels_html = "".join(render_panel(b) for b in briefs)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Brief — {date_human}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0D0D0D; color: #E8E8E0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
  a {{ color: inherit; text-decoration: none; }}
  a:hover {{ color: #fff; }}

  .header {{ padding: 32px 24px 20px; border-bottom: 1px solid #1A1A1A; display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px; }}
  .header-label {{ font-family: monospace; font-size: 10px; letter-spacing: 0.3em; color: #444; text-transform: uppercase; margin-bottom: 8px; }}
  .header-date {{ font-family: Georgia, serif; font-size: 28px; font-weight: 700; color: #F0EFE6; letter-spacing: -0.02em; }}
  .archive-link {{ font-family: monospace; font-size: 11px; color: #555; letter-spacing: 0.1em; text-transform: uppercase; border: 1px solid #333; padding: 8px 14px; }}
  .archive-link:hover {{ color: #aaa; border-color: #555; }}

  .legend {{ padding: 10px 24px; border-bottom: 1px solid #1A1A1A; display: flex; gap: 20px; flex-wrap: wrap; font-size: 11px; color: #555; }}

  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1px; background: #1A1A1A; padding: 1px; }}

  .panel {{ background: #111; border: 1px solid #222; border-top: 3px solid; padding: 24px; }}
  .panel-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }}
  .cat-icon {{ font-size: 20px; }}
  .cat-label {{ font-family: monospace; font-size: 13px; letter-spacing: 0.15em; text-transform: uppercase; }}

  .headline {{ font-family: Georgia, serif; font-size: 18px; font-weight: 700; color: #F0EFE6; margin-bottom: 10px; line-height: 1.3; }}
  .tldr {{ font-size: 13px; color: #AAA; line-height: 1.7; margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid #1E1E1E; }}

  .story {{ border-left: 2px solid; padding-left: 16px; margin-bottom: 20px; }}
  .story-meta {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 11px; }}
  .region {{ font-family: monospace; letter-spacing: 0.1em; text-transform: uppercase; }}
  .dot {{ color: #444; }}
  .source-name {{ color: #888; }}
  .signal {{ margin-left: auto; font-size: 13px; font-weight: 700; }}
  .ext-icon {{ font-size: 10px; color: #555; }}

  .story-title {{ font-family: Georgia, serif; font-size: 15px; font-weight: 600; color: #E8E8E0; display: block; margin-bottom: 6px; line-height: 1.4; }}
  .story-title:hover {{ color: #fff; }}
  .story-title-plain {{ font-family: Georgia, serif; font-size: 15px; font-weight: 600; color: #888; display: block; margin-bottom: 6px; line-height: 1.4; }}
  .summary {{ font-size: 13px; color: #999; line-height: 1.6; margin-bottom: 6px; }}
  .significance {{ font-size: 12px; color: #666; font-style: italic; line-height: 1.4; }}

  .signal-box {{ margin-top: 20px; padding: 14px; background: #0A0A0A; border: 1px solid #222; border-left: 2px solid; }}
  .signal-label {{ font-size: 10px; color: #555; font-family: monospace; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 6px; }}
  .signal-text {{ font-size: 13px; color: #CCC; line-height: 1.6; }}

  .bias-note {{ margin-top: 12px; font-size: 11px; color: #555; font-style: italic; }}

  .footer {{ padding: 16px 24px; border-top: 1px solid #1A1A1A; font-size: 11px; color: #333; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }}

  @media (max-width: 600px) {{
    .header {{ padding: 20px 16px 16px; }}
    .header-date {{ font-size: 20px; }}
    .grid {{ grid-template-columns: 1fr; }}
    .panel {{ padding: 16px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="header-label">Morning Brief</div>
    <div class="header-date">{date_human}</div>
  </div>
  <a class="archive-link" href="https://github.com/shunsukeokano-spec/morning-brief/tree/main/data/exports">Archive ↗</a>
</div>

<div class="legend">
  <span><span style="color:#A8FF78;font-weight:700">↑</span> Bull</span>
  <span><span style="color:#FF6B6B;font-weight:700">↓</span> Bear</span>
  <span><span style="color:#888;font-weight:700">–</span> Neutral</span>
  <span><span style="color:#FFD700;font-weight:700">◉</span> Watch</span>
  <span style="margin-left:auto">Click story titles to open source</span>
</div>

<div class="grid">
{panels_html}
</div>

<div class="footer">
  <span>State media sources tagged as reference only — interpret with caution.</span>
  <span>Generated {generated_at}</span>
</div>

</body>
</html>"""


def main() -> None:
    date_str, briefs = load_latest_export()
    html = render_html(date_str, briefs)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    log.info("Rendered %s", OUTPUT)


if __name__ == "__main__":
    main()
