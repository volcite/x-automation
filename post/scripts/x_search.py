#!/usr/bin/env python3
import subprocess
import json
import sys
import time

TOKEN = "AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"

def search_tweets(query, max_results=50):
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
    except:
        return None, "JSON parse error"

    if 'errors' in data:
        return None, str(data['errors'])
    if 'status' in data and data['status'] == 429:
        return None, "RATE_LIMIT"

    tweets = data.get('data', [])
    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}

    results = []
    for t in tweets:
        m = t.get('public_metrics', {})
        u = users.get(t['author_id'], {})
        results.append({
            'id': t['id'],
            'username': u.get('username', ''),
            'name': u.get('name', ''),
            'text': t['text'],
            'likes': m.get('like_count', 0),
            'rts': m.get('retweet_count', 0),
            'replies': m.get('reply_count', 0),
            'quotes': m.get('quote_count', 0),
            'impressions': m.get('impression_count', 0),
            'created_at': t.get('created_at', '')
        })

    return results, None

def print_top(results, n=10, label=""):
    if not results:
        print(f"  [{label}] No results")
        return
    sorted_r = sorted(results, key=lambda x: x['likes'], reverse=True)
    print(f"  [{label}] Total: {len(results)}, showing top {min(n, len(sorted_r))}")
    for r in sorted_r[:n]:
        print(f"    likes:{r['likes']} rts:{r['rts']} replies:{r['replies']} imp:{r['impressions']}")
        print(f"    @{r['username']}: {r['text'][:100]}")
        print(f"    URL: https://x.com/{r['username']}/status/{r['id']}")
        print()

all_results = {}
rate_limited = False

queries = [
    ("Claude Code -is:reply -is:retweet", 50, "global_claude_code"),
    ("Claude AI agent -is:reply -is:retweet", 50, "global_claude_agent"),
    ("AI automation workflow -is:reply -is:retweet", 50, "global_ai_automation"),
    ("Anthropic Claude -is:reply -is:retweet", 50, "global_anthropic"),
    ("n8n AI automation -is:reply -is:retweet", 50, "global_n8n"),
    ("AI coding assistant -is:reply -is:retweet", 50, "global_ai_coding"),
    ("Claude Code lang:ja -is:reply -is:retweet", 50, "japan_claude_code"),
    ("AIエージェント lang:ja -is:reply -is:retweet", 50, "japan_ai_agent"),
    ("n8n lang:ja -is:reply -is:retweet", 50, "japan_n8n"),
    ("生成AI 業務効率化 lang:ja -is:reply -is:retweet", 50, "japan_genai"),
    ("from:keitowebai OR from:miyabi_foxx OR from:masahirochaen -is:reply -is:retweet", 10, "competitor_jp1"),
    ("from:tetumemo OR from:beku_AI OR from:Kohaku_NFT -is:reply -is:retweet", 10, "competitor_jp2"),
    ("from:claudeai OR from:n8n_io OR from:dify_ai -is:reply -is:retweet", 10, "competitor_global1"),
    ("from:OpenAI OR from:GeminiApp -is:reply -is:retweet", 10, "competitor_global2"),
]

for i, (query, max_r, label) in enumerate(queries):
    if rate_limited:
        print(f"Skipping {label} due to rate limit")
        continue

    print(f"\n=== Query {i+1}/{len(queries)}: {label} ===")
    print(f"  Query: {query}")
    results, error = search_tweets(query, max_r)

    if error == "RATE_LIMIT":
        print("  RATE LIMITED - stopping API calls")
        rate_limited = True
        continue
    elif error:
        print(f"  Error: {error}")
        # Try without lang:ja if applicable
        if "lang:ja" in query:
            q2 = query.replace(" lang:ja", "")
            print(f"  Retrying without lang:ja: {q2}")
            results, error2 = search_tweets(q2, max_r)
            if error2:
                print(f"  Retry error: {error2}")
                continue

    if results is not None:
        all_results[label] = results
        print_top(results, 5, label)

    if i < len(queries) - 1:
        time.sleep(2)

# Save raw data
with open('/root/koma-x-automation/data/x_api_raw.json', 'w') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("\n=== SUMMARY ===")
global_count = 0
japan_count = 0
for k, v in all_results.items():
    if k.startswith('global'):
        global_count += len(v)
    elif k.startswith('japan'):
        japan_count += len(v)
    print(f"  {k}: {len(v)} tweets")
print(f"  Total global: {global_count}")
print(f"  Total japan: {japan_count}")
