#!/usr/bin/env python3
import json
import sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception as e:
    print("PARSE ERROR:", e)
    print(raw[:300])
    sys.exit(1)

if 'data' not in data:
    print("NO DATA")
    print(str(data)[:500])
    sys.exit(0)

posts = data['data']
users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
print(f"Total posts: {len(posts)}")
posts.sort(key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)
for p in posts[:15]:
    m = p.get('public_metrics', {})
    u = users.get(p.get('author_id', ''), {})
    txt = p['text'].replace('\n', ' ')[:100]
    print(f"{p['id']} @{u.get('username','?')} L:{m.get('like_count',0)} RT:{m.get('retweet_count',0)} R:{m.get('reply_count',0)} | {txt}")
