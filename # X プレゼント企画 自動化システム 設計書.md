# X プレゼント企画 自動化システム 設計書

## 1. システム概要

Xのプレゼント企画を**月2回・完全自動**で運用するシステム。
トレンド調査 → コンテンツ作成 → X投稿 → エンゲージメント監視 → 自動プレゼント配布を一気通貫で実行する。
人間の介入は一切不要。

### コンテンツ構成

| 種別 | プラットフォーム | 内容 |
|------|----------------|------|
| 無料記事 | **Note** | 2000-3000文字の価値ある記事。リプで配布 |
| 引用RT特典 | **Notion** | テンプレート/チェックリスト等の実践的コンテンツ |

### 役割分担

| レイヤー | 担当 | 内容 |
|---------|------|------|
| **調査・コンテンツ作成** | **Claude Code** | トレンド調査(X API+Note/Brain+WebSearch)、テーマ選定、Note記事執筆(Playwright)、画像生成(nanobanana)、Notion特典作成、X投稿文作成を一括実行 |
| **監視・配布** | **n8n** | リプライ/引用RT監視、リプライ+Hide Reply配布、ログ管理 |
| **投稿実行** | **n8n (既存)** | 予約投稿の自動実行 |

### 全体フロー図

```
[Phase 1: 調査 & コンテンツ作成] ── Claude Code が一括実行
  ┌──────────────────────────────────────────────────────┐
  │ n8n: Schedule Trigger (月2回: 第1・第3月曜)           │
  │   └→ SSH → Claude Code 起動                          │
  │                                                       │
  │ Claude Code が自律的に以下を実行:                      │
  │   ① X APIで自分のジャンルのトレンド調査               │
  │   ② Note/Brainの人気記事テーマ調査 + WebSearchリサーチ │
  │   ③ テーマ選定 & 企画設計                             │
  │   ④ 画像生成 (サムネ+挿入画像: nanobanana/Gemini)      │
  │   ⑤ 無料Note記事の執筆 & Playwright自動公開           │
  │   ⑥ 引用RT特典の作成 (Notion)                        │
  │   ⑦ X投稿5本の作成 → Google Sheetsに予約登録          │
  └───────────────┬──────────────────────────────────────┘
                  ▼
[Phase 2: X投稿]
  ┌──────────────────────────────────────────────────────┐
  │ n8n: 予約投稿実行フロー (既存フロー流用)              │
  │   Google Sheets → 予定時刻に自動投稿                  │
  │   ※ 投稿後、giveaway_tweet_id を企画管理シートに記録  │
  └───────────────┬──────────────────────────────────────┘
                  ▼
[Phase 3: 監視 & プレゼント配布] ── n8n が実行
  ┌──────────────────────────────────────────────────────┐
  │ n8n: リプライ監視フロー (5分間隔)                     │
  │   X API v2 → リプ検出 → リプライ送信 → Hide Reply     │
  │   ※相手に通知は届くが、スレッドでは非表示             │
  └──────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────┐
  │ n8n: 引用RT監視フロー (5分間隔)                       │
  │   X API v2 → 引用RT検出 → リプライ送信 → Hide Reply   │
  │   ※感想付き引用RTに特典を配布                        │
  └──────────────────────────────────────────────────────┘
```

---

## 2. API戦略

### 2.1 X API v2 従量課金プラン (Pay-Per-Use)

従量課金プランを使用するため、月間読取上限の制約なし。
X API v2を直接使用してリプライ・引用RTの監視を行う。

```
┌──────────────────────────────────────────────────────┐
│  X API v2 (従量課金)                                   │
│  ・リプライ検索 (GET /2/tweets/search/recent)          │
│  ・引用RT取得 (GET /2/tweets/{id}/quote_tweets)        │
│  ・トレンド調査 (GET /2/tweets/search/recent)          │
│  ・ツイート投稿 (POST /2/tweets)                       │
│  ・Hide Reply (PUT /2/tweets/{id}/hidden)              │
│  ・メトリクス取得 (GET /2/tweets)                      │
├──────────────────────────────────────────────────────┤
│  twitterapi.io (補助)                                  │
│  ・advanced_search (高度な検索クエリ)                   │
│  ・既存フローとの互換性維持                             │
│  ※ X API v2 で対応できない検索が必要な場合に使用       │
└──────────────────────────────────────────────────────┘
```

### 2.2 API使い分け一覧

