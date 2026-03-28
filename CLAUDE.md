# X Automation System

## 概要
Xアカウントを完全自律運用するマルチエージェントシステム。9つの専門エージェントが連携し、**朝8:00・夕19:00の2投稿**を毎日自動生成・公開する。

## パイプライン構成

```
[テーマ差し込み（随時、n8n経由）]
  ↓
pipeline_inject.sh → data/injected_topic.json（2-3日間有効）

[毎朝7:00 n8n起動]
  ↓
差し込みテーマチェック → pipeline_context.json に injection 情報付与
  ↓
Researcher → data/trends.json           （X API検索・Web検索・競合分析）
  ↓
Planner[morning] → data/content_plan.json  （朝スロット企画 ※差し込みテーマ優先）
  ↓
Writer → data/draft.json               （500文字以上の下書き）
  ↓
Editor → data/approved_post.json       （11点品質チェック）
  ↓
Webhook → n8n → X投稿（8:00）→ slots_used 更新

  ↓（同日、夕スロット繰り返し）
Planner[evening] → Writer → Editor → Webhook（19:00）

[30分ごと n8n起動]
  ↓
n8n: リプライ取得 → pipeline_reply.sh → Webhook → n8nがランダム間隔で返信
```

## 手動実行コマンド
| やりたいこと | コマンド |
|---|---|
| 初回セットアップ | `/x-setup` |
| リサーチャー単体 | `/x-researcher` |
| プランナー単体 | `/x-planner` |
| ライター単体 | `/x-writer` |
| エディター単体 | `/x-editor` |
| アナリスト実行 | `/x-analyst` |
| コミュニティ管理 | `/x-community-manager` |
| 画像プロンプト生成 | `/x-creative` |
| 文体ガイド更新 | `/writing-style-clone` |
| ストーリー投稿作成 | `/storytelling-writer` |
| ナレッジ登録 | `/x-knowledge` |
| ナレッジ追加(CLI) | `bash scripts/pipeline_knowledge.sh '{"topic":"テーマ","content":"内容","category":"philosophy"}'` |
| ナレッジ一覧 | `bash scripts/pipeline_knowledge.sh list` |
| テーマ差し込み | `bash scripts/pipeline_inject.sh '{"topic":"テーマ","details":"詳細","source_url":"URL","duration_days":3}'` |
| 朝パイプライン手動実行 | `bash scripts/pipeline_morning.sh` |
| リプライ返信手動実行 | `bash scripts/pipeline_reply.sh <replies.json>` |
| 分析パイプライン実行 | `bash scripts/pipeline_analysis.sh` |
| 記事をWebhook送信(Note) | `bash scripts/publish_article.sh note` |
| 記事をWebhook送信(特典) | `bash scripts/publish_article.sh bonus` |

## 主要データファイル（agents が読み書きする）

| ファイル | 役割 | 更新者 |
|---|---|---|
| `data/persona.md` | アカウントペルソナ・競合・検索キーワード | x-setup / 手動 |
| `data/style_guide.md` | 文体ルール・禁止表現 | style_cloner |
| `data/strategy.md` | 投稿戦略・インサイト | analyst |
| `data/pipeline_context.json` | 実行スロット情報（morning/evening） | pipeline_morning.sh |
| `data/trends.json` | 当日リサーチ結果 | researcher |
| `data/weekly_plan.json` | 週次テーマカレンダー | planner（月曜のみ） |
| `data/content_plan.json` | 当日コンテンツ企画 | planner |
| `data/draft.json` | ライター下書き | writer / storytelling |
| `data/approved_post.json` | 承認済み最終投稿 | editor |
| `data/visual_prompt.json` | 画像プロンプト | creative |
| `data/analytics.json` | 投稿成績データ | analyst |
| `data/research_history.json` | 過去30件のリサーチ履歴 | pipeline_morning.sh |
| `data/input_metrics.json` | n8nから受け取るメトリクス | n8n連携 |
| `data/input_mentions.json` | n8nから受け取るリプライ | n8n連携 |
| `data/reactive_replies.json` | 生成した返信 | community_manager |
| `data/reply_counter.json` | 日次返信カウンター（上限150件/日, 15件/回） | pipeline_reply.sh |
| `data/injected_topic.json` | 差し込みテーマ（n8nから特定テーマを2-3日間投稿に反映） | pipeline_inject.sh / n8n連携 |
| `data/knowledge_stock.json` | オーナーの思想・哲学・体験ストック | pipeline_knowledge.sh / x-knowledge |

## 絶対ルール（全エージェント共通）

- **ハルシネーション禁止**: 最新情報解説型の投稿では出典URLが存在する情報のみ使用
- **絵文字・ハッシュタグ禁止**: 投稿本文に一切使用しない
- **500文字以上**: 全投稿を必ず500文字以上にする
- **です・ます調統一**: 「しかし」→「でも」、「したがって」→「だから」
- **スロット意識**: morning=教育型・フォロワー獲得、evening=共感系・エンゲージメント

## スロット別コンテンツ方針

| slot | 優先スタイル | 優先CTA | 目標 |
|---|---|---|---|
| morning | 最新情報解説型・教育型 | follow / save | リーチ拡大・フォロワー獲得 |
| evening | 共感ストーリー型・カジュアル報告型 | reply / retweet | ファン化・いいね・RT |

## .env 設定項目
```
WEBHOOK_URL=https://your-n8n.com/webhook/morning-post
REPLY_WEBHOOK_URL=https://your-n8n.com/webhook/reply-handler
ARTICLE_WEBHOOK_URL=https://your-n8n.com/webhook/article-handler
X_BEARER_TOKEN=your_x_api_bearer_token
```

## 参考リソース（エージェントが参照するリファレンス）
- `.claude/skills/writing-style-clone/assets/x_post_sample.md` — 5タイプの投稿文体サンプル
- `.claude/skills/writing-style-clone/references/style_guide.md` — 文体ルール詳細
- `.claude/skills/storytelling-writer/references/emotion_triggers.md` — 感情トリガー一覧
