#!/usr/bin/env python3
"""
【非推奨 - 廃止済み】
Note記事の自動公開はGoogleドキュメント経由に移行しました。

代わりに以下を使用してください:
  bash scripts/publish_article.sh note    # Note記事をWebhook送信
  bash scripts/publish_article.sh bonus   # 追加特典をWebhook送信

n8n側でGoogleドキュメント作成と画像生成を行います。
"""

import sys

print("=" * 50)
print("このスクリプトは廃止されました。")
print()
print("代わりに以下を使用してください:")
print("  bash scripts/publish_article.sh note")
print("  bash scripts/publish_article.sh bonus")
print("=" * 50)
sys.exit(1)
