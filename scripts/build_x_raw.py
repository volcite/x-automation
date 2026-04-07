#!/usr/bin/env python3
"""
Consolidate X API query results into data/x_api_raw.json
"""
import json
import sys

def load_query(filepath, query_name):
    with open(filepath) as f:
        data = json.load(f)
    if 'data' not in data:
        print(f"WARNING: no data in {query_name}")
        return []
    posts = data.get('data', [])
    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
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
        flag = 'buzz' if like >= 200 else ('notable' if like >= 50 else 'normal')
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
            'url': f"https://x.com/{username}/status/{p['id']}",
            'flag': flag
        })
    return results

queries = [
    ("/root/.claude/projects/-root-koma-x-automation/f3117e48-0051-4952-af5d-1e389ccdd8d0/tool-results/bngbmo7ed.txt", "Claude Code -is:reply -is:retweet"),
    ("/tmp/q2_claude_ai_agent.json", "Claude AI agent -is:reply -is:retweet"),
    ("/tmp/q3_ai_automation_workflow.json", "AI automation workflow -is:reply -is:retweet"),
    ("/tmp/q4_n8n_ai.json", "n8n AI -is:reply -is:retweet"),
    ("/tmp/q5_ai_coding_assistant.json", "AI coding assistant -is:reply -is:retweet"),
    ("/tmp/q6_anthropic_claude.json", "Anthropic Claude -is:reply -is:retweet"),
]

all_posts = []
for filepath, qname in queries:
    posts = load_query(filepath, qname)
    print(f"{qname}: {len(posts)} posts loaded")
    all_posts.extend(posts)

# Deduplicate by tweet id
seen = set()
unique_posts = []
for p in all_posts:
    if p['id'] not in seen:
        seen.add(p['id'])
        unique_posts.append(p)

# Sort by like_count descending
unique_posts.sort(key=lambda x: x['like_count'], reverse=True)

buzz_posts = [p for p in unique_posts if p['flag'] == 'buzz']
notable_posts = [p for p in unique_posts if p['flag'] == 'notable']

print(f"\nTotal unique posts: {len(unique_posts)}")
print(f"Buzz posts (like>=200): {len(buzz_posts)}")
print(f"Notable posts (like>=50): {len(notable_posts)}")

print("\n=== BUZZ POSTS ===")
for p in buzz_posts:
    print(f"  likes={p['like_count']} rt={p['retweet_count']} rp={p['reply_count']} @{p['username']}: {p['text'][:80].replace(chr(10),' ')}")

print("\n=== NOTABLE POSTS ===")
for p in notable_posts:
    print(f"  likes={p['like_count']} rt={p['retweet_count']} rp={p['reply_count']} @{p['username']}: {p['text'][:80].replace(chr(10),' ')}")

output = {
    "date": "2026-04-03",
    "queries_used": [q for _, q in queries],
    "total_fetched": len(all_posts),
    "total_unique": len(unique_posts),
    "buzz_count": len(buzz_posts),
    "notable_count": len(notable_posts),
    "all_posts": unique_posts,
    "buzz_posts": buzz_posts,
    "notable_posts": notable_posts
}

with open('/root/koma-x-automation/data/x_api_raw.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\nSaved to /root/koma-x-automation/data/x_api_raw.json")