| 操作 | 使うAPI | エンドポイント |
|------|---------|---------------|
| トレンド調査 | X API v2 | GET /2/tweets/search/recent |
| 自分の過去投稿取得 | X API v2 | GET /2/users/{id}/tweets |
| リプライ監視 | X API v2 | GET /2/tweets/search/recent (conversation_id) |
| 引用RT監視 | X API v2 | GET /2/tweets/{id}/quote_tweets |
| ツイート投稿 | X API v2 | POST /2/tweets |
| リプライ投稿 | X API v2 | POST /2/tweets (reply) |
| Hide Reply | X API v2 | PUT /2/tweets/{id}/hidden |
| メトリクス取得 | X API v2 | GET /2/tweets (public_metrics) |
| 高度な検索 | twitterapi.io | advanced_search (既存フロー互換) |

### 2.3 レート制限の注意点

| エンドポイント | 制限 |
|---------------|------|
| 検索 (recent) | 450回/15分 (app) / 180回/15分 (user) |
| 引用RT取得 | 75回/15分 |
| ツイート投稿 | 100回/15分 (user) / 10,000回/24h (app) |
| Hide Reply | 50回/15分 |

5分間隔ポーリング × 2企画同時 = 最大2回/5分 → どのエンドポイントも余裕。

---

## 3. Hide Reply 方式の設計

### 3.1 仕組み

X API の `PUT /2/tweets/{tweet_id}/hidden` を使用。

**配布フロー:**
1. ユーザーが企画ツイートにリプライ（「欲しい！」等）
2. **自分の企画ツイートに対して** `@ユーザー名 プレゼントはこちら→{URL}` とリプライ
3. 即座に `PUT /2/tweets/{リプライID}/hidden` で非表示化
4. ユーザーには**@メンション通知が届く**（リンク付き）
5. 他のユーザーからは**スレッドで見えない**

```
[企画ツイート] (by こま)
  ├── [ユーザーAのリプ] 「欲しいです！」
  ├── [ユーザーBのリプ] 「ください！」
  ├── [こまのリプ → 即非表示] 「@UserA こちらからどうぞ→ https://...」  ← Hidden
  └── [こまのリプ → 即非表示] 「@UserB こちらからどうぞ→ https://...」  ← Hidden
```

### 3.2 重要な設計ポイント

| 項目 | 内容 |
|------|------|
| **リプライ先** | 必ず**自分の企画ツイート**にリプライする（ユーザーのリプへの返信ではない）|
| **理由** | Hide Replyは「そのツイートの投稿者」しか実行できない。自分のツイートへのリプだから非表示にできる |
| **通知** | @メンション通知で相手に届く。非表示にしても通知は消えない |
| **パーマリンク** | 直接URLなら見える（受取者は通知から辿れる） |
| **レート制限** | Hide: 50回/15分、投稿: 100回/15分 → 十分余裕 |
| **必要スコープ** | `tweet.read`, `users.read`, `tweet.write`, `tweet.moderate.write` |

---

## 4. n8nワークフロー一覧

### 新規作成

| # | ワークフロー名 | トリガー | 目的 |
|---|---------------|---------|------|
| WF1 | 企画パイプライン起動 | Schedule (第1・第3水曜 5:00) | SSH→Claude Codeで調査〜コンテンツ作成を一括実行 (公開日の2日前) |
| WF2 | 投稿ID記録 | 既存予約投稿フローの後続 | 投稿完了時にgiveaway_tweet_idを企画管理シートに記録 |
| WF3 | リプライ監視 & Note配布 | Schedule (5分間隔) | X API v2でリプ検出→リプライ+Hide Reply |
| WF4 | 引用RT監視 & 特典配布 | Schedule (5分間隔) | X API v2で引用RT検出→リプライ+Hide Reply |
| WF5 | 配布レポート | Schedule (日次 22:00) | 配布状況集計→Discord/LINE通知 |
| WF6 | 企画自動終了 & Note有料化 | Schedule (日次 0:00) | end_date到達→Note有料化/非公開→status完了 |

### 既存フロー流用

| 既存フロー | 流用箇所 |
|-----------|---------|
| X投稿予約設定フロー | Google Sheetsへの予約登録 |
| X予約投稿実行フロー | 予定時刻の自動投稿 |

---

## 5. 各コンポーネント詳細設計

### 5.1 WF1: 企画パイプライン起動フロー (n8n → Claude Code)

n8nはトリガーとSSH起動のみ。全処理はClaude Codeが自律実行。

```
Schedule Trigger (第1水曜・第3水曜 5:00 AM)  ← 公開日(金)の2日前
    │
    └──→ [SSH] Claude Code パイプライン起動
          cd /root/koma-x-automation && bash scripts/pipeline_giveaway.sh
```

### 5.2 Claude Code パイプラインスクリプト (VPS)

`pipeline_giveaway.sh` が Claude Code を起動し、以下を**1回の実行で自律的に**すべて完了させる。

