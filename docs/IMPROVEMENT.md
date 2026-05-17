# Continuous Improvement Layer

このドキュメントは「継続的に自己改善するシステム」の設計を定義する。
Shun の要望（明示フィードバック不要、自動改善、コールドスタート期間あり、トレンド重視）に基づく。

## 設計の中核：4つの要求とその実現方法

| Shun の要求 | 実現方法 |
|-------------|---------|
| 1. 好みに合わせたトピックをピックアップ | エンティティ単位の興味スコア（受動シグナルから学習） |
| 2. トレンドを見逃さない | 収集段階で「話題のクラスタ」を検出し関連性可視化 |
| 3. 関心外も週1回 | 日曜に Serendipity Day（強制的に低スコア領域から1記事） |
| 4. 入力最小で継続改善 | 受動シグナル + 自動プロンプト改善（月1回） |

## アーキテクチャ

```
┌────────────────────────────────────────────────────┐
│ Layer 4: 月次自己評価                                │
│  - 予測の答え合わせ                                  │
│  - 興味偏向監査                                      │
│  - プロンプト自動改善（セーフガード付き）              │
└────────────────────────────────────────────────────┘
                       ↑
┌────────────────────────────────────────────────────┐
│ Layer 3: 嗜好モデル                                  │
│  - エンティティ単位の興味スコア（指数移動平均）         │
│  - クラスタ単位の興味スコア                          │
└────────────────────────────────────────────────────┘
                       ↑
┌────────────────────────────────────────────────────┐
│ Layer 2: ストーリー選択（毎朝）                       │
│  80% パーソナライズ + 15% トレンド + 5% Serendipity │
└────────────────────────────────────────────────────┘
                       ↑
┌────────────────────────────────────────────────────┐
│ Layer 1: 収集段階の改善                              │
│  - 広めに収集（カテゴリあたり 8-10 候補）             │
│  - クラスタリングでテーマ統合                         │
│  - 過去 N 日のクラスタとマッチング                    │
└────────────────────────────────────────────────────┘
                       ↑
┌────────────────────────────────────────────────────┐
│ Layer 0: 受動シグナル収集                            │
│  - クリック・滞在時間・スクロール                     │
│  - コールドスタート期間（最初2週間）のみ明示タグ        │
└────────────────────────────────────────────────────┘
```

---

## Layer 0: 受動シグナル

### シグナル定義

| イベント | 重み | 取得方法 |
|---------|------|---------|
| story_clicked（ソースリンク クリック） | +3 | Webアプリ |
| story_scrolled_to_end（最後まで読んだ） | +1 | IntersectionObserver |
| panel_dwell_long（10秒以上滞在） | +1 | 滞在タイマー |
| panel_skipped_3days（3日連続未閲覧） | -2 | 日次ジョブで集計 |
| brief_email_opened（メール開封） | +0.5 | トラッキングピクセル |

### コールドスタート（最初の14日間）

各記事の下に小さな UI を表示：
- 「興味あり」「興味なし」「もっと深く」の3択チェック
- これらは `+5 / -5 / +10` 相当として記録
- 14日経過後は UI 自動非表示
- `cold_start_end_date` を config に保持

### 実装

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    story_id INTEGER REFERENCES stories(id),
    signal_type TEXT NOT NULL,  -- clicked|scrolled|dwelled|skipped|explicit_yes|explicit_no|explicit_more
    weight REAL NOT NULL,
    created_at TEXT NOT NULL
);
```

Web アプリから `POST /api/signal` で記録するシンプルなエンドポイントを Phase 2 で実装。
（GitHub Pages は静的なので、シグナル収集には別途 Cloudflare Workers などを使うか、
localStorage に貯めてから定期的に GitHub Issues 経由で送信する案あり → Phase 2 で決定）

---

## Layer 1: トレンドクラスタ検出（中核機能）

これが Shun の要求の一番面白い部分です。

### 流れ

1. **広めに収集**: カテゴリあたり 8〜10 記事候補を Claude に出させる
2. **エンティティ抽出**: 各候補から企業名・人名・国名・技術名を抽出
3. **クラスタリング**: 共通エンティティの多い記事同士をクラスタ化
4. **過去クラスタとマッチング**: 過去 30 日のクラスタと類似度比較
5. **クラスタ強度判定**:
   - **新規**: 過去にない → 「new」タグ
   - **継続**: 過去に出ていた → 「continuing N days」タグ
   - **急上昇**: 過去3日で記事数が急増 → 「surging」タグ
   - **衰退**: 過去はあったが今日少ない → 表示候補から除外
6. **代表記事の選定**: 各クラスタから 1〜2 本選んでブリーフへ

### スキーマ

```sql
CREATE TABLE clusters (
    id INTEGER PRIMARY KEY,
    theme TEXT NOT NULL,            -- Claudeが命名: "China-Taiwan semiconductor tensions"
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    total_stories INTEGER DEFAULT 0,
    status TEXT                     -- new|continuing|surging|dormant
);

