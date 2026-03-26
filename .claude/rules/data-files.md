---
description: パイプラインで使用するデータファイルの仕様と責務
globs: data/*.json, data/*.md
---

# データファイル仕様

各ファイルは特定のエージェントが書き込み、後続のエージェントが読み取るパイプライン構造。

| ファイル | 役割 | 書き込み者 |
|---|---|---|
| `data/persona.md` | アカウントペルソナ・競合・検索キーワード | x-setup / 手動 |
| `data/style_guide.md` | 文体ルール・禁止表現 | style_cloner |
| `data/strategy.md` | 投稿戦略・インサイト | analyst |
| `data/pipeline_context.json` | 実行スロット情報（morning/evening） | pipeline_morning.sh |
| `data/trends.json` | 当日リサーチ結果 | researcher |
| `data/content_plan.json` | 当日コンテンツ企画 | planner |
| `data/draft.json` | ライター下書き | writer / storytelling |
| `data/approved_post.json` | 承認済み最終投稿 | editor |
| `data/injected_topic.json` | 差し込みテーマ（2-3日間有効） | pipeline_inject.sh |