```bash
#!/bin/bash
# pipeline_giveaway.sh
# Claude Codeがプレゼント企画の全工程を自律実行する
set -euo pipefail

CONFIG=$(cat config/giveaway_config.json)
PROMPT=$(cat templates/giveaway_prompt.md)

# Claude Codeを起動して全工程を実行
claude --print --model claude-sonnet-4-6 --max-tokens 16000 "$PROMPT"
```

**Claude Codeに渡すプロンプト (`templates/giveaway_prompt.md`):**

```markdown
あなたはXプレゼント企画の自動運用システムです。
以下の8ステップを順番に実行し、すべての成果物を作成してください。
各ステップでは実際にAPIを呼び出して処理を完了させてください。

---

## Step 1: Xトレンド調査

自分の発信ジャンル（AI・自動化・n8n・Claude・副業）のXトレンドを調査する。
X API v2を使用。

### 1-1. ジャンル内の話題投稿を取得
curl -s -H "Authorization: Bearer $X_BEARER_TOKEN" \
  "https://api.x.com/2/tweets/search/recent?query=(AI OR ChatGPT OR Claude OR 自動化 OR n8n) lang:ja&max_results=50&tweet.fields=public_metrics,created_at&sort_order=relevancy"

### 1-2. 自分の過去投稿で反応が良かったものを取得
curl -s -H "Authorization: Bearer $X_BEARER_TOKEN" \
  "https://api.x.com/2/users/$X_USER_ID/tweets?max_results=20&tweet.fields=public_metrics,created_at&exclude=replies,retweets"

### 1-3. 競合・同ジャンルの人気アカウントの最新投稿を取得
同ジャンルで影響力のあるアカウント数名の最新投稿を取得し、どんなテーマが反応を得ているか分析。

## Step 2: Note/Brain 人気記事テーマ調査

WebFetchを使って、Note・Brainで売れている/伸びている記事のテーマを調査する。

### 2-1. Note 人気記事の取得
- note.com のカテゴリ別人気記事ページをスクレイピング
  - https://note.com/topic/technology (テクノロジー)
  - https://note.com/topic/business (ビジネス)
  - https://note.com/search?q=AI+自動化&sort=popular (検索: 人気順)
- 売れている有料記事のタイトル・テーマ・価格帯を収集

### 2-2. Brain 人気記事の取得
- brain-market.com のランキングページをスクレイピング
  - トップページの売れ筋ランキング
  - カテゴリ別の人気コンテンツ
- 売れているテーマ・切り口・価格帯を収集

### 2-3. トレンドテーマ抽出
Note/Brainで今売れているテーマの共通点を分析:
- どんなキーワードが使われているか
- どんな切り口（テンプレート、ロードマップ、完全ガイド等）が売れているか
- 自分のジャンルとの接点はどこか

## Step 3: 最新情報リサーチ (WebSearch)

Step 1-2で特定したトレンドに関連する最新情報をWebSearchで調査。
- 海外テック系サイトから最新のAI/自動化ニュース
- 日本ではまだ知られていない情報を優先
- 実践的なノウハウ・テクニックを重点的に収集

## Step 4: テーマ選定 & 企画設計

Step 1-3の結果を統合分析し、最もバズりやすいテーマを1つ選定:

**選定基準:**
- Xで直近エンゲージメントが高いトピック
- Note/Brainで売れている切り口との親和性
- 「無料で欲しい」と思わせる具体的価値
- 感想を書きやすい（引用RTのハードルが低い）
- 自分の過去投稿で反応が良かったジャンルとの親和性

**決定事項:**
- テーマ名
- 無料Note記事のタイトル・構成
- Notion特典のタイトル・内容
- X告知投稿の方向性

## Step 5: 画像生成 (nanobanana / Gemini API)

記事の各パートを分析し、必要な画像を判定して自動生成する。

### 5-1. 必要な画像の判定
記事構成を分析し、以下を判定:
- **サムネイル** (必ず1枚): 記事タイトルを映えるデザインで
- **手順説明パート** → ステップ図解イラスト
- **概念説明パート** → コンセプトイメージ
- **比較・まとめパート** → 比較図・インフォグラフィック

### 5-2. 各画像のプロンプト生成 & API呼び出し
画像ごとに最適なプロンプトを生成し、Gemini APIで画像生成:

curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "画像プロンプト"}]}],
    "generationConfig": {"responseModalities": ["IMAGE"]}
  }'

### 5-3. 画像の保存
base64レスポンスをデコードしてPNG保存:
- /tmp/giveaway_{campaign_id}/thumbnail.png
- /tmp/giveaway_{campaign_id}/section_1.png
- /tmp/giveaway_{campaign_id}/section_2.png ...

## Step 6: 無料Note記事の作成 & Playwright自動公開

### 6-1. 記事の執筆
- 2000-3000文字
- 読みやすい「です・ます」調
- 具体例・ステップを多用
- Step 5で生成した画像を適切な位置に配置
- 最後にCTA:

  ---
  ここまで読んでいただきありがとうございます！

  この記事が参考になったら、感想を添えて元ポストを引用RTしてください。
  引用RTしてくれた方全員に【特典名】をプレゼントします！

### 6-2. PlaywrightでNote自動公開
Noteには公開APIがないため、Playwrightでブラウザ操作して記事を公開する。

```python
# note_publisher.py (VPS上で実行)
from playwright.async_api import async_playwright
import asyncio

