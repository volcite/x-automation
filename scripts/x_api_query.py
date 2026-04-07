#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.parse
import time

TOKEN = "AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"

def search_tweets(query, max_results=50):
    params = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "public_metrics,created_at,author_id,entities",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics"
    }
    url = "https://api.x.com/2/tweets/search/recent?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def parse_results(data, query_label=""):
    if "error" in data:
        return None, f"ERROR: {data['error']}"
    if data.get("status") == 429:
        return None, "RATE_LIMIT"
    tweets = data.get("data", [])
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    results = []
    for t in tweets:
        m = t.get("public_metrics", {})
        u = users.get(t.get("author_id", ""), {})
        results.append({
            "id": t["id"],
            "text": t["text"],
            "username": u.get("username", ""),
            "name": u.get("name", ""),
            "likes": m.get("like_count", 0),
            "rt": m.get("retweet_count", 0),
            "replies": m.get("reply_count", 0),
            "impressions": m.get("impression_count", 0),
            "created_at": t.get("created_at", ""),
            "query": query_label
        })
    results.sort(key=lambda x: x["likes"], reverse=True)
    return results, None

queries_en = [
    ("Claude Code -is:reply -is:retweet", "en_claude_code"),
    ("Claude AI agent -is:reply -is:retweet", "en_claude_agent"),
    ("AI automation workflow -is:reply -is:retweet", "en_ai_automation"),
    ("Claude computer use -is:reply -is:retweet", "en_claude_computer_use"),
    ("n8n AI -is:reply -is:retweet", "en_n8n_ai"),
    ("AI coding assistant -is:reply -is:retweet", "en_ai_coding"),
]

queries_ja = [
    ("Claude Code lang:ja -is:reply -is:retweet", "ja_claude_code"),
    ("AI自動化 lang:ja -is:reply -is:retweet", "ja_ai_automation"),
    ("AIエージェント lang:ja -is:reply -is:retweet", "ja_ai_agent"),
    ("生成AI 業務効率化 lang:ja -is:reply -is:retweet", "ja_genai_efficiency"),
]

queries_competitor = [
    ("from:keitowebai OR from:miyabi_foxx OR from:masahirochaen -is:reply -is:retweet", "comp_group1"),
    ("from:tetumemo OR from:beku_AI OR from:Kohaku_NFT -is:reply -is:retweet", "comp_group2"),
    ("from:claudeai OR from:OpenAI -is:reply -is:retweet", "comp_official"),
    ("from:n8n_io OR from:dify_ai -is:reply -is:retweet", "comp_tools"),
]

all_results = {
    "global": [],
    "japan": [],
    "competitor": []
}

rate_limited = False
request_count = 0
MAX_REQUESTS = 15

print("=== Starting X API queries ===")

# English queries
for query, label in queries_en:
    if rate_limited or request_count >= MAX_REQUESTS:
        break
    print(f"\n[{label}] Querying: {query[:60]}...")
    data = search_tweets(query, max_results=50)
    request_count += 1
    results, error = parse_results(data, label)
    if error == "RATE_LIMIT":
        print("  RATE LIMIT hit - stopping API calls")
        rate_limited = True
        break
    elif error:
        print(f"  Error: {error}")
    else:
        print(f"  Got {len(results)} tweets, top like_count={results[0]['likes'] if results else 0}")
        all_results["global"].extend(results)
    time.sleep(2)

# Japanese queries
for query, label in queries_ja:
    if rate_limited or request_count >= MAX_REQUESTS:
        break
    print(f"\n[{label}] Querying: {query[:60]}...")
    data = search_tweets(query, max_results=50)
    request_count += 1
    results, error = parse_results(data, label)
    if error == "RATE_LIMIT":
        print("  RATE LIMIT hit - stopping API calls")
        rate_limited = True
        break
    elif error:
        print(f"  Error: {error}")
    elif results is not None and len(results) == 0:
        # Try without lang:ja
        print(f"  0 results with lang:ja, retrying without...")
        time.sleep(2)
        query2 = query.replace(" lang:ja", "")
        data2 = search_tweets(query2, max_results=50)
        request_count += 1
        results2, error2 = parse_results(data2, label)
        if not error2 and results2:
            # filter to likely JP posts
            all_results["japan"].extend(results2)
            print(f"  Got {len(results2)} tweets (no lang filter), top like_count={results2[0]['likes'] if results2 else 0}")
        else:
            print(f"  Still no results: {error2}")
    else:
        if results:
            print(f"  Got {len(results)} tweets, top like_count={results[0]['likes'] if results else 0}")
            all_results["japan"].extend(results)
    time.sleep(2)

# Competitor queries
for query, label in queries_competitor:
    if rate_limited or request_count >= MAX_REQUESTS:
        break
    print(f"\n[{label}] Querying: {query[:60]}...")
    data = search_tweets(query, max_results=10)
    request_count += 1
    results, error = parse_results(data, label)
    if error == "RATE_LIMIT":
        print("  RATE LIMIT hit - stopping API calls")
        rate_limited = True
        break
    elif error:
        print(f"  Error: {error}")
    else:
        print(f"  Got {len(results)} tweets, top like_count={results[0]['likes'] if results else 0}")
        all_results["competitor"].extend(results)
    time.sleep(2)

print(f"\n=== Done. Total requests: {request_count} ===")
print(f"Global tweets: {len(all_results['global'])}")
print(f"Japan tweets: {len(all_results['japan'])}")
print(f"Competitor tweets: {len(all_results['competitor'])}")

# Save raw results
with open("/root/koma-x-automation/data/x_api_raw_today.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("\n=== Top Global Posts (likes >= 50) ===")
global_sorted = sorted(all_results["global"], key=lambda x: x["likes"], reverse=True)
for r in global_sorted[:15]:
    if r["likes"] >= 50:
        ratio = r["replies"] / r["likes"] if r["likes"] > 0 else 0
        print(f"likes={r['likes']} rt={r['rt']} rep={r['replies']} ratio={ratio:.2f} @{r['username']}: {r['text'][:80]}")

print("\n=== Top Japan Posts (likes >= 20) ===")
japan_sorted = sorted(all_results["japan"], key=lambda x: x["likes"], reverse=True)
for r in japan_sorted[:15]:
    if r["likes"] >= 20:
        ratio = r["replies"] / r["likes"] if r["likes"] > 0 else 0
        print(f"likes={r['likes']} rt={r['rt']} rep={r['replies']} ratio={ratio:.2f} @{r['username']}: {r['text'][:80]}")

print("\n=== Competitor Posts ===")
comp_sorted = sorted(all_results["competitor"], key=lambda x: x["likes"], reverse=True)
for r in comp_sorted[:20]:
    ratio = r["replies"] / r["likes"] if r["likes"] > 0 else 0
    print(f"likes={r['likes']} rt={r['rt']} rep={r['replies']} @{r['username']}: {r['text'][:80]}")

print("\nRaw data saved to /root/koma-x-automation/data/x_api_raw_today.json")
