#!/usr/bin/env python3
"""Fetch X API search results and parse them, saving output to data/ directory."""
import json
import sys
import time
import urllib.request
import urllib.parse

BEARER = "AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"
BASE_URL = "https://api.x.com/2/tweets/search/recent"
DATA_DIR = "/root/koma-x-automation/data"

def search(query, max_results=50):
    params = urllib.parse.urlencode({
        "query": query,
        "max_results": max_results,
        "tweet.fields": "public_metrics,created_at,author_id,entities",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics",
    })
    url = f"{BASE_URL}?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {BEARER}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": str(e), "status": e.code, "body": body}
    except Exception as e:
        return {"error": str(e)}

def parse(data, label):
    if "error" in data:
        status = data.get("status", "?")
        print(f"{label}: ERROR status={status} - {data.get('error','')}")
        if status == 429:
            return "RATE_LIMIT"
        return None

    if "data" not in data:
        print(f"{label}: NO DATA - {str(data)[:200]}")
        return None

    tweets = data["data"]
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    meta = data.get("meta", {})
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"Total: {len(tweets)} tweets (result_count={meta.get('result_count','?')})")

    sorted_t = sorted(tweets, key=lambda x: x.get("public_metrics", {}).get("like_count", 0), reverse=True)
    notable = [t for t in sorted_t if t.get("public_metrics", {}).get("like_count", 0) >= 50]
    buzz = [t for t in sorted_t if t.get("public_metrics", {}).get("like_count", 0) >= 200]
    print(f"Notable (like>=50): {len(notable)}, Buzz (like>=200): {len(buzz)}")
    print()

    print("Top 15 by likes:")
    for t in sorted_t[:15]:
        m = t.get("public_metrics", {})
        u = users.get(t["author_id"], {})
        likes = m.get("like_count", 0)
        flag = "[BUZZ]" if likes >= 200 else ("[NOTE]" if likes >= 50 else "      ")
        print(f"{flag} like={likes:4d} rt={m.get('retweet_count',0):3d} rp={m.get('reply_count',0):3d} imp={m.get('impression_count',0):6d}")
        print(f"       id={t['id']} @{u.get('username','?')} ({u.get('name','?')})")
        print(f"       {t['text'][:150].replace(chr(10),' ')}")
        print()
    return sorted_t

queries = [
    ("Q1: Claude Code lang:ja", "Claude Code lang:ja -is:reply -is:retweet", 50),
    ("Q2: AIエージェント lang:ja", "AIエージェント lang:ja -is:reply -is:retweet", 50),
    ("Q3: AI 自動化 lang:ja", "AI 自動化 lang:ja -is:reply -is:retweet", 50),
    ("Q4: n8n lang:ja", "n8n lang:ja -is:reply -is:retweet", 50),
    ("Q5: Competitors group1", "from:keitowebai OR from:miyabi_foxx OR from:masahirochaen -is:reply -is:retweet", 10),
    ("Q6: Competitors group2", "from:tetumemo OR from:beku_AI OR from:Kohaku_NFT -is:reply -is:retweet", 10),
    ("Q7: Global accounts", "from:claudeai OR from:n8n_io OR from:OpenAI -is:reply -is:retweet", 10),
]

all_results = {}

for i, (label, query, max_r) in enumerate(queries):
    print(f"\n[Fetching {i+1}/7] {label}")
    data = search(query, max_r)
    result = parse(data, label)
    if result == "RATE_LIMIT":
        print("RATE LIMIT hit. Stopping.")
        break
    all_results[label] = {"query": query, "raw": data}
    if i < len(queries) - 1:
        print("Sleeping 3s...")
        time.sleep(3)

# Save all results
outfile = f"{DATA_DIR}/x_api_japan_raw.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"\n\nSaved to {outfile}")
