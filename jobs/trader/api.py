"""
JOBS/TRADER/API.PY
==============================================================================
MODULE: Trader API Endpoints (Dynamic Mount)
PURPOSE: Provides REST endpoints for TraderPanel UI.
         Mounted dynamically when trader job starts.
         Trinity remains functional without this.
==============================================================================
"""

from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from jobs.trader.config import (
    MITRAILLETTE,
    SNIPER,
    MITRAILLETTE_RANGES,
    SNIPER_RANGES,
    MEMORIES_DIR,
    TraderConfig,
)
from corpus.soma.cells import load_json

# Router for dynamic mounting
router = APIRouter(prefix="/api/trader", tags=["trader"])


class TraderConfigUpdate(BaseModel):
    mode: Optional[str] = None  # "sniper" | "mitraillette" | "ia" | "manual"
    level: Optional[int] = None  # 0=LOW, 1=DEFAULT, 2=HIGH
    ai_enabled: Optional[bool] = None
    paused: Optional[bool] = None
    panopticon_enabled: Optional[bool] = None
    earn: Optional[bool] = None
    whales_enabled: Optional[bool] = None
    ai_buy_validation: Optional[bool] = None
    manual_strategy: Optional[Dict[str, Any]] = None

    # SOTA v5.9: Options manquantes corrigées
    ghost_mode_enabled: Optional[bool] = None  # 👻 Ghost Mode (virtual stops)
    quantum_enabled: Optional[bool] = None  # ⚛️ Quantum Pulse
    golden_memory_autoexec: Optional[bool] = None  # 🧠 Golden Memory auto-exec

    # Advanced Options (Notifications/Timing/AI)
    notify_buys: Optional[bool] = None
    notify_sells: Optional[bool] = None
    notify_reports: Optional[bool] = None
    notify_mutations: Optional[bool] = None
    report_interval: Optional[int] = None
    circuit_breaker_enabled: Optional[bool] = None
    ai_lock_level: Optional[bool] = None  # Lock level (prevent optimizer override)
    use_golden_ratchet: Optional[bool] = (
        None  # SOTA v5.8: True = trailing stop, False = fixed TP
    )
    dca_enabled: Optional[bool] = None  # DCA (Dollar Cost Averaging)


# Reference to trader instance (set by trader.py on start)
_trader_instance = None


def set_trader_instance(trader):
    """Called by TradingHeart on start to register itself."""
    global _trader_instance
    _trader_instance = trader
    logger.info("📊 API registered")


def clear_trader_instance():
    """Called by TradingHeart on stop."""
    global _trader_instance
    _trader_instance = None
    logger.info("📊 API unregistered")


def _get_ia_state() -> dict:
    """Read IA optimizer's active configuration."""
    config_path = MEMORIES_DIR / "trader" / "active_config.json"
    config = load_json(config_path, default={})
    return {
        "active_mode": config.get("active_mode", "mitraillette"),
        "active_variation": config.get("active_variation", "DEFAULT"),
        "recommended_mode": config.get("recommended_mode"),
        "recommended_variation": config.get("recommended_variation"),
        "last_optimization": config.get("last_optimization"),
    }


