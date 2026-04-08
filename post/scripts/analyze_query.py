#!/usr/bin/env python3
import json
import sys

filepath = sys.argv[1]
query_name = sys.argv[2] if len(sys.argv) > 2 else 'unknown'

with open(filepath) as f:
    data = json.load(f)

if 'errors' in data and 'data' not in data:
    print(f"ERROR for {query_name}: {data}")
    sys.exit(0)

posts = data.get('data', [])
users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
print(f"=== {query_name} | Total: {len(posts)} tweets ===")
posts.sort(key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)

results = []
for p in posts:
    m = p.get('public_metrics', {})
    u = users.get(p.get('author_id', ''), {})
    like = m.get('like_count', 0)
    rt = m.get('retweet_count', 0)
    rp = m.get('reply_count', 0)
    qc = m.get('quote_count', 0)
    imp = m.get('impression_count', 0)
    username = u.get('username', '')
    flag = 'BUZZ   ' if like >= 200 else ('NOTABLE' if like >= 50 else '       ')
    txt = p['text'].replace('\n', ' ')[:100]
    results.append({
        'id': p['id'],
        'username': username,
        'name': u.get('name', ''),
        'text': p['text'],
        'like_count': like,
        'retweet_count': rt,
        'reply_count': rp,
        'quote_count': qc,
        'impression_count': imp,
        'created_at': p.get('created_at', ''),
        'query': query_name,
        'url': f"https://x.com/{username}/status/{p['id']}"
    })
    if like > 0:
        print(f"{flag} likes={like:5} rt={rt:4} rp={rp:3} @{username}: {txt}")

print(json.dumps(results, ensure_ascii=False))
