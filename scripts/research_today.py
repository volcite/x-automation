#!/usr/bin/env python3
"""Today's research: X API queries + analysis"""
import os, json, time, urllib.request, urllib.parse, urllib.error, ssl

# Load token
# Load from .env manually
TOKEN = ""
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("X_BEARER_TOKEN="):
                TOKEN = line.split("=", 1)[1].strip().strip('"')

ssl_ctx = ssl.create_default_context()

def x_search(query, max_results=50):
    """Search X API v2"""
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
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}", "detail": body[:500]}
    except Exception as e:
        return {"error": str(e)}

# Build user lookup from includes
def build_user_map(resp):
    users = {}
    for u in resp.get("includes", {}).get("users", []):
        users[u["id"]] = u
    return users

# English queries
en_queries = [
    "Claude Code -is:reply -is:retweet",
    "Claude AI agent -is:reply -is:retweet",
    "AI automation n8n -is:reply -is:retweet",
    "Anthropic Claude -is:reply -is:retweet",
    "AI coding assistant -is:reply -is:retweet",
]

# Japanese queries
ja_queries = [
    "Claude Code lang:ja -is:reply -is:retweet",
    "AI自動化 lang:ja -is:reply -is:retweet",
    "AIエージェント lang:ja -is:reply -is:retweet",
    "n8n AI lang:ja -is:reply -is:retweet",
    "生成AI 業務効率化 lang:ja -is:reply -is:retweet",
]

# Competitor queries
competitors = [
    "from:keitowebai -is:reply -is:retweet",
    "from:miyabi_foxx -is:reply -is:retweet",
    "from:masahirochaen -is:reply -is:retweet",
    "from:tetumemo -is:reply -is:retweet",
    "from:beku_AI -is:reply -is:retweet",
    "from:Kohaku_NFT -is:reply -is:retweet",
]

all_results = {}
rate_limited = False

print("=== X API English Queries ===")
for q in en_queries:
    if rate_limited:
        break
    print(f"\nQuery: {q}")
    resp = x_search(q, 50)
    if "error" in resp and "429" in str(resp.get("error", "")):
        print("  RATE LIMITED - stopping API calls")
        rate_limited = True
        break
    count = resp.get("meta", {}).get("result_count", 0)
    print(f"  Results: {count}")
    all_results[q] = resp

    # Show top posts by likes
    if resp.get("data"):
        user_map = build_user_map(resp)
        posts = sorted(resp["data"], key=lambda x: x.get("public_metrics", {}).get("like_count", 0), reverse=True)
        for p in posts[:5]:
            m = p.get("public_metrics", {})
            author = user_map.get(p.get("author_id"), {})
            uname = author.get("username", "?")
            print(f"  @{uname} | L:{m.get('like_count',0)} RT:{m.get('retweet_count',0)} R:{m.get('reply_count',0)} | {p['text'][:80]}...")
    time.sleep(2)

print("\n=== X API Japanese Queries ===")
for q in ja_queries:
    if rate_limited:
        break
    print(f"\nQuery: {q}")
    resp = x_search(q, 50)
    if "error" in resp and "429" in str(resp.get("error", "")):
        print("  RATE LIMITED - stopping API calls")
        rate_limited = True
        break
    count = resp.get("meta", {}).get("result_count", 0)
    print(f"  Results: {count}")

    # If 0 results with lang:ja, retry without it
    if count == 0 and "lang:ja" in q:
        q2 = q.replace(" lang:ja", "")
        print(f"  Retrying without lang:ja: {q2}")
        time.sleep(2)
        resp = x_search(q2, 50)
        count = resp.get("meta", {}).get("result_count", 0)
        print(f"  Results (retry): {count}")
        all_results[q2] = resp
    else:
        all_results[q] = resp

    if resp.get("data"):
        user_map = build_user_map(resp)
        posts = sorted(resp["data"], key=lambda x: x.get("public_metrics", {}).get("like_count", 0), reverse=True)
        for p in posts[:5]:
            m = p.get("public_metrics", {})
            author = user_map.get(p.get("author_id"), {})
            uname = author.get("username", "?")
            print(f"  @{uname} | L:{m.get('like_count',0)} RT:{m.get('retweet_count',0)} R:{m.get('reply_count',0)} | {p['text'][:80]}...")
    time.sleep(2)

print("\n=== Competitor Queries ===")
for q in competitors:
    if rate_limited:
        break
    print(f"\nQuery: {q}")
    resp = x_search(q, 10)
    if "error" in resp and "429" in str(resp.get("error", "")):
        print("  RATE LIMITED - stopping API calls")
        rate_limited = True
        break
    count = resp.get("meta", {}).get("result_count", 0)
    print(f"  Results: {count}")
    all_results[q] = resp

    if resp.get("data"):
        user_map = build_user_map(resp)
        posts = sorted(resp["data"], key=lambda x: x.get("public_metrics", {}).get("like_count", 0), reverse=True)
        for p in posts[:3]:
            m = p.get("public_metrics", {})
            author = user_map.get(p.get("author_id"), {})
            uname = author.get("username", "?")
            print(f"  @{uname} | L:{m.get('like_count',0)} RT:{m.get('retweet_count',0)} R:{m.get('reply_count',0)} | {p['text'][:80]}...")
    time.sleep(2)

# Save raw results
with open("data/x_research_raw.json", "w") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

# Aggregate stats
total_en = sum(r.get("meta", {}).get("result_count", 0) for q, r in all_results.items() if not any(jp in q for jp in ["lang:ja", "自動化", "エージェント", "効率化", "from:"]))
total_ja = sum(r.get("meta", {}).get("result_count", 0) for q, r in all_results.items() if any(jp in q for jp in ["lang:ja", "自動化", "エージェント", "効率化"]))

print(f"\n=== Summary ===")
print(f"Total EN posts: {total_en}")
print(f"Total JA posts: {total_ja}")
print(f"Rate limited: {rate_limited}")
print(f"Queries executed: {len(all_results)}")
print("Raw data saved to data/x_research_raw.json")
