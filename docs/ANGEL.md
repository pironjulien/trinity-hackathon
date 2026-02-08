# 👼 Angel.py - The Guardian Supervisor

> **The protective layer.** Process manager, HTTP proxy, and self-healing watchdog.

---

## 📊 Overview

| Metric | Value |
|--------|-------|
| **Lines** | 2,639 |
| **Size** | 97KB |
| **Framework** | FastAPI |
| **Port** | 8888 (Gateway) |

---

## 🏛️ Philosophy

```
"Disk Truth" - State persisted to disk is the source of truth
"Self-Healing" - Auto-recover from failures
"Singleton Enforcement" - Only one Trinity instance allowed
```

---

## 🔧 Core Components

### 1. SubProcessManager
Manages Trinity and other child processes:

```python
class SubProcessManager:
    def __init__(self, name, script, port):
        self.name = name
        self.script = script
        self.port = port
        
    async def start(self):  # Launch subprocess
    async def stop(self):   # Graceful shutdown
```

### 2. WebSocket Hub
Real-time log broadcasting:

```python
class LogsWebSocketHub:
    async def connect(self, websocket)
    async def broadcast(self, message)
    async def broadcast_clear(self, tab)
```

### 3. Zombie Process Killer
Surgical removal of stale processes:

```python
async def _kill_zombie_processes():
    # Kills any non-managed Trinity processes
    # Enforces singleton pattern
```

---

## 🔄 Watchdog Loop

```python
WATCHDOG_INTERVAL = 5  # Fibonacci F5

async def watchdog():
    while True:
        if not trinity.is_running():
            await trinity.start()
        await asyncio.sleep(WATCHDOG_INTERVAL)
```

---

## 📡 HTTP Proxy

Angel proxies requests to Trinity:

```
Client → Angel:8888 → Trinity:8000
                ↓
         WebSocket Hub (logs)
         Static Files (web app)
```

---

## 🛡️ Security Features

| Feature | Purpose |
|---------|---------|
| Rate limiting | Anti brute-force |
| API key validation | External access control |
| Real IP detection | Bypass proxy headers |

```python
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")
```

---

## 📝 Logging

```python
ANGEL_LOG = LOGS_DIR / "angel.jsonl"
ALERTS_LOG = LOGS_DIR / "alerts.jsonl"
TRINITY_LOG = LOGS_DIR / "trinity.jsonl"

def log_event(level, message, stream="angel"):
    # Atomic append to JSONL
    # WebSocket broadcast to clients
```

### Fibonacci Log Rotation
```python
def _rotate_log_if_needed(filepath, max_lines, keep_lines):
    # Truncate when exceeding max
    # Keep last N lines
```

---

## 🔗 Managed Processes

| Process | Script | Port |
|---------|--------|------|
| Trinity | trinity.py | 8000 |
| MCP | (optional) | 8090 |

---

> **Key Insight**: Angel is the immune system - it protects Trinity from crashes, zombies, and external threats while providing a unified gateway for all communication.
