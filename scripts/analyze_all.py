#!/usr/bin/env python3
"""
Analyze all saved X API JSON files and output a combined summary.
"""
import json
import os
import glob

DATA_DIR = "/root/koma-x-automation/data"

FILES = {
    "q1_claude_code": ("Claude Code -is:reply -is:retweet", "global"),
    "q2_ai_agent": ("AI agent automation -is:reply -is:retweet", "global"),
    "q3_n8n_ai": ("n8n AI -is:reply -is:retweet", "global"),
    "q4_claude_computer": ("Claude computer use -is:reply -is:retweet", "global"),
    "q5_ai_coding": ("AI coding assistant 2026 -is:reply -is:retweet", "global"),
    "q6_claude_code_ja": ("Claude Code lang:ja -is:reply -is:retweet", "japan"),
    "q7_ai_jidoka_ja": ("AI自動化 lang:ja -is:reply -is:retweet", "japan"),
    "q8_ai_agent_ja": ("AIエージェント lang:ja -is:reply -is:retweet", "japan"),
    "q9_n8n_ja": ("n8n lang:ja -is:reply -is:retweet", "japan"),
    "c1_keitowebai": ("from:keitowebai -is:reply -is:retweet", "japan"),
    "c2_miyabi_foxx": ("from:miyabi_foxx -is:reply -is:retweet", "japan"),
    "c3_masahirochaen": ("from:masahirochaen -is:reply -is:retweet", "japan"),
    "c4_tetumemo": ("from:tetumemo -is:reply -is:retweet", "japan"),
    "c5_beku_ai": ("from:beku_AI -is:reply -is:retweet", "japan"),
}

all_posts = []

for key, (query, region) in FILES.items():
    fpath = os.path.join(DATA_DIR, f"{key}.json")
    if not os.path.exists(fpath):
        print(f"MISSING: {fpath}")
        continue
    with open(fpath) as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"PARSE ERROR {key}: {e}")
        continue

    if 'data' not in data:
        err = str(data)[:200]
        print(f"NO DATA {key}: {err}")
        continue

    posts = data['data']
    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
    total = len(posts)
    posts.sort(key=lambda x: x.get('public_metrics', {}).get('like_count', 0), reverse=True)

    print(f"\n=== {key} | query: {query} | region: {region} | total: {total} ===")
    for p in posts[:10]:
        m = p.get('public_metrics', {})
        u = users.get(p.get('author_id', ''), {})
        txt = p['text'].replace('\n', ' ')[:100]
        pid = p['id']
        uname = u.get('username', '?')
        lc = m.get('like_count', 0)
        rt = m.get('retweet_count', 0)
        rc = m.get('reply_count', 0)
        imp = m.get('impression_count', 0)
        print(f"  {pid} @{uname} L:{lc} RT:{rt} R:{rc} IMP:{imp}")
        print(f"    {txt}")

    # collect for summary
    for p in posts:
        m = p.get('public_metrics', {})
        u = users.get(p.get('author_id', ''), {})
        all_posts.append({
            "source_query": key,
            "region": region,
            "id": p['id'],
            "username": u.get('username', '?'),
            "text": p['text'],
            "created_at": p.get('created_at', ''),
            "like_count": m.get('like_count', 0),
            "retweet_count": m.get('retweet_count', 0),
            "reply_count": m.get('reply_count', 0),
            "quote_count": m.get('quote_count', 0),
            "impression_count": m.get('impression_count', 0),
        })

print("\n\n=== TOP GLOBAL POSTS (L>=50) ===")
global_buzz = [p for p in all_posts if p['region'] == 'global' and p['like_count'] >= 50]
global_buzz.sort(key=lambda x: x['like_count'], reverse=True)
for p in global_buzz[:20]:
    ratio = p['reply_count'] / max(p['like_count'], 1)
    txt = p['text'].replace('\n', ' ')[:100]
    print(f"  {p['id']} @{p['username']} L:{p['like_count']} RT:{p['retweet_count']} R:{p['reply_count']} ratio:{ratio:.3f}")
    print(f"    {txt}")

print("\n=== TOP JAPAN POSTS (L>=20) ===")
japan_buzz = [p for p in all_posts if p['region'] == 'japan' and p['like_count'] >= 20]
japan_buzz.sort(key=lambda x: x['like_count'], reverse=True)
for p in japan_buzz[:20]:
    ratio = p['reply_count'] / max(p['like_count'], 1)
    txt = p['text'].replace('\n', ' ')[:100]
    print(f"  {p['id']} @{p['username']} L:{p['like_count']} RT:{p['retweet_count']} R:{p['reply_count']} ratio:{ratio:.3f}")
    print(f"    {txt}")

print("\n=== COMPETITOR POSTS ===")
comp_queries = ['c1_keitowebai', 'c2_miyabi_foxx', 'c3_masahirochaen', 'c4_tetumemo', 'c5_beku_ai']
comp_posts = [p for p in all_posts if p['source_query'] in comp_queries]
comp_posts.sort(key=lambda x: x['like_count'], reverse=True)
for p in comp_posts[:20]:
    ratio = p['reply_count'] / max(p['like_count'], 1)
    txt = p['text'].replace('\n', ' ')[:100]
    print(f"  {p['id']} @{p['username']} L:{p['like_count']} RT:{p['retweet_count']} R:{p['reply_count']} ratio:{ratio:.3f}")
    print(f"    {txt}")

# Save all_posts for further processing
with open('/root/koma-x-automation/data/all_posts_raw.json', 'w') as f:
    json.dump(all_posts, f, ensure_ascii=False, indent=2)
print("\nSaved all_posts_raw.json")
