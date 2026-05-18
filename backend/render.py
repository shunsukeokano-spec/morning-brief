"""Generate docs/index.html from today's export JSON.

Run after export.py. Embeds the JSON data directly so the page works
from GitHub Pages without any runtime API calls.
"""

import json
import logging
import os
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
    route = story.get("route", "")

    if has_url:
        title_html = f'<a href="{story["source_url"]}" target="_blank" rel="noopener noreferrer" class="story-title">{title} <span class="ext-icon">↗</span></a>'
    else:
        title_html = f'<span class="story-title-plain">{title}</span>'

    if route == "personal":
        route_badge = '<span class="route-badge route-personal">Your Focus</span>'
    elif route == "world":
        route_badge = '<span class="route-badge route-world">World</span>'
    else:
        route_badge = ""

    return f"""
    <div class="story" style="border-left-color:{color}">
      <div class="story-meta">
        <span class="region" style="color:{color}">{region}</span>
        <span class="dot">·</span>
        <span class="source-name">{source}</span>
        {route_badge}
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


def render_html(date_str: str, briefs: list[dict], worker_url: str = "") -> str:
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

  .route-badge {{ font-size: 9px; font-family: monospace; letter-spacing: 0.08em; text-transform: uppercase; padding: 1px 5px; border-radius: 2px; }}
  .route-personal {{ background: #1a2a1a; color: #A8FF78; border: 1px solid #2a4a2a; }}
  .route-world {{ background: #1a1a2a; color: #7EB8FF; border: 1px solid #2a2a4a; }}

  .note-section {{ padding: 28px 24px; border-top: 1px solid #1A1A1A; }}
  .note-header {{ font-family: monospace; font-size: 10px; letter-spacing: 0.25em; color: #555; text-transform: uppercase; margin-bottom: 12px; }}
  .note-current {{ font-size: 13px; color: #666; font-style: italic; margin-bottom: 12px; padding: 10px 14px; background: #0A0A0A; border-left: 2px solid #333; display: none; }}
  .note-textarea {{ width: 100%; background: #111; border: 1px solid #2a2a2a; color: #E8E8E0; font-family: 'Helvetica Neue', sans-serif; font-size: 14px; padding: 12px; resize: vertical; min-height: 60px; outline: none; border-radius: 2px; }}
  .note-textarea:focus {{ border-color: #444; }}
  .note-textarea::placeholder {{ color: #444; }}
  .note-row {{ display: flex; align-items: center; gap: 12px; margin-top: 10px; flex-wrap: wrap; }}
  .note-save {{ background: #E8E8E0; color: #0D0D0D; border: none; padding: 8px 20px; font-family: monospace; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; font-weight: 700; cursor: pointer; }}
  .note-save:hover {{ background: #fff; }}
  .note-save:disabled {{ opacity: 0.4; cursor: not-allowed; }}
  .note-status {{ font-size: 12px; font-family: monospace; }}
  .note-status.ok {{ color: #A8FF78; }}
  .note-status.err {{ color: #FF6B6B; }}
  .note-not-configured {{ font-size: 12px; color: #555; font-family: monospace; margin-bottom: 10px; }}
  .token-modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 100; align-items: center; justify-content: center; }}
  .token-modal.open {{ display: flex; }}
  .token-box {{ background: #111; border: 1px solid #333; padding: 28px; max-width: 480px; width: 90%; }}
  .token-box h3 {{ font-family: monospace; font-size: 12px; letter-spacing: 0.2em; text-transform: uppercase; color: #888; margin-bottom: 16px; }}
  .token-box p {{ font-size: 13px; color: #777; line-height: 1.6; margin-bottom: 12px; }}
  .token-box a {{ color: #7EB8FF; }}
  .token-input {{ width: 100%; background: #0A0A0A; border: 1px solid #333; color: #E8E8E0; font-family: monospace; font-size: 13px; padding: 10px; outline: none; margin-bottom: 12px; border-radius: 2px; }}
  .token-input:focus {{ border-color: #555; }}
  .token-btn {{ background: #E8E8E0; color: #0D0D0D; border: none; padding: 8px 20px; font-family: monospace; font-size: 11px; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; cursor: pointer; margin-right: 8px; }}
  .token-btn:hover {{ background: #fff; }}
  .token-cancel {{ background: transparent; color: #555; border: 1px solid #333; padding: 8px 16px; font-family: monospace; font-size: 11px; cursor: pointer; }}
  .setup-link-btn {{ font-size: 11px; color: #555; font-family: monospace; cursor: pointer; background: none; border: none; text-decoration: underline; padding: 0; }}
  .setup-link-btn:hover {{ color: #aaa; }}

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
  <span style="color:#444">·</span>
  <span class="route-badge route-personal">Your Focus</span>
  <span style="font-size:11px;color:#555">Shunのメモに関連</span>
  <span class="route-badge route-world">World</span>
  <span style="font-size:11px;color:#555">世間の注目</span>
  <span style="margin-left:auto;font-size:11px;color:#555">Click titles to open source</span>
</div>

<div class="grid">
{panels_html}
</div>

<div class="note-section">
  <div class="note-header">Tomorrow's Brief — Leave a Note</div>
  <div class="note-current" id="note-current"></div>
  <textarea class="note-textarea" id="note-input" placeholder="気になったこと・質問を一行書く。明日のブリーフに反映される。"></textarea>
  <div class="note-row">
    <button class="note-save" id="note-save" onclick="saveNote()">Save to Tomorrow's Brief</button>
    <span class="note-status" id="note-status"></span>
    <button class="setup-link-btn" id="setup-link-btn" onclick="copySetupLink()" style="margin-left:auto;display:none">📋 Copy setup link for other devices</button>
    <button class="setup-link-btn" onclick="openTokenModal()" id="setup-btn">⚙ Setup</button>
  </div>
</div>

<div class="footer">
  <span>State media sources tagged as reference only — interpret with caution.</span>
  <span>Generated {generated_at}</span>
</div>

<!-- Token setup modal -->
<div class="token-modal" id="token-modal">
  <div class="token-box">
    <h3>One-time Setup</h3>
    <p>GitHubのfine-grained tokenが必要です。<a href="https://github.com/settings/personal-access-tokens/new" target="_blank">こちらで発行 ↗</a></p>
    <p style="font-size:12px;color:#555">
      設定: Repository access → <strong>Only morning-brief</strong><br>
      Permissions: <strong>Contents → Read and write</strong><br>
      Expiration: <strong>No expiration</strong><br>
      トークンはこのブラウザのlocalStorageにのみ保存されます。
    </p>
    <input class="token-input" id="token-input" type="password" placeholder="github_pat_..." />
    <div>
      <button class="token-btn" onclick="saveToken()">Save Token</button>
      <button class="token-cancel" onclick="closeTokenModal()">Cancel</button>
    </div>
    <div id="modal-status" style="margin-top:10px;font-size:12px;font-family:monospace;min-height:18px"></div>
  </div>
</div>

<script>
const REPO = 'shunsukeokano-spec/morning-brief';
const NOTE_PATH = 'daily_note.md';
const PAGE_URL = 'https://shunsukeokano-spec.github.io/morning-brief/';
let _sha = null;

function getToken() {{ return localStorage.getItem('gh_token'); }}

async function loadCurrentNote() {{
  // Auto-setup from ?setup= param
  const params = new URLSearchParams(location.search);
  const setupToken = params.get('setup');
  if (setupToken) {{
    localStorage.setItem('gh_token', setupToken);
    history.replaceState(null, '', location.pathname);
    showTokenSet();
    setStatus('ok', '✓ Token set from setup link');
  }} else if (getToken()) {{
    showTokenSet();
  }}

  try {{
    const res = await fetch(`https://api.github.com/repos/${{REPO}}/contents/${{NOTE_PATH}}`);
    if (!res.ok) return;
    const data = await res.json();
    _sha = data.sha;
    const raw = decodeURIComponent(escape(atob(data.content.replace(/\\n/g, ''))));
    const lines = raw.split('\\n').filter(l => !l.trim().startsWith('<!--')).join('\\n').trim();
    if (lines) {{
      const el = document.getElementById('note-current');
      el.textContent = '現在のメモ: ' + lines;
      el.style.display = 'block';
    }}
  }} catch(e) {{ /* no-op */ }}
}}

function showTokenSet() {{
  document.getElementById('setup-btn').textContent = '⚙ Token set';
  document.getElementById('setup-link-btn').style.display = 'inline';
}}

async function saveNote() {{
  const token = getToken();
  if (!token) {{ openTokenModal(); return; }}

  const note = document.getElementById('note-input').value.trim();
  if (!note) {{ setStatus('err', '何か書いてください'); return; }}

  const btn = document.getElementById('note-save');
  btn.disabled = true;
  setStatus('', 'Saving...');

  try {{
    const template = `<!-- 今日のブリーフを読んで気になったこと・質問を1行ここに書く。翌朝のブリーフに反映される。 -->\\n\\n${{note}}\\n`;
    const res = await fetch(`https://api.github.com/repos/${{REPO}}/contents/${{NOTE_PATH}}`, {{
      method: 'PUT',
      headers: {{ 'Authorization': `token ${{token}}`, 'Content-Type': 'application/json' }},
      body: JSON.stringify({{
        message: `Daily note ${{new Date().toISOString().split('T')[0]}}`,
        content: btoa(unescape(encodeURIComponent(template))),
        sha: _sha
      }})
    }});
    if (res.ok) {{
      const data = await res.json();
      _sha = data.content.sha;
      setStatus('ok', "✓ Saved — will appear in tomorrow's brief");
      document.getElementById('note-input').value = '';
      const el = document.getElementById('note-current');
      el.textContent = '現在のメモ: ' + note;
      el.style.display = 'block';
    }} else if (res.status === 401) {{
      localStorage.removeItem('gh_token');
      document.getElementById('setup-btn').textContent = '⚙ Setup';
      document.getElementById('setup-link-btn').style.display = 'none';
      setStatus('err', 'Token expired — please set up again');
      openTokenModal();
    }} else {{
      setStatus('err', 'Save failed (' + res.status + ')');
    }}
  }} catch(e) {{
    setStatus('err', 'Error: ' + e.message);
  }} finally {{
    btn.disabled = false;
  }}
}}

function copySetupLink() {{
  const token = getToken();
  if (!token) return;
  const url = PAGE_URL + '?setup=' + encodeURIComponent(token);
  navigator.clipboard.writeText(url).then(() => {{
    setStatus('ok', '✓ Setup link copied — open it on another device');
  }}).catch(() => {{
    prompt('Copy this link and open on another device:', url);
  }});
}}

function setStatus(type, msg) {{
  const el = document.getElementById('note-status');
  el.textContent = msg;
  el.className = 'note-status' + (type ? ' ' + type : '');
}}

function openTokenModal() {{
  document.getElementById('token-modal').classList.add('open');
  document.getElementById('modal-status').textContent = '';
  setTimeout(() => document.getElementById('token-input').focus(), 50);
}}

function closeTokenModal() {{
  document.getElementById('token-modal').classList.remove('open');
}}

function saveToken() {{
  const t = document.getElementById('token-input').value.trim();
  if (!t) {{
    document.getElementById('modal-status').textContent = 'トークンを入力してください';
    return;
  }}
  localStorage.setItem('gh_token', t);
  document.getElementById('modal-status').style.color = '#A8FF78';
  document.getElementById('modal-status').textContent = '✓ Saved!';
  setTimeout(() => {{
    closeTokenModal();
    showTokenSet();
    setStatus('ok', 'Token saved — now write your note and click Save');
  }}, 600);
}}

document.getElementById('token-modal').addEventListener('click', function(e) {{
  if (e.target === this) closeTokenModal();
}});

document.getElementById('token-input').addEventListener('keydown', function(e) {{
  if (e.key === 'Enter') saveToken();
}});

window.addEventListener('load', loadCurrentNote);
</script>

</body>
</html>"""


def main() -> None:
    date_str, briefs = load_latest_export()
    worker_url = os.environ.get("NOTE_WORKER_URL", "")
    html = render_html(date_str, briefs, worker_url)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    log.info("Rendered %s (worker_url=%s)", OUTPUT, "set" if worker_url else "not set")


if __name__ == "__main__":
    main()
