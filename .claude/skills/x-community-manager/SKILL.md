---
name: x-community-manager
description: Claude Code専用の「コミュニティマネージャー」スキル。リプライやメンションの対応方針・返信文を作成する。
---

# X Community Manager

実行モードを確認してください：

## REACTIVEモード（受信リプライへの返信）
新着リプライのリストを貼り付けてから `community_manager` エージェントを実行してください。
エージェントが各リプライへの返信原案を100文字以内で生成します。

## PROACTIVEモード（能動的リプライ・フォロワー獲得）
以下を確認してから `community_manager` エージェントを実行してください：
- `data/trends.json` が本日分であること
- `data/persona.md` に競合アカウントが設定されていること

`$CM_MODE=proactive` として実行し、インフルエンサーへの質の高いリプライを最大10件生成します。

**モードが不明な場合はユーザーに確認してください。**
