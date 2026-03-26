#!/bin/bash
# ========================================
# 朝のコンテンツ制作パイプライン（一括実行）
# n8nから毎朝7:00にこのスクリプトを1本叩くだけでOK
# 朝スロット（8:00投稿）・夕スロット（19:00投稿）の2本を自動生成する
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

# Claude Code のツール権限を事前許可（root環境でも動作）
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [ ! -f "$CLAUDE_SETTINGS" ]; then
  mkdir -p "$HOME/.claude"
  cat > "$CLAUDE_SETTINGS" << 'SETTINGS_EOF'
{
  "permissions": {
    "allow": [
      "Read(*)",
      "Write(*)",
      "Glob(*)",
      "WebSearch(*)",
      "WebFetch(*)",
      "Bash(*)"
    ],
    "deny": []
  }
}
SETTINGS_EOF
fi

# 作業ディレクトリを x-automation 直下に移動
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# jq がなければ python3 で代替
if ! command -v jq &> /dev/null; then
  if command -v python3 &> /dev/null; then
    log "警告: jq が未インストールのため python3 で代替します"
    jq() {
      python3 -c "
import sys, json, re

args = sys.argv[1:]

# -r フラグ検出
raw = '-r' in args
args = [a for a in args if a != '-r']

# -n フラグ（入力なしモード）
null_input = '-n' in args
args = [a for a in args if a != '-n']

filter_expr = args[0] if args else '.'
files = args[1:] if not null_input else []

# --arg key value の収集
named = {}
remaining_files = []
i = 0
while i < len(files):
    if files[i] == '--arg' and i+2 < len(files):
        named[files[i+1]] = files[i+2]
        i += 3
    else:
        remaining_files.append(files[i])
        i += 1
files = remaining_files

# データ読み込み
if null_input:
    data = None
elif files:
    with open(files[0]) as f:
        data = json.load(f)
    if len(files) > 1:
        extras = []
        for fn in files[1:]:
            with open(fn) as f:
                extras.append(json.load(f))
else:
    data = json.load(sys.stdin)

# 簡易フィルタ評価
def eval_filter(expr, data, named):
    expr = expr.strip()
    # . (identity)
    if expr == '.':
        return data
    # .field or .field.sub
    if re.match(r'^(\.[a-zA-Z_][a-zA-Z0-9_]*)+$', expr):
        result = data
        for key in re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', expr):
            result = result.get(key) if isinstance(result, dict) else None
        return result
    # .field // \"default\"
    m = re.match(r'^(\.[a-zA-Z_.]+)\s*//\s*(.+)$', expr)
    if m:
        val = eval_filter(m.group(1), data, named)
        if val is None:
            default = m.group(2).strip().strip('\"')
            return default
        return val
    # length
    if expr == 'length':
        return len(data) if data else 0
    # .[:-N] or .[-N:]
    if re.match(r'^\.\[.*\]$', expr):
        return eval(f'data{expr[1:]}')
    # jq -n construction: {\"data\": [{\"post\": \$var, ...}]}
    if expr.startswith('{') or expr.startswith('['):
        # \$var 置換
        result = expr
        for k, v in named.items():
            result = result.replace(f'\${k}', json.dumps(v))
        return json.loads(result)
    return data

result = eval_filter(filter_expr, data, named)

if isinstance(result, str):
    print(result if raw else json.dumps(result))
elif result is None:
    print('null')
elif isinstance(result, bool):
    print(str(result).lower())
elif isinstance(result, (int, float)):
    print(result)
else:
    print(json.dumps(result, ensure_ascii=False))
" "$@"
    }
    export -f jq
  else
    log "エラー: jq も python3 も見つかりません。どちらかをインストールしてください。"
    exit 1
  fi
fi

# .envファイルからWEBHOOK_URLを読み込む
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
else
  log "警告: .envファイルが見つかりません"
fi

