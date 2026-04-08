#!/usr/bin/env python3
"""
Parse X API JSON from stdin, output top posts sorted by like_count.
Usage: curl ... | python3 parse_api.py
"""
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception as e:
    print("PARSE_ERROR:", e)
    print(raw[:500])
    sys.exit(1)

if 'data' not in data:
    err = data.get('errors', data.get('error', str(data)[:300]))
    print("NO_DATA:", err)
    sys.exit(0)

posts = data['data']
users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
total = len(posts)
posts.sort(key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)

results = []
for p in posts[:15]:
    m = p.get('public_metrics', {})
    u = users.get(p.get('author_id', ''), {})
    results.append({
        "id": p['id'],
        "username": u.get('username', '?'),
        "name": u.get('name', '?'),
        "text": p['text'],
        "created_at": p.get('created_at', ''),
        "like_count": m.get('like_count', 0),
        "retweet_count": m.get('retweet_count', 0),
        "reply_count": m.get('reply_count', 0),
        "quote_count": m.get('quote_count', 0),
        "impression_count": m.get('impression_count', 0),
    })

print(f"TOTAL:{total}")
print(json.dumps(results, ensure_ascii=False, indent=2))
