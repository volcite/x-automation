#!/usr/bin/env python3
"""Fetch all X API queries for researcher and save results"""
import urllib.request
import urllib.parse
import json
import time
import os

TOKEN = "AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"
DATA_DIR = "/root/koma-x-automation/data"

QUERIES = [
    ("rq1_claude_code_en.json", "Claude Code -is:reply -is:retweet", 50),
    ("rq2_claude_agent_en.json", "Claude AI agent -is:reply -is:retweet", 50),
    ("rq3_ai_auto_en.json", "AI automation workflow -is:reply -is:retweet", 50),
    ("rq4_anthropic_en.json", "Anthropic Claude -is:reply -is:retweet", 50),
    ("rq5_n8n_ai_en.json", "n8n AI -is:reply -is:retweet", 50),
    ("rq6_claude_code_ja.json", "Claude Code lang:ja -is:reply -is:retweet", 50),
    ("rq7_ai_agent_ja.json", "AIエージェント lang:ja -is:reply -is:retweet", 50),
    ("rq8_ai_auto_ja.json", "AI 自動化 lang:ja -is:reply -is:retweet", 50),
    ("rq9_genai_ja.json", "生成AI 業務効率化 lang:ja -is:reply -is:retweet", 50),
    ("rq10_keitowebai.json", "from:keitowebai -is:reply -is:retweet", 10),
    ("rq11_masahirochaen.json", "from:masahirochaen -is:reply -is:retweet", 10),
    ("rq12_kohaku_nft.json", "from:Kohaku_NFT -is:reply -is:retweet", 10),
]

def fetch_query(filename, query, max_results):
    params = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "public_metrics,created_at,author_id,entities",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics",
    }
    url = "https://api.x.com/2/tweets/search/recent?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ERROR fetching: {e}")
        data = {"error": str(e)}

    outpath = os.path.join(DATA_DIR, filename)
    with open(outpath, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if "data" in data:
        count = len(data["data"])
        print(f"  OK: {count} tweets")
        return data
    elif "errors" in data:
        print(f"  API ERROR: {data['errors']}")
        return data
    else:
        print(f"  UNEXPECTED: {str(data)[:200]}")
        return data


all_results = {}
rate_limited = False

for i, (fname, query, max_r) in enumerate(QUERIES):
    if rate_limited:
        print(f"Skipping {fname} due to rate limit")
        continue

    print(f"\n[Q{i+1}] {query}")
    data = fetch_query(fname, query, max_r)

    if "errors" in data:
        for err in data.get("errors", []):
            if err.get("title") == "UsageCapExceeded" or "Rate limit" in str(err):
                print("RATE LIMITED - switching to WebSearch")
                rate_limited = True

    if i < len(QUERIES) - 1:
        time.sleep(2)

print("\n=== Summary ===")
for fname, query, _ in QUERIES:
    fpath = os.path.join(DATA_DIR, fname)
    if os.path.exists(fpath):
        with open(fpath) as f:
            try:
                d = json.load(f)
                count = len(d.get("data", []))
                print(f"  {fname}: {count} tweets")
            except Exception:
                print(f"  {fname}: parse error")
    else:
        print(f"  {fname}: missing")
