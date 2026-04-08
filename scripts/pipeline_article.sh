#!/bin/bash
# ========================================
# X記事（Note記事）制作パイプライン（週次実行）
# 1週間ごとにバズ記事を調査・分析し、記事を作成してWebhookで送信する
#
# フロー:
#   1. 先週バズったX記事をリサーチ
#   2. リサーチデータを分析
#   3. 分析履歴を蓄積（過去1ヶ月分保持）
#   4. 記事テーマを立案（article_planner）
#   5. 記事を執筆（article_writer）
#   6. Webhookでn8nに送信
#
# 使い方:
#   bash scripts/pipeline_article.sh
#   bash scripts/pipeline_article.sh --skip-research    # リサーチをスキップ
#   bash scripts/pipeline_article.sh --min-faves 500    # いいね数の閾値を変更
# ========================================
set -e

# 非インタラクティブSSH環境でも PATH を通す
source ~/.bashrc 2>/dev/null || source ~/.bash_profile 2>/dev/null || true
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

# claude コマンドの場所を特定
CLAUDE_CMD=$(which claude 2>/dev/null)
if [ -z "$CLAUDE_CMD" ]; then
  NVM_CLAUDE=$(ls "$HOME/.nvm/versions/node/"*/bin/claude 2>/dev/null | tail -1)
  for candidate in "$NVM_CLAUDE" "$HOME/.local/bin/claude" "$HOME/.npm-global/bin/claude" "/usr/local/bin/claude" "/usr/bin/claude"; do
    [ -n "$candidate" ] && [ -x "$candidate" ] && CLAUDE_CMD="$candidate" && break
  done
fi
if [ -z "$CLAUDE_CMD" ]; then
  echo "エラー: claude コマンドが見つかりません。インストール・PATHを確認してください。"
  exit 1
fi

# 作業ディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

ARTICLE_DIR="$PROJECT_DIR/article"

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/article_$(date +%Y%m%d_%H%M%S).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# jq がなければ python3 で代替
if ! command -v jq &> /dev/null; then
  if command -v python3 &> /dev/null; then
    log "警告: jq が未インストールのため python3 で代替します"
    jq() {
      python3 -c "
import sys, json
args = sys.argv[1:]
raw = '-r' in args
args = [a for a in args if a != '-r']
null_input = '-n' in args
args = [a for a in args if a != '-n']
filter_expr = args[0] if args else '.'
files = args[1:] if not null_input else []
if files:
    with open(files[0]) as f:
        data = json.load(f)
elif not null_input:
    data = json.load(sys.stdin)
else:
    data = None
parts = filter_expr.lstrip('.').split('.') if filter_expr != '.' else []
result = data
for p in parts:
    if p and isinstance(result, dict):
        result = result.get(p)
if isinstance(result, str):
    print(result if raw else json.dumps(result))
elif result is None:
    print('null')
else:
    print(json.dumps(result, ensure_ascii=False))
" "$@"
    }
    export -f jq
  else
    log "エラー: jq も python3 も見つかりません。"
    exit 1
  fi
fi

# .envファイル読み込み
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
else
  log "警告: .envファイルが見つかりません"
fi

# ========================================
# 引数パース
# ========================================
SKIP_RESEARCH=false
MIN_FAVES=1000

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-research)  SKIP_RESEARCH=true; shift ;;
    --min-faves)      MIN_FAVES="$2"; shift 2 ;;
    --help|-h)
      echo "使い方: bash scripts/pipeline_article.sh [--skip-research] [--min-faves 500]"
      exit 0
      ;;
    *)
      log "不明なオプション: $1"
      exit 1
      ;;
  esac
done

log "========== X記事制作パイプライン開始 =========="