async def publish_note(title, body_html, thumbnail_path, cookies_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=cookies_path)
        page = await context.new_page()

        # 1. Note新規作成ページへ
        await page.goto("https://note.com/notes/new")

        # 2. サムネイル画像をアップロード
        await page.set_input_files('input[type="file"]', thumbnail_path)

        # 3. タイトル入力
        await page.fill('[placeholder*="タイトル"]', title)

        # 4. 本文入力 (リッチエディタにHTML挿入)
        # ※ Noteのエディタ仕様に合わせて実装
        editor = page.locator('[contenteditable="true"]')
        await editor.click()
        # 各セクションと画像を順番に挿入

        # 5. 公開設定
        await page.click('text=公開')  # 公開ボタン
        # 無料記事として公開

        # 6. 公開後のURLを取得
        await page.wait_for_url("**/n/**")
        note_url = page.url

        await browser.close()
        return note_url
```

**Playwrightでの注意点:**
- Noteのログインセッション (cookies) を事前に保存しておく
- VPSにChromium + 日本語フォントをインストール
- Noteの仕様変更で壊れる可能性 → エラー時にDiscord/LINE通知

→ 公開URLを記録: note_url

## Step 7: Notion特典の作成

Note記事よりさらに深い内容のNotionページを作成。
形式: テンプレート / チェックリスト / 実践ガイド / ロードマップ等

### 7-1. Notion APIでページ作成
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"database_id": "'$NOTION_GIVEAWAY_DB_ID'"},
    "properties": {...},
    "children": [...]
  }'

### 7-2. 共有リンクを取得
作成したページの共有設定を公開に変更し、URLを記録: bonus_url

## Step 8: X投稿5本の作成 & Google Sheets予約登録

以下5本の投稿文を作成。公開日 (Day 0) を基準とする。

### 投稿① 予告 (Day -2, 12:00)
「近日公開」のティーザー投稿。テーマをチラ見せして期待感を煽る。
Noteリンクなし。「〇〇についてまとめてます。お楽しみに」的な。

### 投稿② 前日告知 (Day -1, 12:00)
「明日公開」の告知。もう少し具体的な内容を出す。
「明日、〇〇をまとめた記事を無料公開します。リプで受け取れます」

### 投稿③ 公開 (Day 0, 12:00) ← メイン企画ツイート ★
プレゼント企画の本投稿。Noteリンク付き。
「リプで無料Note受け取り」「感想を引用RTで追加特典」を明記。
この投稿のIDが giveaway_tweet_id になる。

### 投稿④ 社会的証明 (Day +1, 20:00)
「たくさんの感想が届いています！」的な投稿。
反応の良さを伝えつつ、まだ受け取ってない人への再告知。
「感想がたくさん届いてます！まだの方はリプで受け取れます」

### 投稿⑤ 最終日告知 (Day +3, 12:00)
「今日の23:59で無料公開終了です」のFOMO投稿。
「終了後は有料になります。まだの方は今日中にリプしてください」

### タイムライン

```
Day -2 (12:00)  投稿① 予告ティーザー
Day -1 (12:00)  投稿② 明日公開の告知
Day  0 (12:00)  投稿③ 公開 & プレゼント開始 ★ ← 監視開始
Day +1 (20:00)  投稿④ 社会的証明 (感想届いてます)
Day +3 (12:00)  投稿⑤ 最終日告知 (今日23:59で終了)
Day +3 (23:59)  → Note有料化 or 非公開化 & 企画終了
```

### Google Sheets APIで予約登録
投稿予約シートに5件を登録:
curl -s -X POST \
  "https://sheets.googleapis.com/v4/spreadsheets/$SHEET_ID/values/X投稿予約シート:append?valueInputOption=USER_ENTERED" \
  -H "Authorization: Bearer $GOOGLE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"values": [
    ["Ready", "予告テキスト", "YYYY/MM/DD 12:00:00", "", "campaign_id"],
    ["Ready", "前日告知テキスト", "YYYY/MM/DD 12:00:00", "", "campaign_id"],
    ["Ready", "公開テキスト", "YYYY/MM/DD 12:00:00", "", "campaign_id_main"],
    ["Ready", "社会的証明テキスト", "YYYY/MM/DD 20:00:00", "", "campaign_id"],
    ["Ready", "最終日テキスト", "YYYY/MM/DD 12:00:00", "", "campaign_id"]
  ]}'

※ 投稿③ (公開ツイート) の campaign_id に "_main" を付与して、
  WF2でgiveaway_tweet_idとして記録する対象を識別する。

### 企画管理シートに登録
campaign_id, theme, note_url, bonus_url, bonus_title,
giveaway_tweet_id="(投稿③完了後に自動記録)", status="active",
start_date (Day 0), end_date (Day +3 23:59),
reply_since_id="0", quote_since_id="0"

---

## 最終出力

全ステップの実行結果をJSON形式で出力:
{
  "campaign_id": "giveaway_YYYYMMDD",
  "theme": "テーマ名",
  "note_url": "https://note.com/...",
  "bonus_url": "https://notion.so/...",
  "bonus_title": "特典タイトル",
  "tweets_scheduled": 5,
  "tweet_schedule": {
    "teaser": "YYYY-MM-DD 12:00",
    "pre_announce": "YYYY-MM-DD 12:00",
    "main": "YYYY-MM-DD 12:00",
    "social_proof": "YYYY-MM-DD 20:00",
    "last_day": "YYYY-MM-DD 12:00"
  },
  "end_datetime": "YYYY-MM-DD 23:59",
  "status": "success"
}
```

