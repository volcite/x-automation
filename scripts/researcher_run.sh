#!/bin/bash
# Researcher script - runs all X API queries and saves results
TOKEN="AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"
OUT_DIR="/root/koma-x-automation/data"

run_query() {
  local QUERY="$1"
  local MAX="$2"
  local OUTFILE="$3"
  curl -s --max-time 15 -G "https://api.x.com/2/tweets/search/recent" \
    --data-urlencode "query=${QUERY}" \
    --data-urlencode "max_results=${MAX}" \
    --data-urlencode "tweet.fields=public_metrics,created_at,author_id,entities" \
    --data-urlencode "expansions=author_id" \
    --data-urlencode "user.fields=username,name,public_metrics" \
    -H "Authorization: Bearer $TOKEN" > "$OUTFILE"
  echo "Saved: $OUTFILE"
}

echo "=== Q1: Claude Code (EN) ==="
run_query "Claude Code -is:reply -is:retweet" 50 "${OUT_DIR}/rq1_claude_code_en.json"
sleep 2

echo "=== Q2: Claude AI agent (EN) ==="
run_query "Claude AI agent -is:reply -is:retweet" 50 "${OUT_DIR}/rq2_claude_agent_en.json"
sleep 2

echo "=== Q3: AI automation workflow (EN) ==="
run_query "AI automation workflow -is:reply -is:retweet" 50 "${OUT_DIR}/rq3_ai_auto_en.json"
sleep 2

echo "=== Q4: Anthropic Claude (EN) ==="
run_query "Anthropic Claude -is:reply -is:retweet" 50 "${OUT_DIR}/rq4_anthropic_en.json"
sleep 2

echo "=== Q5: n8n AI (EN) ==="
run_query "n8n AI -is:reply -is:retweet" 50 "${OUT_DIR}/rq5_n8n_ai_en.json"
sleep 2

echo "=== Q6: Claude Code (JA) ==="
run_query "Claude Code lang:ja -is:reply -is:retweet" 50 "${OUT_DIR}/rq6_claude_code_ja.json"
sleep 2

echo "=== Q7: AIエージェント (JA) ==="
run_query "AIエージェント lang:ja -is:reply -is:retweet" 50 "${OUT_DIR}/rq7_ai_agent_ja.json"
sleep 2

echo "=== Q8: AI 自動化 (JA) ==="
run_query "AI 自動化 lang:ja -is:reply -is:retweet" 50 "${OUT_DIR}/rq8_ai_auto_ja.json"
sleep 2

echo "=== Q9: 生成AI 業務効率化 (JA) ==="
run_query "生成AI 業務効率化 lang:ja -is:reply -is:retweet" 50 "${OUT_DIR}/rq9_genai_ja.json"
sleep 2

echo "=== Q10: from:keitowebai ==="
run_query "from:keitowebai -is:reply -is:retweet" 10 "${OUT_DIR}/rq10_keitowebai.json"
sleep 2

echo "=== Q11: from:masahirochaen ==="
run_query "from:masahirochaen -is:reply -is:retweet" 10 "${OUT_DIR}/rq11_masahirochaen.json"
sleep 2

echo "=== Q12: from:Kohaku_NFT ==="
run_query "from:Kohaku_NFT -is:reply -is:retweet" 10 "${OUT_DIR}/rq12_kohaku_nft.json"
sleep 2

echo "=== All queries complete ==="
