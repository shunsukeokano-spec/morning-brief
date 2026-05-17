# Morning Brief

毎朝5〜10分で読める、バイアスバランスの取れたニュースキュレーション + 長期トレンド分析システム。

## 何ができるか

- 毎朝、複数地域・複数視点のニュースを自動収集（GitHub Actionsで実行）
- 4カテゴリのダイジェスト + 独立した「AI Forecast」セクション
- 過去のダイジェストを蓄積し、週次・月次でトレンド分析
- ソースリンク付きでWebアプリ・メール両方で閲覧

## カテゴリ

1. **Technology**（AI動向含む）
2. **Geopolitics**
3. **Economy**
4. **Startups**（資金調達・新興企業）
5. **AI Forecast**（独立セクション：AIで何が可能になるか、将来予測の示唆）

## アーキテクチャ

```
GitHub Actions (cron 毎朝6:00 JST)
        ↓
  Python Backend
  - Claude APIでウェブ検索 + 要約
  - SQLiteに蓄積
  - 週次トレンド分析
        ↓
  ┌───────────┬───────────┐
  ↓           ↓           ↓
JSONエクスポート    メール送信   静的サイト生成
  ↓                          (GitHub Pages)
Frontend (React)
```

## ドキュメント

- [docs/PROJECT.md](docs/PROJECT.md) — プロジェクトの目的・要件・設計判断
- [docs/ROADMAP.md](docs/ROADMAP.md) — 開発フェーズと優先順位
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — システム構成の詳細
- [CLAUDE.md](CLAUDE.md) — Claude Code向け開発指示書

## 起動方法

### 初期セットアップ（ローカル）

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python collect.py
```

### Claude Codeで開発を継続する

```bash
cd morning-brief
claude
```

Claude Codeは自動的に `CLAUDE.md` を読み、プロジェクト方針を理解した状態で起動します。次にやるべきことは [docs/ROADMAP.md](docs/ROADMAP.md) を参照。
