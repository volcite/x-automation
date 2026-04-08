#!/bin/bash
# All-in-one X API search + parse script
# Usage: bash run_xapi.sh "QUERY" max_results
QUERY="$1"
MAX="${2:-50}"
TOKEN="AAAAAAAAAAAAAAAAAAAAAH/88QEAAAAASsWXEUi28FfZlST0Zps2LStJmcE=4Uly3FCyOIpRz6mrMoQdkDl9NQknTQjTH8FA2JO6VlqMi8xmvJ"

curl -s --max-time 15 -G "https://api.x.com/2/tweets/search/recent" \
  --data-urlencode "query=${QUERY}" \
  --data-urlencode "max_results=${MAX}" \
  --data-urlencode "tweet.fields=public_metrics,created_at,author_id,entities" \
  --data-urlencode "expansions=author_id" \
  --data-urlencode "user.fields=username,name,public_metrics" \
  -H "Authorization: Bearer ${TOKEN}" | python3 /root/koma-x-automation/scripts/parse_tweets.py
