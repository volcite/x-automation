#!/usr/bin/env python3
import json
import sys

filepath = sys.argv[1]
with open(filepath) as f:
    raw = f.read()

data = json.loads(raw)
posts = data.get('data', [])
users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
posts.sort(key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)

print('TOTAL:', len(posts))
for p in posts[:15]:
    m = p.get('public_metrics', {})
    u = users.get(p.get('author_id', ''), {})
    txt = p['text'].replace('\n', ' ')[:120]
    pid = p['id']
    uname = u.get('username', '?')
    lc = m.get('like_count', 0)
    rt = m.get('retweet_count', 0)
    rc = m.get('reply_count', 0)
    imp = m.get('impression_count', 0)
    print(f"{pid} @{uname} L:{lc} RT:{rt} R:{rc} IMP:{imp} | {txt}")