---

### 5.3 WF2: 投稿ID記録フロー (n8n)

既存の予約投稿実行フローの後続。投稿完了時にgiveaway_tweet_idを企画管理シートに書き戻す。

```
[既存: X予約投稿実行フロー] ── 投稿完了
    │
    ├──→ [If] campaign_id が存在するか？
    │     ↓ Yes
    ├──→ [Google Sheets] 企画管理シートを更新
    │     Filter: campaign_id = {投稿のcampaign_id}
    │     Update: giveaway_tweet_id = {投稿で返されたtweet_id}
    │
    └──→ End
```

---

### 5.4 WF3: リプライ監視 & Note配布フロー (n8n)

**読取・書き込みともX API v2を使用（従量課金）。**

```
Schedule Trigger (5分間隔)
    │
    ├──→ [Google Sheets] アクティブ企画を取得
    │     Filter: status="active", giveaway_tweet_id が空でない
    │     取得: campaign_id, giveaway_tweet_id, note_url, reply_since_id
    │
    ├──→ [X API v2] リプライ検索
    │     GET https://api.x.com/2/tweets/search/recent
    │     query: "conversation_id:{giveaway_tweet_id} -from:{自分のID}"
    │     since_id: {reply_since_id}
    │     tweet.fields: author_id,created_at,text,conversation_id
    │     expansions: author_id
    │     user.fields: username
    │     Auth: OAuth 2.0 (こまアカウント)
    │
    ├──→ [If] リプライが0件なら終了
    │
    ├──→ [Google Sheets] 配布済みチェック
    │     配布ログシートで user_id + campaign_id が存在するか確認
    │     → 重複配布を防止
    │
    ├──→ [Filter] 未配布ユーザーのみ残す
    │
    ├──→ [Loop Over Items] 1件ずつ処理
    │     │
    │     ├──→ [X API v2] 自分の企画ツイートにリプライ  ← 書き込み
    │     │     POST https://api.x.com/2/tweets
    │     │     Auth: OAuth 2.0 (こまアカウント)
    │     │     {
    │     │       "text": "@{username} プレゼントをお届けします！\n\n{note_url}\n\n感想を引用RTしてくれたら追加特典もプレゼントします！",
    │     │       "reply": {
    │     │         "in_reply_to_tweet_id": "{giveaway_tweet_id}"
    │     │       }
    │     │     }
    │     │     → response.data.id を取得 (= reply_tweet_id)
    │     │
    │     ├──→ [X API v2] Hide Reply  ← 書き込み
    │     │     PUT https://api.x.com/2/tweets/{reply_tweet_id}/hidden
    │     │     Auth: OAuth 2.0 (こまアカウント)
    │     │     {"hidden": true}
    │     │
    │     ├──→ [Google Sheets] 配布ログ記録
    │     │     campaign_id, user_id, username, "reply", "note",
    │     │     "hide_reply", now(), source_tweet_id, reply_tweet_id
    │     │
    │     └──→ [Wait] 3秒
    │
    └──→ [Google Sheets] reply_since_id 更新
          最新のtweet_idを企画管理シートに保存
```

**n8nノード構成 (実装時の参考):**

