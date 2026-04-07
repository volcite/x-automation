#!/usr/bin/env python3
"""X API v2 search helper script."""
import json
import sys
import subprocess
import time

TOKEN = "AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"

def fetch_tweets(query, max_results=50):
    cmd = [
        "curl", "-s", "--max-time", "15", "-G",
        "https://api.x.com/2/tweets/search/recent",
        "--data-urlencode", f"query={query}",
        "--data-urlencode", f"max_results={max_results}",
        "--data-urlencode", "tweet.fields=public_metrics,created_at,author_id,entities",
        "--data-urlencode", "expansions=author_id",
        "--data-urlencode", "user.fields=username,name,public_metrics",
        "-H", f"Authorization: Bearer {TOKEN}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e), "raw": result.stdout[:200]}

    if "errors" in data and "data" not in data:
        return {"error": data["errors"], "status": data.get("status")}

    tweets = data.get("data", [])
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

    parsed = []
    for t in tweets:
        m = t.get("public_metrics", {})
        u = users.get(t.get("author_id", ""), {})
        parsed.append({
            "id": t["id"],
            "author": u.get("username", ""),
            "author_name": u.get("name", ""),
            "text": t["text"],
            "text_preview": t["text"][:120],
            "likes": m.get("like_count", 0),
            "rts": m.get("retweet_count", 0),
            "replies": m.get("reply_count", 0),
            "quotes": m.get("quote_count", 0),
            "impressions": m.get("impression_count", 0),
            "created_at": t.get("created_at", "")
        })

    parsed.sort(key=lambda x: x["likes"], reverse=True)
    return {"tweets": parsed, "total": len(parsed)}


queries_en = [
    ("claude_code_en", "Claude Code -is:reply -is:retweet", 50),
    ("claude_ai_agent_en", "Claude AI agent -is:reply -is:retweet", 50),
    ("ai_automation_workflow_en", "AI automation workflow 2026 -is:reply -is:retweet", 50),
    ("n8n_ai_en", "n8n AI automation -is:reply -is:retweet", 50),
    ("ai_coding_assistant_en", "AI coding assistant -is:reply -is:retweet", 50),
]

queries_ja = [
    ("claude_code_ja", "Claude Code lang:ja -is:reply -is:retweet", 50),
    ("ai_agent_ja", "AIエージェント lang:ja -is:reply -is:retweet", 50),
    ("n8n_ai_ja", "n8n AI lang:ja -is:reply -is:retweet", 50),
    ("seisei_ai_ja", "生成AI 業務効率化 lang:ja -is:reply -is:retweet", 50),
]

queries_competitor = [
    ("competitor_keitowebai", "from:keitowebai -is:reply -is:retweet", 10),
    ("competitor_masahirochaen", "from:masahirochaen -is:reply -is:retweet", 10),
    ("competitor_Kohaku_NFT", "from:Kohaku_NFT -is:reply -is:retweet", 10),
]

all_results = {}
rate_limit_hit = False

all_queries = queries_en + queries_ja + queries_competitor

for key, query, max_r in all_queries:
    if rate_limit_hit:
        break
    print(f"Fetching: {key} ({query})", file=sys.stderr)
    result = fetch_tweets(query, max_r)

    if isinstance(result, dict) and result.get("status") == 429:
        print("Rate limit hit! Stopping API calls.", file=sys.stderr)
        rate_limit_hit = True
        break

    all_results[key] = result
    time.sleep(2)

# If lang:ja queries returned 0, retry without lang:ja
for key, query, max_r in queries_ja:
    if key in all_results and all_results[key].get("total", 0) == 0:
        new_query = query.replace(" lang:ja", "")
        print(f"Retrying without lang:ja: {new_query}", file=sys.stderr)
        result = fetch_tweets(new_query, max_r)
        all_results[key + "_nolang"] = result
        time.sleep(2)

print(json.dumps(all_results, ensure_ascii=False, indent=2))