if [ -z "$WEBHOOK_URL" ]; then
  log "エラー: WEBHOOK_URLが設定されていません。.envファイルを確認してください。"
  exit 1
fi

# 曜日判定（1=月曜）→ 週次カレンダー生成フラグ
DOW=$(date +%u)
WEEKLY_PLANNING="false"
if [ "$DOW" = "1" ]; then
  WEEKLY_PLANNING="true"
  log "本日は月曜日 → 週次コンテンツカレンダーを生成します"
fi

log "========== パイプライン開始（2スロット制） =========="

# ========================================
# 差し込みテーマチェック
# data/injected_topic.json が存在し、status=active かつ有効期間内であれば
# pipeline_context.json に injection 情報を付与する
# ========================================
INJECTION_ACTIVE="false"
INJECTION_JSON=""

if [ -f "data/injected_topic.json" ]; then
  INJECT_STATUS=$(jq -r '.status // "inactive"' data/injected_topic.json 2>/dev/null || echo "inactive")
  if [ "$INJECT_STATUS" = "active" ]; then
    # 有効期間チェック
    INJECT_DATE=$(jq -r '.inject_date' data/injected_topic.json 2>/dev/null)
    DURATION_DAYS=$(jq -r '.duration_days // 3' data/injected_topic.json 2>/dev/null)
    TODAY_DATE=$(date +%Y-%m-%d)

    DAYS_ELAPSED=$(node -e "
const d1 = new Date('$INJECT_DATE');
const d2 = new Date('$TODAY_DATE');
console.log(Math.floor((d2 - d1) / 86400000));
" 2>/dev/null || echo "999")

    if [ "$DAYS_ELAPSED" -lt "$DURATION_DAYS" ]; then
      INJECTION_ACTIVE="true"
      INJECTION_JSON=$(cat data/injected_topic.json)
      INJECT_TOPIC=$(jq -r '.topic' data/injected_topic.json)
      log "差し込みテーマ検知: 「${INJECT_TOPIC}」（${DAYS_ELAPSED}日目/${DURATION_DAYS}日間）"
    else
      # 有効期限切れ → ステータスを expired に更新
      node -e "
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('data/injected_topic.json', 'utf-8'));
data.status = 'expired';
fs.writeFileSync('data/injected_topic.json', JSON.stringify(data, null, 2), 'utf-8');
"
      log "差し込みテーマ「$(jq -r '.topic' data/injected_topic.json)」の有効期限が切れました → expired に変更"
    fi
  fi
fi

# 差し込みテーマ付き pipeline_context.json を書き出す共通関数
# 引数: $1=slot, $2=post_time
write_injection_context() {
  local _SLOT="$1"
  local _POST_TIME="$2"
  node -e "
const fs = require('fs');
const injection = JSON.parse(fs.readFileSync('data/injected_topic.json', 'utf-8'));
const context = {
  slot: process.argv[1],
  post_time: process.argv[2],
  weekly_planning: process.argv[3] === 'true',
  injection: {
    active: true,
    topic: injection.topic,
    details: injection.details || '',
    source_url: injection.source_url || '',
    priority: injection.priority || 'high',
    inject_date: injection.inject_date,
    duration_days: injection.duration_days,
    day_number: parseInt(process.argv[4]) + 1,
    slots_used: injection.slots_used || []
  }
};
fs.writeFileSync('data/pipeline_context.json', JSON.stringify(context, null, 2), 'utf-8');
" "$_SLOT" "$_POST_TIME" "$WEEKLY_PLANNING" "$DAYS_ELAPSED" 2>> "$LOG_FILE"
}

# ステップ1: リサーチャー（朝・夕共通。1回だけ実行）
log "STEP 1: リサーチャー実行中..."

# pipeline_context.json を初期化（リサーチャーが参照するため morning スロットで初期化）
if [ "$INJECTION_ACTIVE" = "true" ]; then
  # 差し込みテーマ情報を pipeline_context に含める
  write_injection_context "morning" "08:00"