```
[Schedule Trigger: 5分]
    ↓
[Google Sheets: Get Rows] ← 企画管理シート (status=active)
    ↓
[HTTP Request] ← X API v2 GET /2/tweets/search/recent (リプライ検索)
    ↓
[If: データあり?]
    ↓ Yes
[Split Out] ← リプライを1件ずつに
    ↓
[Google Sheets: Lookup] ← 配布ログで重複チェック
    ↓
[If: 未配布?]
    ↓ Yes
[HTTP Request] ← X API v2 POST /2/tweets (リプライ作成)
    ↓
[HTTP Request] ← X API v2 PUT /2/tweets/{id}/hidden (非表示化)
    ↓
[Google Sheets: Append] ← 配布ログ記録
    ↓
[Wait: 3秒]
    ↓ (Loop終了後)
[Google Sheets: Update] ← since_id更新
```

---

### 5.5 WF4: 引用RT監視 & 特典配布フロー (n8n)

WF3とほぼ同構造。検索クエリと配布内容が異なる。

```
Schedule Trigger (5分間隔)
    │
    ├──→ [Google Sheets] アクティブ企画を取得
    │     取得: campaign_id, giveaway_tweet_id, bonus_url, bonus_title, quote_since_id
    │
    ├──→ [X API v2] 引用RT取得
    │     GET https://api.x.com/2/tweets/{giveaway_tweet_id}/quote_tweets
    │     since_id: {quote_since_id}
    │     tweet.fields: author_id,created_at,text
    │     expansions: author_id
    │     user.fields: username
    │     max_results: 100
    │     Auth: OAuth 2.0 (こまアカウント)
    │
    ├──→ [If] 引用RTが0件なら終了
    │
    ├──→ [Filter] 感想付き判定
    │     テキストの文字数 > 20文字 (URL・引用部分を除く)
    │
    ├──→ [Google Sheets] 特典配布済みチェック
    │     配布ログ: user_id + campaign_id + content="bonus"
    │
    ├──→ [Loop Over Items] 1件ずつ処理
    │     │
    │     ├──→ [X API v2] 自分の企画ツイートにリプライ
    │     │     POST https://api.x.com/2/tweets
    │     │     {
    │     │       "text": "@{username} 引用RTありがとうございます！\n特典の【{bonus_title}】はこちらです↓\n\n{bonus_url}",
    │     │       "reply": {
    │     │         "in_reply_to_tweet_id": "{giveaway_tweet_id}"
    │     │       }
    │     │     }
    │     │
    │     ├──→ [X API v2] Hide Reply
    │     │     PUT /2/tweets/{reply_tweet_id}/hidden
    │     │     {"hidden": true}
    │     │
    │     ├──→ [Google Sheets] 配布ログ記録
    │     │     campaign_id, user_id, username, "quote_rt", "bonus",
    │     │     "hide_reply", now(), quote_tweet_id, reply_tweet_id
    │     │
    │     └──→ [Wait] 3秒
    │
    └──→ [Google Sheets] quote_since_id 更新
```

---

### 5.6 WF5: 配布レポートフロー (n8n)

```
Schedule Trigger (毎日 22:00)
    │
    ├──→ [Google Sheets] アクティブ企画の配布ログ集計
    │     ・Note配布数 / 特典配布数
    │     ・本日の新規配布数
    │
    ├──→ [X API v2] 企画ツイートのメトリクス取得
    │     GET https://api.x.com/2/tweets?ids={giveaway_tweet_id}
    │     tweet.fields: public_metrics
    │     → impressions, likes, retweets, quotes, bookmarks
    │
    ├──→ [Code] レポート整形
    │
    └──→ [通知] Discord / LINE に送信
          「【プレゼント企画レポート】
           テーマ: {theme}
           配布: Note {X}件 / 特典 {Y}件 (本日+{Z}件)
           imp: {A} / いいね: {B} / RT: {C} / 引用: {D}
           残り: {E}日」
```

### 5.7 WF6: 企画自動終了 & Note有料化フロー (n8n)

企画終了時にNoteを有料化(or非公開化)し、企画ステータスを完了にする。

```
Schedule Trigger (毎日 23:55)  ← 23:59終了に間に合うよう23:55実行
    │
    ├──→ [Google Sheets] アクティブ企画を取得
    │     Filter: status="active"
    │
    ├──→ [If] end_date の日付 = today ?
    │     ↓ Yes
    │
    ├──→ [SSH → Claude Code] Note記事を有料化 or 非公開化 (Playwright)
    │     Playwrightでブラウザ操作:
    │     方式A: 有料記事に変更 (価格設定画面を操作)
    │     方式B: 非公開に変更 (記事設定→下書きに戻す)
    │
    │     ※ Claude Codeが note_url からNote編集画面を開き、Playwrightで操作
    │
    ├──→ [Google Sheets] status を "completed" に更新
    │
    └──→ [通知] Discord/LINE
          「【企画終了】{theme}
           Note記事を有料化しました
           最終配布数: Note {X}件 / 特典 {Y}件」
```

