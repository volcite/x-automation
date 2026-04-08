#!/usr/bin/env python3
"""Get full text of top posts from all query results"""
import json
import os

data_dir = '/root/koma-x-automation/data'
query_files = [
    ('q1_raw.json', 'Claude Code -is:reply -is:retweet'),
    ('q2_raw.json', 'Claude AI agent -is:reply -is:retweet'),
    ('q3_raw.json', 'AI automation workflow -is:reply -is:retweet'),
    ('q4_raw.json', 'n8n AI -is:reply -is:retweet'),
    ('q5_raw.json', 'Anthropic Claude -is:reply -is:retweet'),
    ('q6_raw.json', 'AI coding assistant -is:reply -is:retweet'),
]

all_notable = []

for fname, label in query_files:
    fpath = os.path.join(data_dir, fname)
    if not os.path.exists(fpath):
        continue
    data = json.load(open(fpath))
    if 'data' not in data:
        print(f'NO DATA: {label}')
        continue
    posts = data['data']
    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
    posts.sort(key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)
    print(f'\n=== {label} ===')
    print(f'Total posts: {len(posts)}')
    notable_count = 0
    for p in posts:
        m = p.get('public_metrics', {})
        lc = m.get('like_count', 0)
        if lc < 50:
            continue
        notable_count += 1
        u = users.get(p.get('author_id', ''), {})
        uname = u.get('username', '?')
        uid = p['id']
        url = f'https://x.com/{uname}/status/{uid}'
        flag = '[BUZZ>=200]' if lc >= 200 else '[NOTE>=50]'
        print(f'\n{flag}')
        print(f'ID: {uid}')
        print(f'URL: {url}')
        print(f'@{uname} ({u.get("name","?")}) followers:{u.get("public_metrics",{}).get("followers_count","?")}')
        print(f'L:{lc} RT:{m.get("retweet_count",0)} R:{m.get("reply_count",0)} Q:{m.get("quote_count",0)} IMP:{m.get("impression_count","?")}')
        print(f'Created: {p.get("created_at","")}')
        print(f'Text:\n{p["text"]}')
        ratio = round(m.get('reply_count',0) / lc, 3) if lc > 0 else 0
        print(f'Reply/Like ratio: {ratio}')
        all_notable.append({
            'id': uid,
            'url': url,
            'username': uname,
            'text': p['text'],
            'metrics': m,
            'reply_to_like_ratio': ratio,
            'created_at': p.get('created_at', ''),
            'query': label
        })
    print(f'Notable count: {notable_count}')

print(f'\n\nTOTAL NOTABLE POSTS (>=50 likes): {len(all_notable)}')

# Save consolidated
out = os.path.join(data_dir, 'x_api_raw.json')
json.dump({'all_notable': all_notable, 'total': len(all_notable)}, open(out, 'w'), ensure_ascii=False, indent=2)
print(f'Saved to {out}')
