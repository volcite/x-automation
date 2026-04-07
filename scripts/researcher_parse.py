#!/usr/bin/env python3
"""Parse X API query results and show top posts"""
import json
import sys
import os

def parse_file(filepath, label):
    if not os.path.exists(filepath):
        print(f"[{label}] File not found: {filepath}")
        return []

    with open(filepath) as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"[{label}] JSON parse error: {e}")
            return []

    if 'errors' in data and 'data' not in data:
        print(f"[{label}] API Error: {data['errors']}")
        return []

    if 'data' not in data:
        print(f"[{label}] No data: {str(data)[:200]}")
        return []

    tweets = data['data']
    users = {}
    if 'includes' in data and 'users' in data['includes']:
        for u in data['includes']['users']:
            users[u['id']] = u

    result = []
    for t in tweets:
        m = t.get('public_metrics', {})
        user = users.get(t.get('author_id', ''), {})
        result.append({
            'id': t['id'],
            'text': t['text'],
            'created_at': t.get('created_at', ''),
            'author_id': t.get('author_id', ''),
            'username': user.get('username', 'unknown'),
            'like_count': m.get('like_count', 0),
            'retweet_count': m.get('retweet_count', 0),
            'reply_count': m.get('reply_count', 0),
            'impression_count': m.get('impression_count', 0),
            'quote_count': m.get('quote_count', 0),
        })

    result.sort(key=lambda x: x['like_count'], reverse=True)

    print(f"\n=== [{label}] {len(result)} tweets fetched ===")
    for i, t in enumerate(result[:5]):
        ratio = t['reply_count'] / t['like_count'] if t['like_count'] > 0 else 0
        print(f"  #{i+1} likes={t['like_count']} rt={t['retweet_count']} reply={t['reply_count']} (ratio={ratio:.2f}) @{t['username']}")
        print(f"      id={t['id']} text={t['text'][:100]}")

    return result

if __name__ == '__main__':
    data_dir = '/root/koma-x-automation/data'
    files = [
        ('rq1_claude_code_en.json', 'Claude Code EN'),
        ('rq2_claude_agent_en.json', 'Claude Agent EN'),
        ('rq3_ai_auto_en.json', 'AI Automation EN'),
        ('rq4_anthropic_en.json', 'Anthropic EN'),
        ('rq5_n8n_ai_en.json', 'n8n AI EN'),
        ('rq6_claude_code_ja.json', 'Claude Code JA'),
        ('rq7_ai_agent_ja.json', 'AI Agent JA'),
        ('rq8_ai_auto_ja.json', 'AI Auto JA'),
        ('rq9_genai_ja.json', 'GenAI JA'),
        ('rq10_keitowebai.json', '@keitowebai'),
        ('rq11_masahirochaen.json', '@masahirochaen'),
        ('rq12_kohaku_nft.json', '@Kohaku_NFT'),
    ]

    all_results = {}
    for fname, label in files:
        fpath = os.path.join(data_dir, fname)
        results = parse_file(fpath, label)
        all_results[label] = results

    # Show buzz posts (likes >= 50)
    print("\n\n=== BUZZ POSTS (likes >= 50) ===")
    buzz = []
    for label, tweets in all_results.items():
        for t in tweets:
            if t['like_count'] >= 50:
                t['query_label'] = label
                buzz.append(t)
    buzz.sort(key=lambda x: x['like_count'], reverse=True)
    for t in buzz[:20]:
        ratio = t['reply_count'] / t['like_count'] if t['like_count'] > 0 else 0
        print(f"likes={t['like_count']} rt={t['retweet_count']} reply={t['reply_count']} ratio={ratio:.2f} [{t['query_label']}] @{t['username']}")
        print(f"  id={t['id']} text={t['text'][:120]}")

    print(f"\nTotal buzz posts: {len(buzz)}")
