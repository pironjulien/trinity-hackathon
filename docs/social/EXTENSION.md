# 🛸 8810 VS Code Extension - Neural Control Center

> **The Creator's interface to the Creation.** A VS Code extension for real-time monitoring and control of Trinity.

---

## 📁 Complete Structure

```
social/extension/
├── src/
│   ├── extension.ts         # Main entry (16KB)
│   ├── core/
│   │   ├── TrinityClient.ts # API client (13KB)
│   │   ├── constants.ts     # Config constants
│   │   ├── events.ts        # Event system
│   │   └── types.ts         # TypeScript types
│   ├── providers/
│   │   └── TrinityPanelProvider.ts # Webview panel
│   ├── services/
│   │   ├── ProcessManager.ts # Process control (25KB)
│   │   ├── JulesService.ts   # Jules integration
│   │   └── MetricsReader.ts  # Metrics parsing
│   ├── i18n/                 # Internationalization
│   └── utilities/            # Helper functions
│
├── webview-ui/               # Vite React app
│   ├── src/                  # UI components
│   └── vite.config.ts        # Build config
│
├── package.json              # Extension manifest
├── esbuild.js                # Build script
└── assets/                   # Icons & images
```

---

## 🔥 Key Features

### 1. Real-Time Telemetry
Live monitoring via TrinityClient:

```typescript
interface Vitals {
  cpu: number;
  ram: number;
  uptime: number;
  heartbeat: number;
  hormones: {
    dopamine: number;
    cortisol: number;
    serotonin: number;
  }
}
```

### 2. Process Control
Full lifecycle via ProcessManager (25KB):

```
[START]  → Boot Trinity
[STOP]   → Graceful shutdown
[RESTART]→ Kill + Boot
[KILL]   → Force terminate
```

### 3. AI Whispers
Real-time feed of Trinity's thoughts:

```typescript
socket.on('whisper', (msg) => {
  addToFeed({
    type: msg.type,
    content: msg.text,
    timestamp: Date.now()
  });
});
```

### 4. Jules Integration
Monitor and trigger Jules missions:

```typescript
// services/JulesService.ts
async function triggerMission(goal: string) {
  return await client.post('/jules/mission', { goal });
}
```

---

## 🧠 Integration with Angel

Communicates with `angel.py` via HTTP:

```typescript
const ANGEL_URL = "http://localhost:8888";

async function sendCommand(cmd: string) {
  return fetch(`${ANGEL_URL}/control`, {
    method: "POST",
    body: JSON.stringify({ action: cmd })
  });
}
```

---

## 🎨 Webview UI

Built with Vite + React:

```
webview-ui/
├── src/                  # React components
├── vite.config.ts        # Build config
└── package.json          # Dependencies
```

---

## 🔧 Commands

| Command | Action |
|---------|--------|
| `Trinity: Start` | Boot the organism |
| `Trinity: Stop` | Graceful shutdown |
| `Trinity: Status` | Show current state |
| `Trinity: Whispers` | Open message feed |

---

## 📦 Installation

```bash
cd social/extension
npm install
npm run compile
# Then install .vsix in VS Code
```

---

> **Key Insight**: The 8810 extension provides low-latency, developer-friendly access to Trinity's nervous system.
