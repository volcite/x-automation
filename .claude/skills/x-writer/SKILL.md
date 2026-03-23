---
name: x-writer
description: Claude Code専用の「ライター」スキル。企画案に基づく500文字以上のX投稿を作成する。
---

# X Writer

`data/content_plan.json` の `style_type` を確認してください。

- `style_type` が「**共感ストーリー型**」の場合 → `storytelling` エージェントを実行
- それ以外の場合 → `writer` エージェントを実行

エージェントはスタイルガイドと投稿サンプルに従い、AIっぽさを排除した500文字以上の下書きを生成して `data/draft.json` に保存します。

完了後、下書きの冒頭（フック部分）と文字数を報告してください。
