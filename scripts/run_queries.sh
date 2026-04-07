#!/bin/bash
BEARER="AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"
DATA="/root/koma-x-automation/data"
PARSE="python3 /root/koma-x-automation/scripts/parse_tweets.py"

xsearch() {
    local label="$1"
    local query="$2"
    local max="${3:-50}"
    local outfile="$4"
    echo "=== ${label} ==="
    curl -s --max-time 15 -G "https://api.x.com/2/tweets/search/recent" \
        --data-urlencode "query=${query}" \
        --data-urlencode "max_results=${max}" \
        --data-urlencode "tweet.fields=public_metrics,created_at,author_id,entities" \
        --data-urlencode "expansions=author_id" \
        --data-urlencode "user.fields=username,name,public_metrics" \
        -H "Authorization: Bearer ${BEARER}" \
        > "${DATA}/${outfile}"
    $PARSE < "${DATA}/${outfile}"
    echo ""
    sleep 3
}

# Q1
xsearch "Q1: Claude Code lang:ja" "Claude Code lang:ja -is:reply -is:retweet" 50 "q1_claudecode_ja.json"

# Q2
xsearch "Q2: AIエージェント lang:ja" "AIエージェント lang:ja -is:reply -is:retweet" 50 "q2_aiagent_ja.json"

# Q3
xsearch "Q3: AI 自動化 lang:ja" "AI 自動化 lang:ja -is:reply -is:retweet" 50 "q3_automation_ja.json"

# Q4
xsearch "Q4: n8n lang:ja" "n8n lang:ja -is:reply -is:retweet" 50 "q4_n8n_ja.json"

# Q5: Competitor group 1
xsearch "Q5: Competitors keitowebai/miyabi_foxx/masahirochaen" "from:keitowebai OR from:miyabi_foxx OR from:masahirochaen -is:reply -is:retweet" 10 "q5_comp1.json"

# Q6: Competitor group 2
xsearch "Q6: Competitors tetumemo/beku_AI/Kohaku_NFT" "from:tetumemo OR from:beku_AI OR from:Kohaku_NFT -is:reply -is:retweet" 10 "q6_comp2.json"

# Q7: Global accounts
xsearch "Q7: claudeai/n8n_io/OpenAI" "from:claudeai OR from:n8n_io OR from:OpenAI -is:reply -is:retweet" 10 "q7_global.json"

echo "=== ALL DONE ==="