**Note有料化のClaude Codeスクリプト:**

```bash
# pipeline_giveaway_close.sh
# 引数: note_url
NOTE_URL=$1

claude --print --model claude-sonnet-4-6 <<PROMPT
以下のNote記事を有料化(または非公開化)してください。
Playwrightを使用してブラウザ操作で実行します。

Note URL: $NOTE_URL
Cookies: /root/koma-x-automation/config/note_cookies.json

手順:
1. Noteの記事編集画面を開く
2. 記事設定から「有料」に変更し価格を設定（例: 980円）
3. または「下書きに戻す」で非公開化
4. 変更を保存

実行結果をJSON形式で出力:
{"status": "success", "action": "paid/draft", "price": 980, "note_url": "..."}
PROMPT
```

---

## 6. データ構造

### Google Sheets: 企画管理シート

| カラム | 型 | 説明 |
|--------|-----|------|
| campaign_id | string | 企画ID (例: giveaway_20260327) |
| theme | string | テーマ |
| note_url | string | 無料Note記事URL |
| bonus_url | string | 特典URL (Notion共有リンク) |
| bonus_title | string | 特典タイトル |
| giveaway_tweet_id | string | 告知ツイートのID (投稿後に自動記録) |
| note_id | string | Note記事ID (有料化処理用) |
| status | string | draft → active → completed |
| start_date | date | 公開日 (Day 0) |
| end_date | datetime | 終了日時 (Day +3 23:59) |
| reply_since_id | string | リプライ監視の最終取得ID |
| quote_since_id | string | 引用RT監視の最終取得ID |

### Google Sheets: 配布ログシート

| カラム | 型 | 説明 |
|--------|-----|------|
| campaign_id | string | 企画ID |
| user_id | string | X user ID |
| username | string | @ユーザー名 |
| trigger_type | string | reply / quote_rt |
| content_delivered | string | note / bonus |
| delivery_method | string | hide_reply |
| delivered_at | datetime | 配布日時 |
| source_tweet_id | string | ユーザーのリプ/引用RTのID |
| reply_tweet_id | string | 配布リプライのID (Hidden) |

### Google Sheets: 投稿予約シート (既存流用 + campaign_id列追加)

| カラム | 型 | 説明 |
|--------|-----|------|
| Status | string | Ready / Done |
| Content | string | 投稿文 |
| PostDate | datetime | 予定投稿日時 |
| XURL | string | 投稿後のツイートID |
| campaign_id | string | 紐づく企画ID |

---

## 7. VPS上のファイル構成

```
/root/koma-x-automation/
├── scripts/
│   ├── 00_run_setup.sh                # (既存) 初期設定
│   ├── pipeline_morning.sh            # (既存) 朝の投稿パイプライン
│   ├── pipeline_analysis.sh           # (既存) 投稿分析
│   │
│   ├── pipeline_giveaway.sh           # (新規) プレゼント企画パイプライン
│   └── pipeline_giveaway_close.sh    # (新規) Note有料化/非公開化
│
├── playwright/
│   ├── note_publisher.py              # (新規) Note記事自動公開スクリプト
│   └── note_paywall.py                # (新規) Note記事有料化スクリプト
│
├── templates/
│   └── giveaway_prompt.md             # (新規) Claude Code用プロンプト
│
├── config/
│   ├── ...                            # (既存)
│   ├── giveaway_config.json           # (新規) 企画設定
│   └── note_cookies.json              # (新規) Noteログインセッション
│
└── .env                               # 環境変数
    # X_BEARER_TOKEN=...
    # GEMINI_API_KEY=...
    # NOTION_API_TOKEN=...
    # NOTION_GIVEAWAY_DB_ID=...
    # GOOGLE_SHEETS_ID=...
```

### giveaway_config.json

```json
{
  "genre_keywords": ["AI", "ChatGPT", "Claude", "自動化", "n8n", "副業"],
  "campaign_duration_days": 3,
  "note_word_count": {"min": 2000, "max": 3000},
  "schedule": {
    "teaser": "-2days 12:00",
    "pre_announce": "-1day 12:00",
    "main_post": "day0 12:00",
    "social_proof": "+1day 20:00",
    "last_day_warning": "+3days 12:00",
    "close": "+3days 23:59"
  },
  "reply_filter_keywords": ["受け取り", "ほしい", "欲しい", "ください", "お願い", "知りたい", "気になる"],
  "quote_rt_min_chars": 20
}
```

