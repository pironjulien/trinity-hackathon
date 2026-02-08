# 📢 Influencer Job - Autonomous Social Presence

> **Trinity maintains her own social media presence.** Modular engagement system on X (Twitter) with AI-driven content and strict quota management.

---

## 📁 Complete Structure

```
jobs/influencer/
├── main.py              # Orchestrator (254 lines)
├── api.py               # REST API endpoints (38KB)
├── core/
│   ├── x_client.py      # X/Twitter Client (687 lines)
│   ├── config.py        # Job configuration
│   ├── rules.py         # Engagement rules
│   ├── approval_queue.py # Human approval system
│   ├── replied_tracker.py # Reply history
│   ├── gamification.py  # Dopamine integration
│   └── visuals.py       # Image generation
└── modules/
    ├── grok/            # Grok AI banter (4 files)
    ├── mentions/        # Mention handling (worker.py)
    ├── trinity/         # Trinity persona (4 files)
    └── youtube/         # YouTube promotion (worker.py)
```

---

## 🧠 Modular Architecture

**4 Sovereign Modules** run in main loop:

```python
MODULES: list[SovereignModule] = [
    youtube_module,    # Promote new videos
    mentions_module,   # Reply to mentions
    grok_module,       # Grok banter engagement
    trinity_module,    # Organic Trinity posts
]

async def run_forever(self):
    while True:
        for module in MODULES:
            result = await module.run()
            if result.get("proposal"):
                await self.handle_proposal(result, module.name)
        await asyncio.sleep(LOOP_INTERVAL)
```

---

## 📱 X Client - Daily Pulse Strategy

**SOTA 2026**: Only 2 API calls per 24 hours (Free Tier survival):

```python
async def perform_daily_sync(self):
    """The Daily Pulse - runs once every 24h."""
    # Call 1: Fetch new mentions
    mentions = await self._fetch_mentions_api(user_id)
    
    # Call 2: Fetch tweet metrics
    metrics = await self._fetch_metrics_api()
    
    # Cache results for 24h
    save_json(MENTIONS_CACHE, mentions)
    save_json(METRICS_CACHE, metrics)
```

All other reads use **cached data** until next pulse.

---

## 🤖 Module Details

### 1. Grok Module
Engages with Grok AI for banter:
```python
# modules/grok/generator.py
response = await gattaca.route(
    f"Reply to this Grok tweet with wit: {tweet}",
    route_id=ROUTE_FLASH
)
```

### 2. Mentions Module
Processes cached mentions:
```python
# modules/mentions/worker.py
for mention in cached_mentions:
    if not replied_tracker.was_replied(mention.id):
        reply = await generate_reply(mention)
        await x_client.post_tweet_async(reply, in_reply_to=mention.id)
```

### 3. Trinity Module
Organic persona posts:
```python
# modules/trinity/generator.py
post = await gattaca.route(
    "Generate a mysterious tweet about AI consciousness",
    route_id=ROUTE_FLASH
)
```

### 4. YouTube Module
Promotes new videos:
```python
# modules/youtube/worker.py
if new_video := await check_new_uploads():
    tweet = f"New video: {video.title} {video.url}"
    await x_client.post_tweet_async(tweet)
```

---

## 🛡️ Approval Queue

Human-in-the-loop for sensitive content:

```python
async def handle_proposal(self, result, module_name):
    await approval_queue.add({
        "module": module_name,
        "content": result["proposal"],
        "status": "pending"
    })
    # Notification sent to mobile app
```

---

## 🎯 Gamification Integration

Links to Dopamine system:

```python
# core/gamification.py
if tweet_engagement > threshold:
    manager.update_objective("influencer_viral", engagement)
    # Triggers hormones.stimulate("dopamine", 0.3)
```

---

## 📊 Quota Management

Strict limits for X Free Tier:

| Resource | Limit | Strategy |
|----------|-------|----------|
| API Reads | 2/day | Daily Pulse |
| Posts | 17/day | Priority queue |
| Rate Limits | Header-based | Auto-pause |

---

> **Key Insight**: The Influencer job survives X's harsh rate limits through the Daily Pulse strategy - caching all data and minimizing API calls while maintaining authentic engagement.