@router.get("/status")
async def get_trader_status(refresh: bool = False):
    """
    Get trader status.
    SOTA 2026: Works OFFLINE by reading config from disk.
    refresh=True -> Triggers background update (Fire & Forget).
    """
    # Load config from disk (always available)
    try:
        config = TraderConfig.load()
    except Exception:
        config = TraderConfig()  # default

    # SHARED: Load Persisted Data (Real Truth)
    # This logic applies whenever we don't have a fresh live report (Offline or Booting)

    # 1. Load Files
    state = load_json(MEMORIES_DIR / "trader" / "state.json", default={})
    portfolio = load_json(MEMORIES_DIR / "trader" / "portfolio.json", default={})
    pulse = load_json(MEMORIES_DIR / "trader" / "pulse.json", default={})  # Sentiment
    perf = portfolio.get("performance", {})

    # 2. Parse Positions
    raw_positions = portfolio.get("positions", [])
    positions_dict = {}
    positions_val = 0.0

    for p in raw_positions:
        pair = p.get("pair")
        if pair:
            q = float(p.get("quantity", 0))
            entry_price = float(p.get("entry_price", 0))
            current_price = float(p.get("current_price", 0))
            p["cost"] = q * entry_price
            p["value"] = q * current_price
            positions_dict[pair] = p
            positions_val += p["value"]

    # 3. Derived Stats
    wins = int(perf.get("wins", 0))
    losses = int(perf.get("losses", 0))
    total_battles = wins + losses
    win_rate = (wins / total_battles * 100) if total_battles > 0 else 0
    btc_qty = float(perf.get("btc_piggy_bank", 0))

    # 4. DuckDB: Price & History (Real Data)
    from jobs.trader.data.history import create_history

    db_trades = []
    last_btc_price = 0.0

    try:
        chronos = create_history()
        # Async calls in sync context (FastAPI handles it if we await, but here we are in async def)
        last_btc_price = await chronos.get_latest_price()
        db_trades = await chronos.get_recent_trades()
    except Exception as e:
        logger.error(f"🕐 [DATA] Chronos API Error: {e}")

    # 5. Final Real Values
    btc_val_eur = btc_qty * last_btc_price if last_btc_price > 0 else 0.0
    capital_actif = positions_val
    total_sys = capital_actif + btc_val_eur

    # 6. Sentiment (Real)
    # If pulse has data, use it. Else 0 (No Fake Neutral)
    sentiment_score = pulse.get("score", 0)

    # 7. Construct Report
    persisted_report = {
        "regime": "OFFLINE",
        "btc_24h": last_btc_price,
        "sentiment": sentiment_score,  # Real Score
        "mode": "🛑 OFF",
        "submode": "OFF",
        "cycle": state.get("_cycle_count", 0),  # Real Cycle
        "total_capital": total_sys,
        "capital_actif": capital_actif,
        "cash": 0,
        "positions_value": positions_val,
        "positions": positions_dict,
        "btc_total": btc_qty,
        "btc_earn": btc_qty,
        "btc_value": btc_val_eur,
        "cagnotte": btc_val_eur,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "pnl_daily": state.get("session_pnl", 0),
        "pnl_global": perf.get("total_profit", 0),
        "trades_history": db_trades,
        "circuit_breaker": state.get("circuit_breaker", False),
    }

    # If offline, load persisted state/portfolio to avoid empty UI
    if not _trader_instance:
        return {
            "status": "offline",
            "report": persisted_report,
            "config": {
                "mode": config.mode,
                "level": config.level,
                "ai_enabled": config.ai_enabled,
                "earn": config.earn,
                "paused": config.paused,
                "panopticon_enabled": config.panopticon_enabled,
                "whales_enabled": config.whales_enabled,
                "ai_buy_validation": config.ai_buy_validation,
                # Advanced
                "notify_buys": config.notify_buys,
                "notify_sells": config.notify_sells,
                "notify_reports": config.notify_reports,
                "notify_mutations": config.notify_mutations,
                "report_interval": config.report_interval,
                "circuit_breaker_enabled": config.circuit_breaker_enabled,
                "ai_lock_level": config.ai_lock_level,
                "use_golden_ratchet": config.use_golden_ratchet,
                "dca_enabled": config.dca_enabled,
            },
            "ia_state": _get_ia_state(),
            "strategies": {
                "mitraillette": asdict(MITRAILLETTE),
                "sniper": asdict(SNIPER),
            },
            "ranges": {
                "mitraillette": MITRAILLETTE_RANGES,
                "sniper": SNIPER_RANGES,
            },
        }

    # ... Existing Online Logic ...
    trader = _trader_instance

    # SOTA v5.4: Explicit Refresh Trigger (Fire & Forget)
    if refresh:
        trader._trigger_ui_refresh()
        logger.info("📊 UI refresh")

    cached = getattr(trader, "_cached_report", {})

    # HOT FIX: If instance cache is empty/booting, try to load disk cache (Hot Start)
    if not cached or cached.get("sync_status") == "BOOTING":
        try:
            cache_path = MEMORIES_DIR / "trader" / "trader_cache.json"
            disk_cache = load_json(cache_path)
            if disk_cache:
                # Merge/Replace
                cached = disk_cache
                cached["sync_status"] = "CACHED"
                # Update instance to avoid re-reading disk
                trader._cached_report = cached
        except Exception:
            pass

    if not cached:
        # Initializing state (Online but no report yet)
        # Fallback to reconstructed report
        boot_report = persisted_report.copy()
        boot_report.update(
            {
                "regime": "BOOTING",
                "mode": "⏳ INIT",
                "submode": config.mode.upper(),
                "cycle": trader.cycle_count,  # Use live memory if available
            }
        )
        return {
            "status": "online",
            "message": "Initializing...",
            "report": boot_report,
            "config": asdict(config),  # Use loaded config
            "ia_state": _get_ia_state(),
            "strategies": {
                "mitraillette": asdict(MITRAILLETTE),
                "sniper": asdict(SNIPER),
            },
            "ranges": {
                "mitraillette": MITRAILLETTE_RANGES,
                "sniper": SNIPER_RANGES,
            },
        }

    # Full Online Report
    return {
        "status": "online",
        "report": {
            # Market State
            "regime": cached.get("regime", "RANGE"),
            "btc_24h": cached.get("btc_24h", 0),
            "sentiment": cached.get("sentiment", 50),
            # Strategy
            "mode": cached.get("mode", "🤖 IA" if config.ai_enabled else "👤 MANUEL"),
            "submode": cached.get("submode", config.mode.upper()),
            "cycle": cached.get("cycle_count", trader.cycle_count),
            # Portfolio
            "total_capital": cached.get("total_capital", 0),
            "capital_actif": cached.get("capital_actif", 0),
            "cash": cached.get("cash", 0),
            "positions_value": cached.get("positions_value", 0),
            "positions": cached.get("positions", {}),
            # Sacred Reserve (BTC)
            "btc_total": cached.get("btc_total", 0),
            "btc_earn": cached.get("btc_earn", 0),
            "btc_value": cached.get("btc_value", 0),
            "cagnotte": cached.get("cagnotte", 0),
            # Combat History
            "wins": cached.get("wins", 0),
            "losses": cached.get("losses", 0),
            "win_rate": cached.get("win_rate_session", 0),
            "pnl_daily": cached.get("pnl_daily", 0),
            "pnl_global": cached.get("pnl_session", 0),
            "trades_history": cached.get("trades_history", []),
            # Status
            # Status
            "circuit_breaker": cached.get("circuit_breaker", False),
        },
        "config": {
            "mode": config.mode,
            "level": config.level,
            "ai_enabled": config.ai_enabled,
            "earn": config.earn,
            "paused": config.paused,
            "panopticon_enabled": config.panopticon_enabled,
            "whales_enabled": config.whales_enabled,
            "notify_buys": config.notify_buys,
            "notify_sells": config.notify_sells,
            "notify_reports": config.notify_reports,
            "notify_mutations": config.notify_mutations,
            "report_interval": config.report_interval,
            "circuit_breaker_enabled": config.circuit_breaker_enabled,
            "ai_lock_level": config.ai_lock_level,
            "use_golden_ratchet": config.use_golden_ratchet,
            "dca_enabled": config.dca_enabled,
        },
        "ia_state": _get_ia_state(),
        "strategies": {
            "mitraillette": asdict(MITRAILLETTE),
            "sniper": asdict(SNIPER),
        },
        "ranges": {
            "mitraillette": MITRAILLETTE_RANGES,
            "sniper": SNIPER_RANGES,
        },
    }


