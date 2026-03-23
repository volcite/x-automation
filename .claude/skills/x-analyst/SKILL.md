---
name: x-analyst
description: Claude Code専用の「アナリスト」スキル。投稿のエンゲージメント分析・戦略更新を行う。
---

# X Analyst

`analyst` エージェントを実行してください。

**事前確認**: `data/input_metrics.json` が存在するか確認してください。存在しない場合はユーザーに以下のJSONを作成するよう依頼してください：
```json
{
  "tweet_id": "投稿ID",
  "date": "YYYY-MM-DD",
  "slot": "morning または evening",
  "theme": "テーマ名",
  "style": "文体タイプ",
  "cta_type": "follow/save/reply等",
  "impressions": 0,
  "likes": 0,
  "retweets": 0,
  "replies": 0,
  "profile_visits": 0,
  "new_followers_attributed": 0,
  "saves": 0
}
```

エージェントはエンゲージメント率を計算（S〜D評価）し、`data/analytics.json` を更新して `data/strategy.md` にインサイトを追記します。
