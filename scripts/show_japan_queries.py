#!/usr/bin/env python3
import json

with open('/root/koma-x-automation/data/x_api_japan_raw.json', 'r') as f:
    all_data = json.load(f)

for label in ['Q1: Claude Code lang:ja', 'Q2: AIエージェント lang:ja', 'Q3: AI 自動化 lang:ja', 'Q4: n8n lang:ja']:
    entry = all_data[label]
    raw = entry.get('raw', {})
    tweets = raw.get('data', [])
    users = {u['id']: u for u in raw.get('includes', {}).get('users', [])}
    sorted_t = sorted(tweets, key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)
    notable = [t for t in sorted_t if t.get('public_metrics', {}).get('like_count', 0) >= 10]
    print('=' * 70)
    print(f'{label} - Total={len(tweets)}, Notable(like>=10): {len(notable)}')
    print()
    for t in sorted_t[:10]:
        m = t.get('public_metrics', {})
        u = users.get(t['author_id'], {})
        text = t['text'].replace('\n', ' ')[:180]
        print(f'  @{u.get("username","?")} ({u.get("name","?")})')
        print(f'  like={m.get("like_count",0)} rt={m.get("retweet_count",0)} rp={m.get("reply_count",0)} imp={m.get("impression_count",0)} bm={m.get("bookmark_count",0)}')
        print(f'  id={t["id"]}')
        print(f'  {text}')
        print()
    print()
