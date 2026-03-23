#!/bin/bash
source ~/.bashrc 2>/dev/null || source ~/.bash_profile 2>/dev/null || true
CLAUDE_CMD=$(which claude 2>/dev/null)
if [ -z "$CLAUDE_CMD" ]; then
  for candidate in "$HOME/.local/bin/claude" "$HOME/.npm-global/bin/claude" "/usr/local/bin/claude" "/usr/bin/claude"; do
    [ -x "$candidate" ] && CLAUDE_CMD="$candidate" && break
  done
fi
[ -z "$CLAUDE_CMD" ] && echo "エラー: claude コマンドが見つかりません。" && exit 1

cd "$(dirname "$0")/.."
echo "Starting: Writer..."
"$CLAUDE_CMD" -p "$(cat .claude/agents/writer.md)"