# ========================================
# STEP 1: バズ記事リサーチ（先週分）
# ========================================
if [ "$SKIP_RESEARCH" = false ]; then
  log "[STEP 1] バズ記事リサーチ開始..."

  # 先週の日付範囲を算出
  SINCE_DATE=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d 2>/dev/null)
  UNTIL_DATE=$(date +%Y-%m-%d)

  log "  期間: ${SINCE_DATE} 〜 ${UNTIL_DATE}"
  log "  いいね閾値: ${MIN_FAVES}以上"
  log "  言語: 全言語（日本語+海外）"

  if bash scripts/pipeline_article_research.sh \
    --min-faves "$MIN_FAVES" \
    --since "$SINCE_DATE" \
    --until "$UNTIL_DATE" \
    --lang all \
    --analyze \
    --verbose >> "$LOG_FILE" 2>&1; then
    log "[STEP 1] リサーチ＆分析完了 ✅"
  else
    log "[STEP 1] リサーチ失敗 ❌ 既存データで続行します"
  fi
else
  log "[STEP 1] リサーチをスキップ（--skip-research）"
fi

# ========================================
# STEP 2: 分析履歴の蓄積（過去1ヶ月分保持）
# ========================================
log "[STEP 2] 分析履歴を蓄積..."

HISTORY_FILE="data/article_analysis_history.json"
TODAY=$(date +%Y-%m-%d)
ONE_MONTH_AGO=$(date -d "30 days ago" +%Y-%m-%d 2>/dev/null || date -v-30d +%Y-%m-%d 2>/dev/null)

# 最新のanalysis-*.mdを検出
LATEST_ANALYSIS=$(ls -t "$ARTICLE_DIR"/output/analysis-*.md 2>/dev/null | head -1)

if [ -n "$LATEST_ANALYSIS" ]; then
  log "  最新分析: $LATEST_ANALYSIS"

  # 分析ファイルの内容を要約として保存
  ANALYSIS_CONTENT=$(cat "$LATEST_ANALYSIS")

  # 履歴ファイルの初期化（存在しなければ）
  if [ ! -f "$HISTORY_FILE" ]; then
    echo '{"entries": []}' > "$HISTORY_FILE"
  fi

  # 新しいエントリを追加し、1ヶ月以上古いエントリを削除
  node -e "
const fs = require('fs');
const history = JSON.parse(fs.readFileSync('$HISTORY_FILE', 'utf-8'));
const today = '$TODAY';
const oneMonthAgo = '$ONE_MONTH_AGO';
const analysisFile = '$(basename "$LATEST_ANALYSIS")';

// 同日のエントリが既にあれば上書き
history.entries = history.entries.filter(e => e.date !== today);

// 新しいエントリを追加
history.entries.push({
  date: today,
  analysis_file: analysisFile,
  analysis_path: '$LATEST_ANALYSIS'
});

// 1ヶ月以上古いエントリを削除
history.entries = history.entries.filter(e => e.date >= oneMonthAgo);

// 日付順にソート（新しい順）
history.entries.sort((a, b) => b.date.localeCompare(a.date));

history.last_updated = new Date().toISOString();
history.total_entries = history.entries.length;

fs.writeFileSync('$HISTORY_FILE', JSON.stringify(history, null, 2));
console.log('履歴更新完了: ' + history.entries.length + '件保持');
" >> "$LOG_FILE" 2>&1

  log "[STEP 2] 分析履歴蓄積完了 ✅"
else
  log "[STEP 2] 分析ファイルが見つかりません ⚠️ 既存の履歴で続行"
fi

# ========================================
# STEP 3: 記事テーマ立案（article_planner）
# ========================================
log "[STEP 3] 記事テーマ立案開始..."

if "$CLAUDE_CMD" -p "$(awk '/^---$/{n++; next} n>=2' .claude/agents/article_planner.md)" >> "$LOG_FILE" 2>&1; then
  if [ -f "data/article_plan.json" ]; then
    ARTICLE_THEME=$(jq -r '.theme' data/article_plan.json)
    log "[STEP 3] 記事テーマ立案完了 ✅ テーマ: ${ARTICLE_THEME}"
  else
    log "[STEP 3] article_plan.json が生成されませんでした ❌"
    exit 1
  fi
else
  log "[STEP 3] 記事テーマ立案失敗 ❌"
  exit 1
fi

