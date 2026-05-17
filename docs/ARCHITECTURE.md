# Architecture

## システム全体図

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions (cron: 0 21 * * * UTC = 6:00 JST)        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Python Backend                                    │ │
│  │                                                    │ │
│  │  collect.py                                        │ │
│  │    └─→ Anthropic API (claude-sonnet-4 + web_search)│ │
│  │    └─→ 5カテゴリ並列 (Tech/Politics/Economy/        │ │
│  │         Startups/AI Forecast)                      │ │
│  │    └─→ SQLite (data/briefs.db)                     │ │
│  │                                                    │ │
│  │  analyze.py (週次・月次)                            │ │
│  │    └─→ 過去データから集計                            │ │
│  │    └─→ メタトレンド生成                              │ │
│  │                                                    │ │
│  │  export.py                                         │ │
│  │    └─→ JSON to data/exports/YYYY-MM-DD.json        │ │
│  │    └─→ static HTML to docs/ (GitHub Pages)         │ │
│  │                                                    │ │
│  │  email_send.py                                     │ │
│  │    └─→ Shunにメール送信                              │ │
│  └────────────────────────────────────────────────────┘ │
│           ↓                                              │
│  git add → commit → push                                 │
└─────────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│  GitHub Repository                                       │
│  ├── data/exports/  (日次JSON - 人間可読・Gitで履歴)      │
│  ├── docs/          (静的サイト - GitHub Pages)          │
│  └── data/briefs.db (SQLite - 解析用)                   │
└─────────────────────────────────────────────────────────┘
```

## SQLite スキーマ（案）

```sql
-- 日次ブリーフのメタ情報
CREATE TABLE briefs (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,             -- YYYY-MM-DD
    category TEXT NOT NULL,         -- tech, politics, economy, startups, ai_forecast
    headline TEXT,
    tldr TEXT,
    signal TEXT,                    -- 30-90 day forward-looking insight
    bias_note TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(date, category)
);

-- 個別ストーリー
CREATE TABLE stories (
    id INTEGER PRIMARY KEY,
    brief_id INTEGER REFERENCES briefs(id),
    title TEXT NOT NULL,
    summary TEXT,
    source TEXT,                    -- e.g. "Reuters"
    source_region TEXT,             -- Western/Asia/Middle East/Global South/State Media
    source_url TEXT,                -- ★クリックで原文へ
    significance TEXT,
    trend_signal TEXT,              -- bull/bear/neutral/watch
    created_at TEXT NOT NULL
);

-- エンティティ（Phase 3〜）
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT,                      -- company/person/country/tech
    first_seen TEXT,
    last_seen TEXT
);

CREATE TABLE story_entities (
    story_id INTEGER REFERENCES stories(id),
    entity_id INTEGER REFERENCES entities(id),
    PRIMARY KEY (story_id, entity_id)
);

-- 予測示唆の追跡（Phase 4〜）
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    brief_id INTEGER REFERENCES briefs(id),
    prediction_text TEXT NOT NULL,
    timeframe TEXT,                 -- "30 days", "90 days", etc.
    made_at TEXT NOT NULL,
    resolved_at TEXT,               -- いつ答え合わせしたか
    outcome TEXT                    -- 'correct', 'partial', 'wrong', 'pending'
);

-- フィードバック（Phase 5〜）
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    story_id INTEGER REFERENCES stories(id),
    rating TEXT,                    -- 'useful', 'not_useful'
    created_at TEXT NOT NULL
);
```

## プロンプト設計

`backend/prompts.py` で集中管理。各カテゴリに対して以下を生成：

- `system_prompt`: 役割・バランス要件・出力フォーマット
- `user_prompt`: 当日の検索指示

JSON出力を強制し、`stories[].source_url` を必ず含めるよう指示する。

## GitHub Actions ワークフロー

```yaml
# .github/workflows/daily-brief.yml
name: Daily Brief
on:
  schedule:
    - cron: '0 21 * * *'  # 6:00 JST
  workflow_dispatch:       # 手動実行可

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: python backend/collect.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - run: python backend/export.py
      - name: Commit results
        run: |
          git config user.name "morning-brief-bot"
          git config user.email "bot@users.noreply.github.com"
          git add data/
          git commit -m "Daily brief $(date +%Y-%m-%d)" || exit 0
          git push
```

## セキュリティ

- `ANTHROPIC_API_KEY` は GitHub Secrets で管理
- メールアドレス等の個人情報は `config.toml` ではなく Secrets に
- `data/briefs.db` を Git に含めるかは要検討（含めるとサイズ膨張、含めないと再計算不可）
  - 案: 月次でアーカイブ、最新月のみGit管理

## コスト試算

| 項目 | 月額 |
|------|------|
| GitHub Actions | $0 (public repo or 2000分/月の無料枠) |
| Anthropic API | ~$15 (5カテゴリ × 30日) |
| GitHub Pages | $0 |
| メール送信 (Resend無料枠) | $0 (100通/日まで) |
| **合計** | **~$15/月** |
