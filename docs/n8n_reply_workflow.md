# n8n リプライ自動返信 ワークフロー構築ガイド

## 全体の流れ

```
30分ごと
   │
   ▼
┌─────────────────────────────────────────────────────┐
│ n8n                                                 │
│                                                     │
│ [Cron 30分] ──▶ [X API] リプライ取得                │
│                  (since_id で重複排除)               │
│                       │                             │
│                       │ 新着あり                     │
│                       ▼                             │
│                 [JSON整形]                           │
│                  ・元投稿テキスト付与                  │
│                  ・会話履歴付与                       │
│                       │                             │
│                       ▼                             │
│                 [SSH実行]                            │
│                  pipeline_reply.sh                   │
│                       │                             │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ Claude Code サーバー                                 │
│                                                     │
│  pipeline_reply.sh                                  │
│    ├─ 上限チェック（150件/日, 15件/回）              │
│    ├─ community_manager エージェント実行              │
│    │   ├─ 文脈理解 → 分類 → 品質チェック             │
│    │   ├─ confidence: high/medium → 返信生成         │
│    │   └─ confidence: low → スキップ（返信しない）    │
│    └─ Webhook で返信JSONをn8nへ送信                  │
│                                                     │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ n8n (Webhook受信)                                   │
│                                                     │
│ [Webhook] ──▶ [replies配列を展開]                    │
│                       │                             │
│              ┌────────┼────────┐                    │
│              ▼        ▼        ▼                    │
│          返信①    返信②    返信③                    │
│              │        │        │                    │
│         [Wait]   [Wait]   [Wait]                    │
│         1-3分    1-3分    1-3分   ← ランダム間隔     │
│              │        │        │                    │
│         [X API]  [X API]  [X API]                   │
│         返信投稿  返信投稿  返信投稿                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## シャドウバン対策

```
 ┌───────────────────────────────────────────┐
 │ 量の制限                                   │
 │  ・1日150件まで / 1回あたり15件まで         │
 │  ・30分間隔で取得 → 一度に大量処理しない     │
 ├───────────────────────────────────────────┤
 │ タイミングの自然さ（n8n側で制御）            │
 │  ・返信間: 1-3分のランダム間隔              │
 │  ・一括送信しない → 1件ずつ順番に投稿       │
 ├───────────────────────────────────────────┤
 │ 品質による自動フィルタ（Claude Code側）     │
 │  ・文脈が不明 → 返信しない                 │
 │  ・嘘になるリスク → 返信しない              │
 │  ・定型的すぎる → 返信しない               │
 │  ・confidence: low → 自動スキップ          │
 └───────────────────────────────────────────┘
```

---

## n8n ノード構成（詳細）

### 1. Schedule Trigger
```
毎30分実行
```

### 2. X API: メンション取得
```
HTTP Request ノード
  Method: GET
  URL: https://api.twitter.com/2/users/:id/mentions
  Parameters:
    since_id: {{ $workflow.staticData.last_mention_id }}
    max_results: 50
    tweet.fields: text,author_id,conversation_id,in_reply_to_user_id,referenced_tweets
    expansions: author_id,referenced_tweets.id
  Authentication: OAuth 2.0
```

### 3. IF: 新着あり？
```
条件: {{ $json.meta.result_count > 0 }}
```

### 4. Code: JSON整形 + since_id更新

```javascript
const data = $input.first().json;

// since_id 更新（次回取得時の重複排除）
if (data.meta?.newest_id) {
  $workflow.staticData.last_mention_id = data.meta.newest_id;
}

const tweets = data.data || [];
const users = {};
(data.includes?.users || []).forEach(u => {
  users[u.id] = u.username;
});

// 元投稿のテキストを取得（referenced_tweets から）
const refTweets = {};
(data.includes?.tweets || []).forEach(t => {
  refTweets[t.id] = t.text;
});

