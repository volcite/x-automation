#!/usr/bin/env python3
"""Parse X API query results from JSON file"""
import json
import sys

def parse(filepath, query_label):
    data = json.load(open(filepath))
    if 'data' not in data:
        print(f'NO DATA for {query_label}')
        print(str(data)[:500])
        return []

    posts = data['data']
    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
    print(f'\n=== {query_label} ===')
    print(f'Total posts: {len(posts)}')

    posts.sort(key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)

    notable = []
    for p in posts:
        m = p.get('public_metrics', {})
        lc = m.get('like_count', 0)
        if lc < 50:
            continue
        u = users.get(p.get('author_id', ''), {})
        txt = p['text'].replace('\n', ' ')[:120]
        flag = '[BUZZ>=200]' if lc >= 200 else '[NOTE>=50]'
        uname = u.get('username', '?')
        uid = p['id']
        url = f'https://x.com/{uname}/status/{uid}'
        print(f'{flag} ID={uid}')
        print(f'  URL: {url}')
        print(f'  @{uname} | L:{lc} RT:{m.get("retweet_count",0)} R:{m.get("reply_count",0)} IMP:{m.get("impression_count","?")}')
        print(f'  Text: {txt}')
        notable.append({'id': uid, 'username': uname, 'url': url, 'text': p['text'][:200], 'metrics': m, 'created_at': p.get('created_at',''), 'query': query_label})

    print(f'Notable (>=50 likes): {len(notable)}')
    return notable

if __name__ == '__main__':
    filepath = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else 'unknown'
    results = parse(filepath, label)
    out_path = filepath.replace('.json', '_parsed.json')
    json.dump(results, open(out_path, 'w'), ensure_ascii=False, indent=2)
    print(f'\nSaved parsed to {out_path}')
