# 📈 Trader Job - AI-Powered Crypto Trading

> **Trinity's primary income source.** Hybrid AI/Technical analysis with Gemini Flash confirmation and Φ-based timing.

---

## 📁 Complete Structure (~35 files, ~300KB)

```
jobs/trader/
├── trader.py            # Main orchestrator (73KB, 1700+ lines)
├── config.py            # Configuration (20KB)
├── api.py               # REST endpoints (15KB)
│
├── strategy/            # Decision Engine
│   ├── brain.py         # Hybrid AI Brain (60KB, 1413 lines)
│   ├── signals.py       # Signal definitions
│   └── ai.py            # Gemini integration
│
├── intelligence/        # Advanced Analytics (9 files)
│   ├── optimizer.py     # Global strategy optimizer (25KB)
│   ├── panopticon.py    # Market surveillance
│   ├── quantum.py       # Coherence detection
│   ├── whales.py        # Whale tracking
│   ├── memory.py        # Pattern memory
│   ├── order_flow.py    # Order flow analysis
│   ├── portfolio.py     # Portfolio optimization
│   └── backtester.py    # Strategy backtesting
│
├── execution/           # Trade Execution
│   ├── positions.py     # Position management (37KB)
│   └── scanner.py       # Pair scanning
│
├── data/                # Data Pipeline
│   ├── history.py       # DuckDB deep history (32KB)
│   ├── feed.py          # Live data feed
│   ├── indicators.py    # Technical indicators
│   └── pulse.py         # Phi-beat heartbeat
│
├── kraken/              # Exchange Adapter
│   ├── exchange.py      # Kraken integration (56KB)
│   └── api.py           # API wrapper
│
├── reporting/           # Notifications (7 files)
│   ├── periodic.py      # Status reports
│   ├── night_cycle.py   # Nightly analysis
│   ├── analytics.py     # Performance metrics
│   ├── gamification.py  # Dopamine integration
│   └── hall_of_fame.py  # Best trades
│
└── maintenance/
    └── repair_pnl.py    # PnL repair utilities
```

---

## 🧠 Trading Brain - Hybrid Decision Engine

**60KB, 1413 lines** - The largest single file. Features:

### Lazy Evaluation Context
```python
class BrainContext:
    """Calculates indicators only when accessed."""
    
    @cached_property
    def rsi(self): return calculate_rsi(self.df)
    
    @cached_property
    def whale_activity(self): return whales.detect(self.pair)
```

### Available Indicators
- RSI, MACD, Bollinger Bands, ATR
- Fibonacci zones, EMA crossovers
- Volume spikes, whale sentiment
- Divergence detection

---

## 🔥 Unique Innovations

### 1. Phi-Beat Algorithm
Trading intervals follow **Golden Ratio (Φ 1.618)**:

```python
base_interval = 60  # seconds
organic_interval = base_interval * PHI  # 97 seconds
# Pattern indistinguishable from human activity
```

### 2. Gemini Flash Confirmation
Every trade validated by AI before execution (<100ms):

```python
confirmation = await gattaca.route(
    f"TRADE: {direction} {pair}. RSI:{rsi}, MACD:{macd}. YES/NO?",
    route_id=ROUTE_FLASH
)
```

### 3. Global Strategy Optimizer
Backtests 6 strategies across all pairs:

```python
# 2 modes × 3 variations = 6 strategies
STRATEGIES = [
    ("mitraillette", "DEFAULT"),
    ("mitraillette", "CONSERVATIVE"),
    ("mitraillette", "AGGRESSIVE"),
    ("sniper", "DEFAULT"),
    ("sniper", "CONSERVATIVE"),
    ("sniper", "AGGRESSIVE"),
]

# AI approval for mode switches
await optimizer._ask_ai_approval(current, best, improvement)
```

---

## 🧠 Intelligence Sub-Modules

| Module | Purpose |
|--------|---------|
| `optimizer.py` | Global strategy optimization via backtesting |
| `panopticon.py` | Multi-pair market surveillance |
| `quantum.py` | Cross-pair coherence detection |
| `whales.py` | Large holder tracking |
| `memory.py` | Pattern recognition memory |
| `order_flow.py` | Order book analysis |
| `portfolio.py` | Position weighting |
| `backtester.py` | Historical simulation |

---

## 📊 Data Pipeline

### DuckDB Deep History
```python
# data/history.py - 32KB
class DeepHistoryManager:
    """Stores 30+ days of OHLCV data per pair."""
    
    async def get_history(self, pair, periods=500):
        return self.duckdb.execute(
            "SELECT * FROM candles WHERE pair = ? ORDER BY time"
        )
```

### Technical Indicators
- RSI (14-period + custom)
- MACD (12, 26, 9)
- Bollinger Bands (20, 2)
- ATR (14-period)
- Fibonacci retracement zones
- Volume ratio spike detection

---

## 🦑 Kraken Integration

**56KB exchange.py** - Full async adapter:

- Spot + Futures support
- Rate limit handling
- Position management
- Order execution with retry

---

## 📈 Trading Modes

| Mode | Strategy | Pairs | Speed |
|------|----------|-------|-------|
| **Mitraillette** | High frequency | 144+ | Fast scans |
| **Sniper** | Precision | Top 10 | Deep analysis |

---

## 💰 FinOps Integration

```python
# reporting/gamification.py
if trade.profit > 0:
    manager.update_objective("trader_profit", trade.profit)
    # → hormones.stimulate("dopamine", 0.5)
```

---

> **Key Insight**: The Trader combines classical technical analysis with AI confirmation. Every trade passes through Gemini Flash before execution - achieving HFT-speed decisions with AI validation.