---

## 8. 技術スタック

| レイヤー | ツール | 用途 |
|---------|--------|------|
| オーケストレーション | n8n | スケジュール管理・監視・配布ループ |
| AI / コンテンツ | Claude Code (VPS SSH) | 調査〜コンテンツ作成を自律実行 |
| リサーチ (AI内部) | WebSearch / WebFetch | 最新情報調査・Note/Brain人気記事調査 |
| 画像生成 | nanobanana (Gemini API) | サムネイル・挿入画像の自動生成 |
| ブラウザ自動操作 | Playwright | Note記事の自動公開・有料化 |
| X API | **X API v2 (従量課金)** | 投稿・Hide Reply・リプ監視・引用RT監視・トレンド調査 |
| X検索 (補助) | twitterapi.io | 高度な検索 (既存フロー互換) |
| 記事公開 | Playwright → Note | 無料記事公開・有料化 |
| 特典管理 | Notion API | 特典コンテンツ作成 |
| データ管理 | Google Sheets | 企画管理・配布ログ・投稿予約 |
| 通知 | Discord / LINE | 日次レポート |

---

## 9. 実装順序

### Phase 1: 監視・配布の自動化

1. Google Sheetsに管理シート・配布ログシート作成
2. **WF3: リプライ監視 & Hide Reply配布フロー** (n8n JSON作成)
3. **WF4: 引用RT監視 & Hide Reply配布フロー** (n8n JSON作成)
4. **WF2: 投稿ID記録フロー** (既存予約投稿フローの拡張)
5. テスト: 手動で企画ツイートを投稿し、配布動作を確認

### Phase 2: コンテンツ自動生成

6. VPSに Playwright + Chromium + 日本語フォント環境構築
7. `note_publisher.py` (Note自動公開) の実装・テスト
8. `note_paywall.py` (Note有料化) の実装・テスト
9. nanobanana (Gemini API) 画像生成テスト
10. Notion API連携テスト
11. VPSに `pipeline_giveaway.sh` + `giveaway_prompt.md` を配置
12. **WF1: 企画パイプライン起動フロー** (n8n JSON作成)
13. テスト: 1回分の企画を自動生成し、内容を確認

### Phase 3: 完全自律運用

14. **WF5: 配布レポートフロー**
15. **WF6: 企画自動終了 & Note有料化フロー**
16. 結合テスト (WF1→投稿→WF3/4→WF5→WF6)
17. 本番運用開始

---

## 10. 完成時の運用サイクル

```
[1回の企画サイクル: 6日間]

Day -2 (水) 05:00  → Claude Code: トレンド調査→Note・特典・投稿5本を一括作成
Day -2 (水) 12:00  → n8n: 投稿① 予告ティーザー
Day -1 (木) 12:00  → n8n: 投稿② 明日公開の告知
Day  0 (金) 12:00  → n8n: 投稿③ 公開 & プレゼント開始 ★ 監視開始
Day +1 (土) 20:00  → n8n: 投稿④ 社会的証明 (感想届いてます)
Day +1〜+3         → n8n: 5分間隔でリプ&引用RT監視 → Hide Replyで自動配布
Day +3 (月) 12:00  → n8n: 投稿⑤ 最終日告知 (今日23:59で終了)
Day +3 (月) 23:55  → n8n: Note有料化 → 企画終了
毎日 22:00         → n8n: 日次レポート

[月2回: 第1週・第3週に同じサイクルが自動で繰り返される]
```

**人間の介入: ゼロ**

---

## 11. リスク・注意事項

### X API関連
- Hide Replyの大量実行がスパム判定されないか → 3秒間隔で安全に
- 従量課金の費用モニタリング → WF5のレポートでAPI消費量も追跡
- X API v2 従量課金のスコープに `tweet.moderate.write` が含まれるか要確認

### Playwright / Note関連
- Noteの画面仕様変更でPlaywrightが壊れるリスク → エラー時にDiscord/LINE通知で即検知
- Noteのログインセッション (cookies) の有効期限管理 → 定期的にcookies更新
- Note利用規約上のbot操作リスク → 頻度を控えめに（月2回のみ）

### 運用リスク
- Notionの共有リンクが意図せずインデックスされる可能性
- 2企画が同時にアクティブになる期間 (第1企画の後半 + 第3企画の前半) のAPI消費増
- nanobanana画像生成の品質ブレ → プロンプトテンプレートで統一感を担保

### コンプライアンス
- 景品表示法: 無料デジタルコンテンツのプレゼントは原則規制対象外
- Note記事の著作権: リサーチ結果の要約・オリジナル解説に留める
