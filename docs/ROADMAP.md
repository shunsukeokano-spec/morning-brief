# Roadmap

参照: 改善層の詳細設計は [IMPROVEMENT.md](IMPROVEMENT.md)

## Phase 1: MVP — 毎日の自動収集と蓄積 【最優先】

**ゴール**: 毎朝6:00 JSTに自動で5カテゴリのブリーフが生成・保存される

- [x] `backend/db.py` — SQLiteスキーマ定義とアクセス層（briefs, stories）
- [x] `backend/prompts.py` — カテゴリ別プロンプト
- [x] `backend/collect.py` — Claude API呼び出し + DB保存
- [x] `backend/export.py` — DB → JSON エクスポート
- [x] `.github/workflows/daily-brief.yml` — cron実行
- [ ] `ANTHROPIC_API_KEY` を GitHub Secrets に登録 ← **Shunが手動で設定**
- [x] AI Forecast セクションのプロンプト設計

**完了の定義**: Gitに毎朝 `data/exports/YYYY-MM-DD.json` がコミットされる

## Phase 2: 閲覧UI + シグナル収集インフラ

**ゴール**: 朝起きたら手元で読める + 行動データが蓄積される

### 閲覧UI
- [ ] 既存Artifactベースのフロントエンドを静的サイト化
- [ ] GitHub Pagesにデプロイ
- [ ] 各記事のソース原文へのリンク
- [ ] 過去ブリーフのアーカイブ閲覧
- [ ] メール配信（候補: Resend）

### シグナル収集（コールドスタート対応）
- [ ] `signals` テーブル追加
- [ ] クリック・スクロール・滞在時間の検知（IntersectionObserver, dwell timer）
- [ ] 最初の14日間: 各記事に「興味あり/興味なし/もっと深く」3択タグUI
- [ ] 14日経過後はタグUI自動非表示（手動で消すコマンドも用意）
- [ ] シグナル送信エンドポイント（Cloudflare Workers or GitHub Issues API経由）

**完了の定義**: Webで読めて、行動データが`signals`テーブルに溜まり、コールドスタート期間が機能する

## Phase 3: トレンドクラスタ検出 + 80/15/5 選択

**ゴール**: 「話題のクラスタ」が可視化され、ストーリー選択が好み・トレンド・多様性のバランスを取る

### クラスタリング（収集段階に統合）
- [ ] `entities` `clusters` `story_clusters` テーブル追加
- [ ] `backend/collect.py` を拡張: カテゴリあたり8-10候補を取得
- [ ] エンティティ抽出（Claudeに同一ステップで出させる）
- [ ] 過去30日のクラスタと類似度マッチング
- [ ] クラスタ状態判定: new / continuing / surging / dormant
- [ ] フロントエンド: クラスタバッジ、「continuing N days」、急上昇マーク

### 80/15/5 選択ロジック
- [ ] 候補からの選択ロジック実装
- [ ] 日曜は Serendipity 比率を 30% に引き上げ
- [ ] カバレッジレポート: 「今週触れなかった領域 TOP3」

## Phase 4: 嗜好モデル + 月次自己評価

**ゴール**: 過去のシグナルから嗜好を学習し、月1回 Claude が自身のキュレーションを評価

### 嗜好モデル
- [ ] `entity_interests` テーブル追加
- [ ] EMA でエンティティ興味スコア計算（日次更新）
- [ ] 30日無シグナルのエンティティはスコア半減
- [ ] クラスタ興味スコア = 含まれるエンティティの平均

### 月次自己評価ジョブ
- [ ] `.github/workflows/monthly-review.yml`（毎月1日実行）
- [ ] 予測の答え合わせ（過去30日の `signal` 結果をウェブ検索で検証）
- [ ] `predictions` テーブルに記録
- [ ] 興味偏向監査（スコア分布の可視化）
- [ ] 網羅性監査（漏れた重要トピックの検出）
- [ ] 月次レポートをShunにメール送信

## Phase 5: プロンプト自動改善 + セーフガード

**ゴール**: 月次評価結果から Claude が `prompts.py` を改善し、安全に自動適用

- [ ] `prompts_history` テーブル追加
- [ ] 改善案生成: 過去30日の評価結果から Claude がプロンプト改善案を生成
- [ ] 自動適用: 変更を `prompts.py` にコミット
- [ ] メトリクス記録: 適用前30日 + 適用後7日のクリック率・滞在時間
- [ ] **自動ロールバック**: 7日後にメトリクスが20%以上悪化したら旧版に戻す
- [ ] ロールバック時のメール通知
- [ ] 月次レポートに「今月の変更点」セクション追加

## Phase 6: 音声配信（優先度低）

- [ ] TTSでブリーフを音声化
- [ ] Podcast RSS フィード生成
- [ ] 通勤時間に聞ける形に

## 進捗管理ルール

- Phase内のタスクは順序自由、ただし**Phase完了までは次のPhaseに進まない**
- 1 Phase ≒ 1 PR を目安に
- 各Phase完了時に Shun に動作確認を依頼
- 設計変更が必要になったら `docs/PROJECT.md` を更新してからコード変更
- 改善層に関わる変更は `docs/IMPROVEMENT.md` も同期更新