CREATE TABLE story_clusters (
    story_id INTEGER REFERENCES stories(id),
    cluster_id INTEGER REFERENCES clusters(id),
    PRIMARY KEY (story_id, cluster_id)
);
```

### 表示への反映

各ストーリーカードに：
- クラスタ名（バッジ表示）
- 「continuing 5 days」のような継続情報
- ↗ 急上昇マーク（surging クラスタ）
- 関連過去記事へのリンク

---

## Layer 2: ストーリー選択（80/15/5 ルール）

毎朝、各カテゴリで 3〜4 ストーリーを選ぶときの配分：

```python
def select_stories(candidates, target_count=4):
    # 80%: パーソナライズ（興味スコアの高いエンティティを含む）
    personalized = sorted(candidates, key=interest_score, reverse=True)[:int(target_count * 0.8)]

    # 15%: トレンド（surging クラスタの代表記事）
    surging = [c for c in candidates if c.cluster_status == "surging"]
    trending = surging[:max(1, int(target_count * 0.15))]

    # 5%: Serendipity（興味スコア低めだが重要なもの、ランダム）
    if today.weekday() == 6:  # 日曜
        # Serendipity Day: 比率を上げる（30%）
        low_interest = [c for c in candidates if interest_score(c) < THRESHOLD]
        serendipity = random.sample(low_interest, min(2, len(low_interest)))
    else:
        serendipity = random.sample(candidates, 1) if random.random() < 0.05 else []

    return dedupe(personalized + trending + serendipity)[:target_count]
```

### Serendipity Day（毎週日曜）

- 通常 5% → 30% に引き上げ
- 「今週あなたが触れなかった領域」をカバレッジレポートで明示
- フッターに「今日は意図的に幅広く選んでいます」のバナー

---

## Layer 3: 嗜好モデル

### エンティティ興味スコア

```python
# 指数移動平均（EMA）
new_score = 0.9 * old_score + 0.1 * recent_signal_sum

# 時間減衰: 30日間シグナルがないエンティティはスコア半減
if days_since_last_signal > 30:
    score *= 0.5
```

シンプルだが効果的。複雑なベイズや行列分解は不要（データ量的にも）。

### クラスタ興味スコア

クラスタに含まれる全エンティティの興味スコア平均。

### スキーマ

```sql
CREATE TABLE entity_interests (
    entity_id INTEGER PRIMARY KEY REFERENCES entities(id),
    score REAL DEFAULT 0,
    last_updated TEXT NOT NULL,
    signal_count INTEGER DEFAULT 0
);
```

---

## Layer 4: 月次自己評価（自動プロンプト改善）

### 月1回（毎月1日）、Claudeが以下を実行：

#### 4-1. 予測の答え合わせ

過去30日の各ブリーフの `signal` フィールド（30〜90日予測）を取り出し、
ウェブ検索で「実際にどうなったか」を確認。`predictions` テーブルに結果を記録。

#### 4-2. 興味偏向監査

過去30日のストーリーから、Shun の興味スコアの分布を分析：
- どの領域に偏っているか
- 触れなかった重要トピックは何か
- Serendipity Day は機能しているか

#### 4-3. 網羅性監査

「過去30日で出るべきだったが出なかった重要ニュース」をClaude が検出：
- 主要メディアのトップ記事と照合
- 自分のキュレーションの抜けを発見

#### 4-4. プロンプト自動改善

上記を踏まえて Claude が `prompts.py` の改善案を生成し、自動適用。

### セーフガード（重要）

```python
# prompts_history テーブル
CREATE TABLE prompts_history (
    id INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    category TEXT NOT NULL,
    old_prompt TEXT NOT NULL,
    new_prompt TEXT NOT NULL,
    reason TEXT NOT NULL,
    metrics_before JSON,
    metrics_7d_after JSON,
    rolled_back_at TEXT  -- NULL if still active
);
```

**自動ロールバック条件**:
- 適用後7日間の以下のいずれかが悪化（前30日平均比）:
  - ストーリークリック率が 20% 以上低下
  - パネル滞在時間平均が 20% 以上低下
  - エラー率が増加

ロールバック時は Shun に「自動ロールバックしました」とメール通知。

**月次レポート**:
毎月の改善で何を変えたか、Shun にダイジェスト送信。
「気に入らなければ手動で戻せる」よう、ロールバック用コマンドも明記。

---

## 実装フェーズ（ROADMAP統合）

| フェーズ | 対応する Layer |
|---------|---------------|
| Phase 1 | Layer 1 の収集機能のみ（クラスタリングなし） |
| Phase 2 | Layer 0 のシグナル収集インフラ + コールドスタート UI |
| Phase 3 | Layer 1 のクラスタリング + Layer 2 のストーリー選択 |
| Phase 4 | Layer 3 の嗜好モデル + Layer 4 の月次自己評価 |
| Phase 5 | Layer 4 のプロンプト自動改善 + セーフガード |

順序を入れ替えてはいけない理由：
- Layer 0（シグナル）がないと Layer 3（嗜好）が学習できない
- Layer 1（クラスタ）がないと Layer 2（選択）の "trend" 軸が動かない
- Layer 4（自動改善）は他全部のメトリクスが揃ってから

## やってはいけないこと

- 嗜好モデルの「興味なし」シグナルだけでカテゴリ全体を遮断しない（フィルターバブル防止）
- Serendipity Day をオプトアウト可能にしない（Shun の要求の本質）
- プロンプト自動改善のロールバック機能を省略しない
- コールドスタート期間を「絶対」にしない（Shun が早く UI を消したくなったら消せるように）