else
  echo "{\"slot\": \"morning\", \"post_time\": \"08:00\", \"weekly_planning\": $WEEKLY_PLANNING}" > data/pipeline_context.json
fi

if "$CLAUDE_CMD" -p "$(awk '/^---$/{n++; next} n>=2' .claude/agents/researcher.md)" >> "$LOG_FILE" 2>&1; then
  log "STEP 1: リサーチャー完了 ✅"
  # リサーチデータ（競合分析・トレンド）を履歴に蓄積
  if [ ! -f data/research_history.json ]; then
    echo "[]" > data/research_history.json
  fi
  if [ -f data/trends.json ] && command -v jq &> /dev/null; then
    jq '. += [input]' data/research_history.json data/trends.json > data/temp_rh.json && mv data/temp_rh.json data/research_history.json

    LEN=$(jq 'length' data/research_history.json 2>/dev/null || echo "0")
    if [ "$LEN" -gt 30 ]; then
      # 直近30件を超えた古いデータを退避
      jq '.[:-30]' data/research_history.json > data/temp_old.json
      jq '.[-30:]' data/research_history.json > data/temp_rh.json && mv data/temp_rh.json data/research_history.json

      if [ ! -f data/research_history_archive.json ]; then
        echo "[]" > data/research_history_archive.json
      fi

      jq '. + input' data/research_history_archive.json data/temp_old.json > data/temp_arc.json && mv data/temp_arc.json data/research_history_archive.json
      rm -f data/temp_old.json

      log "リサーチデータを蓄積し、古いデータを research_history_archive.json に退避しました（直近30件保持）"
    else
      log "リサーチデータを research_history.json に蓄積しました"
    fi
  fi
else
  log "STEP 1: リサーチャー失敗 ❌"
  exit 1
fi

