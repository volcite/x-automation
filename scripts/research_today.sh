#!/bin/bash
source /root/koma-x-automation/.env

OUTPUT_DIR="/root/koma-x-automation/data/research_raw"
mkdir -p "$OUTPUT_DIR"

search_x() {
  local query="$1"
  local output_file="$2"
  local max_results="${3:-50}"

  echo "Searching: $query -> $output_file"
  curl -s --max-time 15 -G "https://api.x.com/2/tweets/search/recent" \
    --data-urlencode "query=${query}" \
    --data-urlencode "max_results=${max_results}" \
    --data-urlencode "tweet.fields=public_metrics,created_at,author_id,entities" \
    --data-urlencode "expansions=author_id" \
    --data-urlencode "user.fields=username,name,public_metrics" \
    -H "Authorization: Bearer ${X_BEARER_TOKEN}" > "$OUTPUT_DIR/$output_file"
  sleep 2
}

# English queries (5)
search_x "Claude Code -is:reply -is:retweet" "en_claude_code.json"
search_x "Claude AI agent -is:reply -is:retweet" "en_claude_agent.json"
search_x "AI automation workflow -is:reply -is:retweet" "en_ai_automation.json"
search_x "n8n AI -is:reply -is:retweet" "en_n8n_ai.json"
search_x "AI coding assistant 2025 -is:reply -is:retweet" "en_ai_coding.json"

# Japanese queries (4)
search_x "Claude Code lang:ja -is:reply -is:retweet" "ja_claude_code.json"
search_x "AI自動化 lang:ja -is:reply -is:retweet" "ja_ai_automation.json"
search_x "AIエージェント lang:ja -is:reply -is:retweet" "ja_ai_agent.json"
search_x "生成AI 業務効率化 lang:ja -is:reply -is:retweet" "ja_genai_biz.json"

# Competitor queries (3 batched)
search_x "from:keitowebai OR from:miyabi_foxx OR from:masahirochaen -is:reply -is:retweet" "comp_group1.json" 10
search_x "from:tetumemo OR from:beku_AI -is:reply -is:retweet" "comp_group2.json" 10
search_x "from:claudeai OR from:n8n_io -is:reply -is:retweet" "comp_official.json" 10

echo "=== All X API searches complete ==="
echo "Files saved:"
ls -la "$OUTPUT_DIR/"
