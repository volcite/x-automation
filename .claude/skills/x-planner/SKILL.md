---
name: x-planner
description: Claude Code専用の「プランナー」スキル。リサーチ結果から最も最適な投稿企画・テーマを立案する。
---

# X Planner

`planner` エージェントを実行してください。

実行前に `data/pipeline_context.json` を確認し、スロット情報が設定されていない場合は以下のデフォルトで設定してください：
```json
{"slot": "evening", "post_time": "19:00", "weekly_planning": false}
```

エージェントは以下を実行します：
1. trends.json・analytics.json・strategy.mdを読み込んで分析
2. スロット（morning/evening）に合ったコンテンツタイプ・CTAを選定
3. フック・感情トリガー・バズ要素を設計
4. 結果を `data/content_plan.json` に保存

完了後、企画内容を報告してください。
