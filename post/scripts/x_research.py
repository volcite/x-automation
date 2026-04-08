#!/usr/bin/env python3
"""X API v2 research script - fetches trending posts for analysis"""
import json, os, sys, time, urllib.request, urllib.parse

TOKEN = os.environ.get("X_BEARER_TOKEN", "")
if not TOKEN:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("X_BEARER_TOKEN="):
                    TOKEN = line.split("=", 1)[1].strip().strip('"')
if not TOKEN:
    print("ERROR: X_BEARER_TOKEN not set")
    sys.exit(1)

def search_tweets(query, max_results=50):
    """Search recent tweets via X API v2"""
    params = urllib.parse.urlencode({
        "query": query,
        "max_results": max_results,
        "tweet.fields": "public_metrics,created_at,author_id,entities",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics"
    })
    url = f"https://api.x.com/2/tweets/search/recent?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}", "detail": body[:200]}
    except Exception as e:
        return {"error": str(e)}

# English queries
en_queries = [
    "Claude Code -is:reply -is:retweet",
    "Claude AI agent -is:reply -is:retweet",
    "AI automation workflow -is:reply -is:retweet",
    "n8n AI -is:reply -is:retweet",
    "Anthropic Claude -is:reply -is:retweet",
    "AI coding assistant -is:reply -is:retweet",
]

# Japanese queries
ja_queries = [
    "Claude Code lang:ja -is:reply -is:retweet",
    "AI自動化 lang:ja -is:reply -is:retweet",
    "AIエージェント lang:ja -is:reply -is:retweet",
    "n8n lang:ja -is:reply -is:retweet",
    "生成AI 業務効率化 lang:ja -is:reply -is:retweet",
]

# Competitor queries
competitor_queries = [
    "from:keitowebai OR from:miyabi_foxx OR from:masahirochaen -is:reply -is:retweet",
    "from:tetumemo OR from:beku_AI OR from:Kohaku_NFT -is:reply -is:retweet",
    "from:claudeai OR from:n8n_io OR from:OpenAI -is:reply -is:retweet",
]

all_results = {"en": {}, "ja": {}, "competitors": {}}
request_count = 0
rate_limited = False

def run_queries(queries, category, max_r=50):
    global request_count, rate_limited
    for q in queries:
        if rate_limited or request_count >= 15:
            print(f"  SKIP (rate limit): {q}")
            continue
        print(f"  Searching: {q}")
        result = search_tweets(q, max_r)
        request_count += 1
        if "error" in result:
            if "429" in str(result.get("error", "")) or "429" in str(result.get("detail", "")):
                print(f"  RATE LIMITED at request #{request_count}")
                rate_limited = True
                continue
            print(f"  Error: {result['error']}")
        count = len(result.get("data", []))
        print(f"  Got {count} tweets")
        all_results[category][q] = result
        time.sleep(2)

print("=== English queries ===")
run_queries(en_queries, "en")

print("\n=== Japanese queries ===")
run_queries(ja_queries, "ja")

print("\n=== Competitor queries ===")
run_queries(competitor_queries, "competitors", max_r=10)

# Save raw results
with open("data/x_api_raw.json", "w") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print(f"\nTotal API requests: {request_count}")
print(f"Rate limited: {rate_limited}")
print("Raw results saved to data/x_api_raw.json")

# Extract top posts by likes
def extract_top_posts(results_dict, top_n=20):
    all_posts = []
    for query, result in results_dict.items():
        if "data" not in result:
            continue
        users = {u["id"]: u for u in result.get("includes", {}).get("users", [])}
        for t in result["data"]:
            m = t.get("public_metrics", {})
            u = users.get(t.get("author_id"), {})
            all_posts.append({
                "id": t["id"],
                "text": t["text"],
                "likes": m.get("like_count", 0),
                "rts": m.get("retweet_count", 0),
                "replies": m.get("reply_count", 0),
                "impressions": m.get("impression_count", 0),
                "quotes": m.get("quote_count", 0),
                "username": u.get("username", ""),
                "name": u.get("name", ""),
                "followers": u.get("public_metrics", {}).get("followers_count", 0),
                "created_at": t.get("created_at", ""),
                "query": query,
                "urls": [e["expanded_url"] for e in t.get("entities", {}).get("urls", [])] if t.get("entities", {}).get("urls") else []
            })
    # Deduplicate by id
    seen = set()
    unique = []
    for p in all_posts:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
    unique.sort(key=lambda x: x["likes"], reverse=True)
    return unique[:top_n]

print("\n=== TOP ENGLISH POSTS (by likes) ===")
en_top = extract_top_posts(all_results["en"], 25)
for p in en_top[:15]:
    ratio = round(p["replies"] / p["likes"], 3) if p["likes"] > 0 else 0
    print(f"@{p['username']} | L:{p['likes']} RT:{p['rts']} R:{p['replies']} Q:{p['quotes']} I:{p['impressions']} r/l:{ratio} | {p['text'][:90]}...")

print("\n=== TOP JAPANESE POSTS (by likes) ===")
ja_top = extract_top_posts(all_results["ja"], 25)
for p in ja_top[:15]:
    ratio = round(p["replies"] / p["likes"], 3) if p["likes"] > 0 else 0
    print(f"@{p['username']} | L:{p['likes']} RT:{p['rts']} R:{p['replies']} Q:{p['quotes']} I:{p['impressions']} r/l:{ratio} | {p['text'][:90]}...")

print("\n=== COMPETITOR POSTS ===")
comp_top = extract_top_posts(all_results["competitors"], 20)
for p in comp_top[:15]:
    ratio = round(p["replies"] / p["likes"], 3) if p["likes"] > 0 else 0
    print(f"@{p['username']} | L:{p['likes']} RT:{p['rts']} R:{p['replies']} Q:{p['quotes']} I:{p['impressions']} r/l:{ratio} | {p['text'][:90]}...")

# Save summary
summary = {"en_top": en_top, "ja_top": ja_top, "comp_top": comp_top, "request_count": request_count, "rate_limited": rate_limited}
with open("data/x_api_research_summary.json", "w") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print("\nSummary saved to data/x_api_research_summary.json")