# ========================================
# スロット別パイプライン関数
# 引数: $1=slot名(morning/evening), $2=投稿時刻(HH:MM)
# ========================================
run_slot() {
  local SLOT="$1"
  local POST_TIME="$2"

  log "========== ${SLOT}スロット開始（${POST_TIME}投稿） =========="

  # pipeline_context.json をスロット情報で更新（プランナーが参照する）
  if [ "$INJECTION_ACTIVE" = "true" ]; then
    write_injection_context "$SLOT" "$POST_TIME"
  else
    echo "{\"slot\": \"$SLOT\", \"post_time\": \"$POST_TIME\", \"weekly_planning\": $WEEKLY_PLANNING}" > data/pipeline_context.json
  fi

  # プランナー
  log "[${SLOT}] プランナー実行中..."
  if "$CLAUDE_CMD" -p "$(awk '/^---$/{n++; next} n>=2' .claude/agents/planner.md)" >> "$LOG_FILE" 2>&1; then
    log "[${SLOT}] プランナー完了 ✅"
  else
    log "[${SLOT}] プランナー失敗 ❌"
    return 1
  fi

  # ライター
  log "[${SLOT}] ライター実行中..."
  if "$CLAUDE_CMD" -p "$(awk '/^---$/{n++; next} n>=2' .claude/agents/writer.md)" >> "$LOG_FILE" 2>&1; then
    log "[${SLOT}] ライター完了 ✅"
  else
    log "[${SLOT}] ライター失敗 ❌"
    return 1
  fi

  # エディター（品質チェック → approved_post.json へ保存）
  log "[${SLOT}] エディター実行中..."
  if "$CLAUDE_CMD" -p "$(awk '/^---$/{n++; next} n>=2' .claude/agents/editor.md)" >> "$LOG_FILE" 2>&1; then
    log "[${SLOT}] エディター完了 ✅"
  else
    log "[${SLOT}] エディター失敗 ❌"
    return 1
  fi

  # 承認チェック & Webhook送信
  local APPROVED
  APPROVED=$(jq -r '.approved' data/approved_post.json 2>/dev/null || echo "false")

  if [ "$APPROVED" = "true" ]; then
    log "[${SLOT}] 投稿承認済み ✅ ${POST_TIME}の自動投稿キューに格納"
    # posts/ にスロット付きでアーカイブ
    cp data/approved_post.json "posts/$(date +%Y-%m-%d)_${SLOT}.json"

    # Webhook送信
    local POST_CONTENT RAW_DATE SCHEDULED_TIME IMAGE_PROMPT PAYLOAD HTTP_CODE
    POST_CONTENT=$(jq -r '.final_content' data/approved_post.json)
    RAW_DATE=$(jq -r '.date' data/approved_post.json)
    SCHEDULED_TIME=$(echo "$RAW_DATE" | tr '-' '/')
    IMAGE_PROMPT=$(jq -r '.image_prompt // ""' data/approved_post.json)

    PAYLOAD=$(jq -n \
      --arg post "$POST_CONTENT" \
      --arg date "$SCHEDULED_TIME" \
      --arg image_prompt "$IMAGE_PROMPT" \
      '{"data": [{"post": $post, "date": $date, "image_prompt": $image_prompt}]}')

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json; charset=utf-8" \
      -d "$PAYLOAD")

    if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
      log "[${SLOT}] n8n Webhook送信完了 ✅ (HTTP $HTTP_CODE)"

      # ナレッジストック使用時は usage_count を更新
      local KNOWLEDGE_ID
      KNOWLEDGE_ID=$(jq -r '.knowledge_used_id // ""' data/content_plan.json 2>/dev/null || echo "")
      if [ -n "$KNOWLEDGE_ID" ] && [ "$KNOWLEDGE_ID" != "null" ] && [ -f "data/knowledge_stock.json" ]; then
        node -e "
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('data/knowledge_stock.json', 'utf-8'));
const targetId = process.argv[1];
const today = process.argv[2];
const item = data.items.find(i => i.id === targetId);
if (item) {
  item.usage_count = (item.usage_count || 0) + 1;
  item.last_used_at = today;
  if (item.usage_count >= item.max_usage) {
    item.status = 'retired';
  }
  data.last_updated = new Date().toISOString();
  fs.writeFileSync('data/knowledge_stock.json', JSON.stringify(data, null, 2), 'utf-8');
}
" "$KNOWLEDGE_ID" "$(date +%Y-%m-%d)" 2>> "$LOG_FILE"
        log "[${SLOT}] ナレッジストック使用回数を更新: ${KNOWLEDGE_ID}"
      fi

      # 差し込みテーマ使用時は slots_used を更新
      if [ "$INJECTION_ACTIVE" = "true" ]; then
        local SLOT_KEY="$(date +%Y-%m-%d)_${SLOT}"
        node -e "
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('data/injected_topic.json', 'utf-8'));
const slotKey = process.argv[1];
if (!data.slots_used) data.slots_used = [];
if (!data.slots_used.includes(slotKey)) data.slots_used.push(slotKey);
fs.writeFileSync('data/injected_topic.json', JSON.stringify(data, null, 2), 'utf-8');
" "$SLOT_KEY" 2>> "$LOG_FILE"
        log "[${SLOT}] 差し込みテーマのslots_usedを更新: ${SLOT_KEY}"
      fi
    else
      log "[${SLOT}] n8n Webhook送信失敗 ❌ (HTTP $HTTP_CODE)"
    fi
  else
    log "[${SLOT}] 投稿差し戻し ⚠️ エディターのフィードバックを確認してください"
  fi

  log "========== ${SLOT}スロット完了 =========="
}

# 朝スロット実行（8:00投稿）
# 月曜の場合、プランナーが weekly_plan.json を生成してから朝コンテンツを計画する
run_slot "morning" "08:00" || log "朝スロット失敗 ❌ 夕スロットに進みます"

# 夕スロット実行（19:00投稿）
run_slot "evening" "19:00" || log "夕スロット失敗 ❌"

log "========== パイプライン終了（2スロット完了） =========="
