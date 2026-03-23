---
name: x-researcher
description: Claude Code専用の「リサーチャー」スキル。Xトレンドや競合調査からネタ候補を抽出する。
---

# X Researcher

`researcher` エージェントを実行してください。

エージェントは以下を自律的に実行します：
1. `data/persona.md` からキーワードを読み込み、5〜10個の検索クエリを自律決定
2. Web検索でトレンド・競合・バズ投稿を調査
3. フォロワー獲得シグナルを分析
4. 結果を `data/trends.json` に保存

完了後、発見した主要トレンドとネタ候補を報告してください。