@router.post("/config")
async def update_trader_config(update: TraderConfigUpdate):
    """Update trader configuration (Offline & Online)."""
    try:
        config = TraderConfig.load()

        if update.mode is not None:
            config.mode = update.mode
        if update.level is not None:
            config.level = update.level
        if update.ai_enabled is not None:
            config.ai_enabled = update.ai_enabled
        if update.paused is not None:
            config.paused = update.paused
        if update.panopticon_enabled is not None:
            config.panopticon_enabled = update.panopticon_enabled
        if update.earn is not None:
            config.earn = update.earn
        if update.whales_enabled is not None:
            config.whales_enabled = update.whales_enabled
        if update.ai_buy_validation is not None:
            config.ai_buy_validation = update.ai_buy_validation

        # SOTA v5.9: Options manquantes corrigées
        if update.ghost_mode_enabled is not None:
            config.ghost_mode_enabled = update.ghost_mode_enabled
        if update.quantum_enabled is not None:
            config.quantum_enabled = update.quantum_enabled
        if update.golden_memory_autoexec is not None:
            config.golden_memory_autoexec = update.golden_memory_autoexec

        # Advanced
        if update.notify_buys is not None:
            config.notify_buys = update.notify_buys
        if update.notify_sells is not None:
            config.notify_sells = update.notify_sells
        if update.notify_reports is not None:
            config.notify_reports = update.notify_reports
        if update.notify_mutations is not None:
            config.notify_mutations = update.notify_mutations
        if update.report_interval is not None:
            config.report_interval = update.report_interval
        if update.circuit_breaker_enabled is not None:
            config.circuit_breaker_enabled = update.circuit_breaker_enabled
        if update.ai_lock_level is not None:
            config.ai_lock_level = update.ai_lock_level
        if update.use_golden_ratchet is not None:
            config.use_golden_ratchet = update.use_golden_ratchet
        if update.dca_enabled is not None:
            config.dca_enabled = update.dca_enabled
        if update.manual_strategy is not None:
            config.manual_strategy = update.manual_strategy

        config.save()
        logger.info(
            f"📊 [TRADER API] Config updated: mode={config.mode} level={config.level}"
        )

        # Hot reload if running
        if _trader_instance:
            _trader_instance.reload_config(config)

        return {
            "status": "ok",
            "config": {
                "mode": config.mode,
                "level": config.level,
                "ai_enabled": config.ai_enabled,
                "earn": config.earn,
                "paused": config.paused,
                "panopticon_enabled": config.panopticon_enabled,
                "whales_enabled": config.whales_enabled,
                "ai_buy_validation": config.ai_buy_validation,
                "ghost_mode_enabled": config.ghost_mode_enabled,
                "quantum_enabled": config.quantum_enabled,
                "golden_memory_autoexec": config.golden_memory_autoexec,
                "notify_buys": config.notify_buys,
                "notify_sells": config.notify_sells,
                "notify_reports": config.notify_reports,
                "notify_mutations": config.notify_mutations,
                "report_interval": config.report_interval,
                "circuit_breaker_enabled": config.circuit_breaker_enabled,
                "ai_lock_level": config.ai_lock_level,
                "use_golden_ratchet": config.use_golden_ratchet,
                "dca_enabled": config.dca_enabled,
                "manual_strategy": config.manual_strategy or {},
            },
        }
    except Exception as e:
        logger.error(f"💥 [TRADER API] Config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
