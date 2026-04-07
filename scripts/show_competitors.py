#!/usr/bin/env python3
import json

with open('/root/koma-x-automation/data/x_api_japan_raw.json', 'r') as f:
    all_data = json.load(f)

for label in ['Q5: Competitors group1', 'Q6: Competitors group2', 'Q7: Global accounts']:
    entry = all_data[label]
    raw = entry.get('raw', {})
    tweets = raw.get('data', [])
    users = {u['id']: u for u in raw.get('includes', {}).get('users', [])}
    sorted_t = sorted(tweets, key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)
    print('=' * 70)
    print(f'{label} - ALL {len(tweets)} POSTS:')
    for t in sorted_t:
        m = t.get('public_metrics', {})
        u = users.get(t['author_id'], {})
        text = t['text'].replace('\n', ' ')[:200]
        print(f'  @{u.get("username","?")} id={t["id"]}')
        print(f'  like={m.get("like_count",0)} rt={m.get("retweet_count",0)} rp={m.get("reply_count",0)} imp={m.get("impression_count",0)} bm={m.get("bookmark_count",0)}')
        print(f'  {text}')
        print()
    print()
