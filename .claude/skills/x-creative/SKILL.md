---
name: x-creative
description: Claude Code専用の「クリエイティブ」スキル。投稿に添付する画像や動画のプロンプトを生成する。
---

# X Creative

`creative` エージェントを実行してください。

**事前確認**: `data/approved_post.json` の `image_needed` フィールドを確認してください。
- `image_needed: false` の場合 → 画像プロンプト生成は不要です。その旨を報告して終了してください。
- `image_needed: true` の場合 → エージェントを実行してください。

エージェントは承認済み投稿のトーン・テーマを分析し、DALL-E 3やMidjourneyで使用できる英語プロンプトを生成して `data/visual_prompt.json` に保存します。