# ========================================
# STEP 4: 記事執筆（article_writer）
# ========================================
log "[STEP 4] 記事執筆開始..."

if "$CLAUDE_CMD" -p "$(awk '/^---$/{n++; next} n>=2' .claude/agents/article_writer.md)" >> "$LOG_FILE" 2>&1; then
  if [ -f "data/article_draft.json" ]; then
    CHAR_COUNT=$(jq -r '.char_count' data/article_draft.json)
    ARTICLE_TITLE=$(jq -r '.title' data/article_draft.json)
    log "[STEP 4] 記事執筆完了 ✅ タイトル: ${ARTICLE_TITLE} (${CHAR_COUNT}文字)"
  else
    log "[STEP 4] article_draft.json が生成されませんでした ❌"
    exit 1
  fi
else
  log "[STEP 4] 記事執筆失敗 ❌"
  exit 1
fi

# ========================================
# STEP 5: Webhookでn8nに送信
# ========================================
log "[STEP 5] Webhook送信..."

if [ -z "$ARTICLE_WEBHOOK_URL" ]; then
  log "[STEP 5] ARTICLE_WEBHOOK_URL が設定されていません ⚠️ 送信をスキップ"
  log "  記事は data/article_draft.json に保存されています"
else
  # title と content（article_content）を分離したペイロードを生成
  WEBHOOK_PAYLOAD=$(node -e "
const fs = require('fs');
const draft = JSON.parse(fs.readFileSync('data/article_draft.json', 'utf-8'));
const payload = {
  title: draft.title || '',
  content: draft.article_content || '',
  subtitle: draft.subtitle || '',
  meta_description: draft.meta_description || '',
  char_count: draft.char_count || 0,
  date: draft.date || ''
};
process.stdout.write(JSON.stringify(payload));
")

  HTTP_CODE=$(echo "$WEBHOOK_PAYLOAD" | curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$ARTICLE_WEBHOOK_URL" \
    -H "Content-Type: application/json; charset=utf-8" \
    --data-binary @-)

  if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    log "[STEP 5] Webhook送信完了 ✅ (HTTP $HTTP_CODE)"
    log "  送信フィールド: title, content, subtitle, meta_description, char_count, date"
  else
    log "[STEP 5] Webhook送信失敗 ❌ (HTTP $HTTP_CODE)"
    log "  記事は data/article_draft.json に保存されています"
  fi
fi

# ========================================
# STEP 6: ナレッジストック使用カウント更新
# ========================================
if [ -f "data/article_plan.json" ] && [ -f "data/knowledge_stock.json" ]; then
  KNOWLEDGE_IDS=$(jq -r '.knowledge_used[]?.id // empty' data/article_plan.json 2>/dev/null || echo "")

  if [ -n "$KNOWLEDGE_IDS" ]; then
    log "[STEP 6] ナレッジストック使用カウント更新..."

    echo "$KNOWLEDGE_IDS" | while read -r KID; do
      [ -z "$KID" ] && continue
      node -e "
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('data/knowledge_stock.json', 'utf-8'));
const today = '${TODAY}';
const item = data.items.find(i => i.id === '${KID}');
if (item) {
  item.usage_count = (item.usage_count || 0) + 1;
  item.last_used_at = today;
  if (item.usage_count >= (item.max_usage || 5)) {
    item.status = 'retired';
  }
  fs.writeFileSync('data/knowledge_stock.json', JSON.stringify(data, null, 2));
  console.log('ナレッジ更新: ' + '${KID}' + ' (usage: ' + item.usage_count + ')');
}
" >> "$LOG_FILE" 2>&1
    done

    log "[STEP 6] ナレッジストック更新完了 ✅"
  fi
fi

# ========================================
# 完了
# ========================================
log "========== X記事制作パイプライン完了 =========="
log "  テーマ: ${ARTICLE_THEME:-不明}"
log "  タイトル: ${ARTICLE_TITLE:-不明}"
log "  文字数: ${CHAR_COUNT:-不明}"
log "  記事ファイル: data/article_draft.json"
log "  ログ: $LOG_FILE"
