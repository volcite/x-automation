#!/usr/bin/env python3
import subprocess
import json

TOKEN = "AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"

cmd = [
    "curl", "-s", "--max-time", "15", "-G",
    "https://api.x.com/2/tweets/search/recent",
    "--data-urlencode", "query=Claude Code -is:reply -is:retweet",
    "--data-urlencode", "max_results=10",
    "--data-urlencode", "tweet.fields=public_metrics,created_at",
    "-H", f"Authorization: Bearer {TOKEN}"
]
result = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
