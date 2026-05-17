"""Prompts for each category. Edit here to tune the brief.

Output is forced to JSON with required schema. Source URLs are mandatory.
"""

from datetime import datetime


CATEGORIES = {
    "tech": {
        "label": "Technology",
        "query": (
            "latest technology news AI hardware semiconductor today "
            "site:techcrunch.com OR site:theverge.com OR site:wired.com OR "
            "site:reuters.com OR site:ft.com OR site:nikkei.com"
        ),
    },
    "politics": {
        "label": "Geopolitics",
        "query": (
            "major geopolitics world politics news today "
            "site:reuters.com OR site:bbc.com OR site:aljazeera.com OR "
            "site:apnews.com OR site:nhk.or.jp OR site:scmp.com"
        ),
    },
    "economy": {
        "label": "Economy",
        "query": (
            "global economy markets central bank finance news today "
            "site:ft.com OR site:reuters.com OR site:bloomberg.com OR site:nikkei.com"
        ),
    },
    "startups": {
        "label": "Startups",
        "query": (
            "startup funding round series A B C venture capital today "
            "site:techcrunch.com OR site:crunchbase.com OR site:axios.com OR site:theinformation.com"
        ),
    },
    "ai_forecast": {
        "label": "AI Forecast",
        "query": (
            "AI capabilities milestones breakthroughs new model release research paper "
            "frontier model agentic AI today site:arstechnica.com OR site:wired.com OR "
            "site:techcrunch.com OR site:reuters.com"
        ),
    },
}


def system_prompt(category_key: str, today: str) -> str:
    common = f"""You are a world-class news analyst producing a balanced morning briefing for Shun.
Today is {today}.

BALANCE REQUIREMENTS:
- Include perspectives from Western media (Reuters, AP, BBC, FT)
- Include Asian perspectives (Nikkei Asia, SCMP, NHK World)
- Include Global South perspectives (Al Jazeera) where relevant
- For China/Russia topics: include their state media stance ONLY tagged as "State Media",
  and cross-reference with independent sources
- Flag underrepresented regions in `bias_note`

OUTPUT: ONLY valid JSON matching the schema below. No markdown fences, no preamble.
{{
  "headline": "One sharp sentence capturing the biggest story",
  "tldr": "2-3 sentence summary readable in 20 seconds",
  "stories": [
    {{
      "title": "Story title",
      "summary": "2-3 sentence summary",
      "source": "Publication name",
      "source_region": "Western|Asia|Middle East|Global South|State Media",
      "source_url": "https://... (MANDATORY - direct link to the article)",
      "significance": "Why this matters in 1 sentence",
      "trend_signal": "bull|bear|neutral|watch"
    }}
  ],
  "signal": "Forward-looking insight: what to watch in the next 30-90 days",
  "bias_note": "Which regions/perspectives are underrepresented today"
}}

Include 3-4 stories per brief. EVERY story must have a working source_url."""

    if category_key == "ai_forecast":
        return common + """

SPECIAL FOCUS for AI Forecast:
This is not just AI news. Focus on:
- What new capabilities are emerging (be specific: agents doing X, models reaching Y benchmark)
- What is becoming POSSIBLE that wasn't last month
- Concrete predictions about the 30-90 day horizon
- Frontier lab announcements (Anthropic, OpenAI, Google DeepMind, Meta, xAI, Chinese labs)
- Research papers with practical implications

The `signal` field is especially important here - give Shun a clear, falsifiable forecast."""

    return common


def user_prompt(category_key: str, user_note: str = "") -> str:
    cat = CATEGORIES[category_key]
    base = (
        f"Search for the most important {cat['label']} news from the last 24 hours. "
        f"Focus on: {cat['query']}. "
        "Prioritize stories with global significance and forward-looking implications. "
        "Every story must include a working source_url."
    )
    if user_note:
        base += (
            f"\n\nShun's note: {user_note}\n"
            f"If this relates to {cat['label']}, address it directly — find stories that answer "
            "the question or deepen the context. If unrelated, ignore it."
        )
    return base


def get_today() -> str:
    return datetime.utcnow().strftime("%A, %B %d, %Y")
