# 🧬 Trinity.py - The Neural Core

> **The brain itself.** A FastAPI server providing Trinity's computation, logic, and API endpoints.

---

## 📊 Overview

| Metric | Value |
|--------|-------|
| **Lines** | 942 |
| **Size** | 36KB |
| **Framework** | FastAPI |
| **Port** | 8000 |

---

## 🧠 Architecture

```
trinity.py = Headless Worker (No WebSockets)
    ↓ Managed by
angel.py = Supervisor + HTTP Proxy
```

---

## 🔧 Core Sections

### 1. JSONL Logging Sink
Routes logs to module-specific files:

```python
_LOG_ROUTES = {
    "jobs.trader": "trader.jsonl",
    "jobs.influencer": "influencer.jsonl",
    "jobs.youtuber": "youtuber.jsonl",
    "social": "social.jsonl",
    "corpus": "trinity.jsonl",
    "jules": "jules.jsonl",
}
```

### 2. Lifecycle Management
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Boot jobs, scheduler, triggers
    yield
    # Shutdown: Graceful cleanup
```

### 3. Security (SOTA 2026)
- Rate limiting (anti brute-force)
- Security headers middleware
- RBAC token validation
- Shared secret for IPC (Angel ↔ Trinity)

### 4. Background Loops
```python
monitor_triggers()      # Proactive evaluation every 5 min
monitor_gamification()  # Update objectives (uptime, efficiency)
```

---

## 🔐 Authentication

| Role | Access |
|------|--------|
| `god` | Full control |
| `worker` | Read + limited actions |
| `viewer` | Read-only |

```python
@app.post("/auth/login")
async def auth_login(req: LoginRequest):
    # Validate credentials → Issue token
```

---

## 📡 Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Version info |
| `GET /health` | Health check |
| `POST /auth/login` | Authentication |
| `GET /vitals` | System vitals |
| `GET /jobs` | Job status |
| `POST /hormones/reset` | Reset hormonal levels |

---

## 🔗 Integration

Trinity imports from:
- `corpus.brain.*` - Neural modules
- `corpus.dna.*` - Configuration
- `corpus.soma.*` - Body systems
- `jobs.*` - Revenue generators

---

> **Key Insight**: Trinity is a pure computation node. All user-facing features (WebSockets, static files) are handled by Angel.
