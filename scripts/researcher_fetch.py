#!/usr/bin/env python3
"""
Researcher: fetch tweets from X API v2 and save results to data/
"""
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import os

BEARER = "AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"
BASE_URL = "https://api.x.com/2/tweets/search/recent"
OUT_DIR = "/root/koma-x-automation/data"

def fetch_tweets(query, max_results=50, label="q"):
    params = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "public_metrics,created_at,author_id,entities",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics",
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {BEARER}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP Error {e.code}: {body[:200]}")
        return {"error": e.code, "body": body}
    except Exception as ex:
        print(f"  Exception: {ex}")
        return {"error": str(ex)}

queries_en = [
    ("Claude Code -is:reply -is:retweet", 50, "q1_en_claude_code"),
    ("Claude AI agent -is:reply -is:retweet", 50, "q2_en_claude_agent"),
    ("AI automation workflow -is:reply -is:retweet", 50, "q3_en_ai_auto"),
    ("n8n AI -is:reply -is:retweet", 50, "q4_en_n8n_ai"),
    ("Anthropic Claude -is:reply -is:retweet", 50, "q5_en_anthropic"),
]

queries_ja = [
    ("Claude Code lang:ja -is:reply -is:retweet", 50, "q6_ja_claude_code"),
    ("AIエージェント lang:ja -is:reply -is:retweet", 50, "q7_ja_ai_agent"),
    ("AI自動化 lang:ja -is:reply -is:retweet", 50, "q8_ja_ai_auto"),
    ("n8n lang:ja -is:reply -is:retweet", 50, "q9_ja_n8n"),
]

queries_competitor = [
    ("from:keitowebai -is:reply -is:retweet", 10, "q10_comp_keito"),
    ("from:masahirochaen -is:reply -is:retweet", 10, "q11_comp_masahiro"),
    ("from:Kohaku_NFT -is:reply -is:retweet", 10, "q12_comp_kohaku"),
]

all_queries = queries_en + queries_ja + queries_competitor

results = {}
rate_limited = False

for query, max_r, label in all_queries:
    if rate_limited:
        print(f"  Skipping {label} due to rate limit")
        results[label] = {"skipped": True, "reason": "rate_limit"}
        continue

    print(f"Fetching {label}: {query}")
    data = fetch_tweets(query, max_r, label)

    if isinstance(data, dict) and data.get("error") == 429:
        print("  Rate limit hit! Stopping API calls.")
        rate_limited = True
        results[label] = {"skipped": True, "reason": "rate_limit"}
        continue

    # If ja query returns 0 results, retry without lang:ja
    if isinstance(data, dict) and "data" not in data and "lang:ja" in query:
        print(f"  0 results with lang:ja, retrying without...")
        new_query = query.replace(" lang:ja", "")
        data = fetch_tweets(new_query, max_r, label + "_nolang")
        time.sleep(2)

    results[label] = data
    count = data.get("meta", {}).get("result_count", 0) if isinstance(data, dict) else 0
    print(f"  -> {count} tweets fetched")

    # Save individual result
    out_path = os.path.join(OUT_DIR, f"researcher_{label}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    time.sleep(2)

# Save combined results
combined_path = os.path.join(OUT_DIR, "researcher_all_raw.json")
with open(combined_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nAll done. Results saved to {combined_path}")

# Print summary of high-engagement posts
print("\n=== HIGH ENGAGEMENT POSTS (like_count >= 50) ===")
for label, data in results.items():
    if not isinstance(data, dict) or "data" not in data:
        continue
    users = {}
    for u in data.get("includes", {}).get("users", []):
        users[u["id"]] = u.get("username", "unknown")
    for tweet in data.get("data", []):
        m = tweet.get("public_metrics", {})
        likes = m.get("like_count", 0)
        rts = m.get("retweet_count", 0)
        replies = m.get("reply_count", 0)
        if likes >= 50 or rts >= 20:
            tid = tweet.get("id", "")
            uid = tweet.get("author_id", "")
            uname = users.get(uid, "unknown")
            print(f"[{label}] @{uname} | likes={likes} rt={rts} reply={replies}")
            print(f"  URL: https://x.com/{uname}/status/{tid}")
            print(f"  TEXT: {tweet.get('text','')[:100]}")
            print()