const formatted = tweets.map(t => {
  const replyTo = t.referenced_tweets?.find(r => r.type === 'replied_to');
  const originalText = replyTo ? (refTweets[replyTo.id] || '') : '';

  return {
    tweet_id: t.id,
    author: `@${users[t.author_id] || t.author_id}`,
    text: t.text,
    my_original_post: originalText,
    conversation_history: []
  };
});

return [{ json: formatted }];
```

### 5. Write Binary File
```
パス: /tmp/reply_input.json
内容: {{ JSON.stringify($json) }}
```

### 6. SSH: pipeline_reply.sh 実行
```
コマンド:
  cd /path/to/x-automation && bash scripts/pipeline_reply.sh /tmp/reply_input.json
```

### 7. Webhook (別ワークフロー): 返信受信

```
Webhook ノード
  Method: POST
  Path: /reply-handler
```

### 8. Code: replies配列を展開
```javascript
const data = $input.first().json;
const replies = data.replies || [];

return replies
  .filter(r => r.confidence !== 'low')
  .map(r => ({ json: r }));
```

### 9. Split In Batches
```
Batch Size: 1
```

### 10. Wait: ランダム間隔
```
Resume: After Time Interval
Amount: {{ Math.floor(Math.random() * 120 + 60) }}
Unit: Seconds

→ 1分〜3分のランダム間隔
```

### 11. X API: リプライ投稿
```
HTTP Request ノード
  Method: POST
  URL: https://api.twitter.com/2/tweets
  Body (JSON):
    {
      "text": "{{ $json.content }}",
      "reply": {
        "in_reply_to_tweet_id": "{{ $json.to_tweet_id }}"
      }
    }
  Authentication: OAuth 2.0
```

---

## 会話履歴の取得（推奨・品質向上）

元投稿だけでなくスレッドの会話履歴も渡すと、返信の精度が上がります。

```javascript
// 各メンションの conversation_id から会話を取得
for (const mention of formatted) {
  try {
    const conv = await this.helpers.httpRequest({
      method: 'GET',
      url: `https://api.twitter.com/2/tweets/search/recent`,
      qs: {
        query: `conversation_id:${mention.conversation_id}`,
        'tweet.fields': 'text,author_id,created_at',
        max_results: 10
      },
      headers: { Authorization: `Bearer ${credentials.accessToken}` }
    });

    mention.conversation_history = (conv.data || [])
      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      .map(t => ({
        author: `@${users[t.author_id] || t.author_id}`,
        text: t.text
      }));
  } catch (e) {
    // 取得失敗は空配列のまま
  }
}
```

---

## エラーハンドリング

### X API 429 (レート制限)
```javascript
if ($json.statusCode === 429) {
  const resetTime = $json.headers['x-rate-limit-reset'];
  const waitSec = resetTime - Math.floor(Date.now() / 1000) + 10;
  // Wait ノードで待機後リトライ
}
```

### SSH失敗時
```
Error Trigger → Slack/Discord通知
  "リプライパイプライン失敗: {{ $json.stderr }}"
```

---

## .env 設定
```bash
WEBHOOK_URL=https://your-n8n.com/webhook/morning-post
REPLY_WEBHOOK_URL=https://your-n8n.com/webhook/reply-handler
```

## テスト用ダミーJSON

```json
[
  {
    "tweet_id": "test_001",
    "author": "@test_user",
    "text": "これ試してみたんですけど、めちゃくちゃ便利ですね！設定で迷ったところがあったので質問いいですか？",
    "my_original_post": "n8nでXの投稿を自動化する方法をまとめました。意外とシンプルにできるので、気になる方はぜひ。",
    "conversation_history": []
  },
  {
    "tweet_id": "test_002",
    "author": "@another_user",
    "text": "わかるーーー自分も同じこと思ってました",
    "my_original_post": "自動化って最初の設定がだるいんですけど、一回動き出すともう手動には戻れないですよね...",
    "conversation_history": []
  }
]
```
