#!/usr/bin/env python3
"""Analyze X API raw data for top posts and patterns"""
import json

with open("data/x_research_raw.json") as f:
    data = json.load(f)

all_posts = []
for query, resp in data.items():
    if not resp.get("data"):
        continue
    user_map = {}
    for u in resp.get("includes", {}).get("users", []):
        user_map[u["id"]] = u
    for p in resp["data"]:
        m = p.get("public_metrics", {})
        author = user_map.get(p.get("author_id"), {})
        is_ja = any(jp in query for jp in ["lang:ja", "自動化", "エージェント", "効率化"])
        is_comp = "from:" in query
        all_posts.append({
            "id": p["id"],
            "text": p["text"][:200],
            "username": author.get("username", "?"),
            "name": author.get("name", "?"),
            "likes": m.get("like_count", 0),
            "rts": m.get("retweet_count", 0),
            "replies": m.get("reply_count", 0),
            "quotes": m.get("quote_count", 0),
            "impressions": m.get("impression_count", 0),
            "region": "japan" if is_ja else "global",
            "is_competitor": is_comp,
            "query": query,
            "created_at": p.get("created_at", ""),
            "author_followers": author.get("public_metrics", {}).get("followers_count", 0)
        })

# Deduplicate by ID
seen = set()
unique = []
for p in all_posts:
    if p["id"] not in seen:
        seen.add(p["id"])
        unique.append(p)
all_posts = unique

all_posts.sort(key=lambda x: x["likes"], reverse=True)

print("=== TOP 20 POSTS BY LIKES ===")
for p in all_posts[:20]:
    ratio = p["replies"] / p["likes"] if p["likes"] > 0 else 0
    print(f"\n@{p['username']} [{p['region']}] {'[COMP]' if p['is_competitor'] else ''}")
    print(f"  L:{p['likes']} RT:{p['rts']} R:{p['replies']} Q:{p['quotes']} Imp:{p['impressions']} R/L:{ratio:.2f}")
    print(f"  Followers: {p['author_followers']} | ID: {p['id']}")
    print(f"  {p['text'][:140]}...")

print("\n=== HIGH REPLY/LIKE RATIO (conversation inducing) ===")
conv_posts = [p for p in all_posts if p["likes"] >= 10 and p["likes"] > 0 and p["replies"] / p["likes"] > 0.1]
conv_posts.sort(key=lambda x: x["replies"] / x["likes"], reverse=True)
for p in conv_posts[:10]:
    ratio = p["replies"] / p["likes"]
    print(f"\n@{p['username']} [{p['region']}] R/L:{ratio:.2f}")
    print(f"  L:{p['likes']} RT:{p['rts']} R:{p['replies']}")
    print(f"  {p['text'][:120]}...")

print("\n=== COMPETITOR TOP POSTS ===")
comp_posts = [p for p in all_posts if p["is_competitor"]]
comp_posts.sort(key=lambda x: x["likes"], reverse=True)
for p in comp_posts[:15]:
    print(f"@{p['username']} L:{p['likes']} RT:{p['rts']} R:{p['replies']} | {p['text'][:100]}...")
