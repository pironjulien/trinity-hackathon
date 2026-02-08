"""
JOBS/TRADER/CONFIG.PY
==============================================================================
MODULE: TRADER CONFIGURATION (Single Source of Truth)
PURPOSE: All trading constants, strategy parameters, and runtime configuration.
SOTA: PHI-based intervals, no hardcoded values outside this file.
==============================================================================
"""

from typing import Final, List, Dict, Literal, Optional
from dataclasses import dataclass
from pathlib import Path
import json

# ==============================================================================
# PHI CONSTANTS (Import from corpus for consistency)
# ==============================================================================
from corpus.dna.conscience import (
    PHI,
    INV_PHI,
    INV_PHI_SQUARED,
    F5,
    F8,
    F13,
    F21,
    F34,
    F55,
    F89,
    F144,
    F233,
    F377,
    F2584,
    F4181,
)
from dataclasses import asdict

F18 = F2584  # 18th Fibonacci number
from corpus.dna.genome import JOBS_DIR, MEMORIES_DIR  # noqa: E402

# ==============================================================================
# FILE PATHS
# ==============================================================================
TRADER_DIR: Final[Path] = JOBS_DIR / "trader"
TRADER_JSON: Final[Path] = MEMORIES_DIR / "trader" / "trader.json"
STATE_FILE: Final[Path] = MEMORIES_DIR / "trader" / "state.json"
POSITIONS_FILE: Final[Path] = MEMORIES_DIR / "trader" / "positions.json"
MARKET_DB_FILE: Final[str] = str(MEMORIES_DIR / "trader" / "market.db")
PORTFOLIO_FILE: Final[Path] = MEMORIES_DIR / "trader" / "portfolio.json"


# ==============================================================================
# SAFETY (Environment-based)
# ==============================================================================
import os  # noqa: E402

TRADER_DRY_RUN: Final[bool] = os.getenv("TRADER_DRY_RUN", "False").lower() in (
    "true",
    "1",
)

# ==============================================================================
# BTC RULES (INVIOLABLE - SACRED)
# ==============================================================================
FORBIDDEN_SELL_ASSETS: Final[tuple] = ("BTC",)
BTC_SACRED_PAIR: Final[str] = "BTC/EUR"
CAGNOTTE_BTC_THRESHOLD: Final[float] = 4.236  # Phi^3 (Sacred Threshold)
CAGNOTTE_BTC_RATIO: Final[float] = 0.236  # 1/Phi^3 (~23.6%) of profit → Piggy bank
BTC_HEDGE_THRESHOLD: Final[float] = -0.0382  # -3.82% → Reduce exposure
BTC_STOP_TRADING: Final[float] = -0.0618  # -6.18% → Full stop
BTC_WEAKNESS_THRESHOLD: Final[float] = -0.0236  # -2.36% → Caution mode

# ==============================================================================
# GLOBAL CONSTANTS (Mode independent)
# ==============================================================================
SCAN_TOP_X: Final[int] = F377  # Scan 377 top pairs (Fibonacci)
DEEP_HISTORY: Final[int] = 46368  # F24 (~1 year) candles for analysis
CYCLE_INTERVAL: Final[int] = F34  # 34s per cycle (Heartbeat)
NOISE_THRESHOLD: Final[float] = 0.0013  # 0.13% (Ignored price noise)
ESTIMATED_FEES: Final[float] = 0.0026  # 0.26% Taker Fee (Kraken)

# ==============================================================================
# TAKE PROFIT STEPS (Golden Ratio Sequence)
# ==============================================================================
# LEGACY: Fixed steps (kept for backward compatibility)
GOLDEN_STEPS: Final[List[float]] = [
    0.013,  # F13 (1.3%)
    0.01618,  # Golden (1.618%)
    0.02618,  # Phi² (2.618%)
    0.04236,  # Phi³ (4.236%)
    0.06854,  # Phi⁴ (6.854%)
    0.11090,  # Phi⁵ (Moonshot)
]

# SOTA v5.8: Dynamic Phi-progression for infinite trailing (Golden Ratchet Infinity)
# Formula: Step(n) = BASE_STEP × Φ^n
# Level 0: 1.0%, Level 1: 1.618%, Level 2: 2.618%, Level 3: 4.236%...
GOLDEN_RATCHET_BASE: Final[float] = 0.01  # 1% base step


def get_golden_step(level: int) -> float:
    """
    Calculate dynamic take-profit step using Phi progression.

    Args:
        level: Ratchet level (0, 1, 2, ...)

    Returns:
        Step percentage (e.g., 0.01618 for level 1 = 1.618%)

    Formula: Step(n) = 0.01 × Φ^n
    - Level 0:  1.00%
    - Level 1:  1.618%
    - Level 2:  2.618%
    - Level 3:  4.236%
    - Level 4:  6.854%
    - Level 5:  11.09%
    - Level 6:  17.94%
    - Level 7:  29.03%
    - Level 8:  46.97%
    - Level 9:  75.99%
    - Level 10: 122.9% (x2.2 initial!)
    """
    return GOLDEN_RATCHET_BASE * (PHI**level)


# ==============================================================================
# CIRCUIT BREAKER
# ==============================================================================
DAILY_LOSS_LIMIT: Final[float] = -0.089  # -8.9% Daily → Emergency stop

# ==============================================================================
# PORTFOLIO MANAGEMENT
# ==============================================================================
MAX_SPREAD_DEFAULT: Final[float] = 0.013  # F13 (1.3%) max spread
SPREAD_EXCEPTIONS: Final[Dict[str, float]] = {
    "PTB/EUR": 0.055,  # 5.5% exception (volatile)
}
# Pairs without OHLCV data on Kraken (WebSocket sends tickers but REST has no candles)
OHLCV_EXCLUDED_PAIRS: Final[tuple] = (
    "AIBTC/EUR",  # AI Token - no candle data available
)
NO_OHLCV_BLACKLIST_DURATION: Final[int] = 604800  # 1 week in seconds
STAGNANT_PNL_THRESHOLD: Final[float] = 0.013  # 1.3% stagnant threshold
STAGNANT_AGE_MINUTES: Final[int] = F4181  # 4181 min (~3 days) -> Force sell
TURBO_AGE_MINUTES: Final[int] = F5  # 5 min scalping window
TURBO_PNL_THRESHOLD: Final[float] = 0.034  # 3.4% in 5 min → Take profit
SELL_COOLDOWN: Final[int] = F377  # 377s (~6 min) cooldown
DUST_THRESHOLD_EUR: Final[float] = 0.236  # 1/Phi³ dust threshold
DUST_EJECTION_BUFFER: Final[float] = 0.10  # 10% margin → Panic sell

# ==============================================================================
# PUMP/WHALE DETECTION
# ==============================================================================
PUMP_THRESHOLD: Final[float] = F55  # 55% confidence for pump
SNIPER_THRESHOLD: Final[float] = F55  # 55% confidence for sniper
PUMP_VOLUME_RATIO: Final[float] = 2.618  # Phi² volume explosion

# ==============================================================================
# REGIME MULTIPLIERS (Market conditions)
# ==============================================================================
REGIME_MULTIPLIERS: Final[Dict[str, float]] = {
    "BULL": PHI,  # +61.8% stake
    "BEAR": INV_PHI_SQUARED,  # -62% stake
    "RANGE": 1.0,  # Normal
    "CRASH": 0.0618,  # Survival mode
}


# ==============================================================================
# STRATEGY: MITRAILLETTE (Fast scalping)
# ==============================================================================
@dataclass(frozen=True)
class MitrailletteConfig:
    """Fast scalping strategy - many small trades."""

    rsi_oversold: float = 34
    rsi_overbought: float = 61.8
    rsi_period: int = F21
    stop_loss: float = -0.01618  # -1.618%
    tp1: float = 0.013  # +1.3%
    tp2: float = 0.01618  # +1.618%
    min_confidence: float = 61.8
    max_positions: int = F34  # 34 max
    trend_ema: int = F89  # 89 EMA
    min_trade: float = 2.618  # 2.618€ min
    max_trade: float = F13  # 13€ max
    rsi_composite_limit: float = 42.36  # Phi^3 * 10


MITRAILLETTE = MitrailletteConfig()

# Ranges for optimizer (LOW, DEFAULT, HIGH)
# Ranges for optimizer (LOW=Passive, DEFAULT=Normal, HIGH=Aggressive)
# LOGIC: Aggressive = High Volume = Lower Confidence Threshold + Higher RSI Threshold
# SOTA v5.8: Phi-Harmonized Ranges (All values derived from Φ or Fibonacci)
MITRAILLETTE_RANGES: Final[Dict[str, List]] = {
    # RSI: Fibonacci sequence (F13=13, F21=21, F34=34, Phi³*10=42.36)
    "rsi_oversold": [F21, F34, 42.36],  # Passive=21, Normal=34, Aggressive=42.36
    "rsi_overbought": [F55, 61.8, 76.4],  # Phi ratios (55, 61.8%, 76.4%)
    "rsi_period": [F13, F21, F13],  # Fast reaction for Aggro
    # Risk/Reward: Pure Phi progression (Φ, Φ², Φ³)
    "stop_loss": [-0.01, -0.01618, -0.02618],
    "tp1": [0.00618, 0.01, 0.01618],  # 0.618%, 1%, 1.618%
    "tp2": [0.01, 0.01618, 0.02618],  # 1%, 1.618%, 2.618%
    # Confidence: Inverted Phi (High level = Low threshold for volume)
    "min_confidence": [76.4, 61.8, 55.0],  # 76.4%, 61.8%, 55 (F10)
    # Positions: Fibonacci sequence
    "max_positions": [F21, F34, F55],  # 21, 34, 55
    "trend_ema": [F144, F89, F55],  # Fibonacci EMAs
    # Trade sizes: Phi progression
    "min_trade": [1.618, 2.618, 4.236],  # Φ, Φ², Φ³
    "max_trade": [F8, F13, F21],  # Fibonacci
    "rsi_composite_limit": [F34, 42.36, 50.0],  # 34, Φ³*10, 50
}


# ==============================================================================
# STRATEGY: SNIPER (Precision, few big trades)
# ==============================================================================
@dataclass(frozen=True)
class SniperConfig:
    """Precision strategy - few high-confidence trades."""

    rsi_oversold: float = F13
    rsi_overbought: float = 76.4
    rsi_period: int = F34
    stop_loss: float = -0.02618  # -2.618%
    tp1: float = 0.02618  # +2.618%
    tp2: float = 0.04236  # +4.236%
    min_confidence: float = 85
    max_positions: int = F13  # 13 max
    trend_ema: int = F144  # 144 EMA
    min_trade: float = F8  # 8€ min
    max_trade: float = F21  # 21€ max


SNIPER = SniperConfig()

# SOTA v5.8: Phi-Harmonized Ranges (Precision mode - tighter thresholds)
SNIPER_RANGES: Final[Dict[str, List]] = {
    # RSI: Very tight Fibonacci (extreme precision)
    "rsi_oversold": [F8, F13, 23.6],  # 8, 13, 23.6 (Φ²*10)
    "rsi_overbought": [61.8, 76.4, 85.4],  # Phi ratios (61.8%, 76.4%, 100-14.6≈85.4)
    "rsi_period": [F34, F34, F21],  # Stable periods
    # Risk/Reward: Higher Phi progression (bigger swings)
    "stop_loss": [-0.01618, -0.02618, -0.04236],  # Φ%, Φ²%, Φ³%
    "tp1": [0.01618, 0.02618, 0.04236],  # 1.618%, 2.618%, 4.236%
    "tp2": [0.02618, 0.04236, 0.06854],  # 2.618%, 4.236%, 6.854%
    # Confidence: High bar (Phi-derived from 100-x)
    "min_confidence": [88.6, 85.4, 76.4],  # 100-11.4, 100-14.6, 100-23.6
    # Positions: Small Fibonacci (precision = few trades)
    "max_positions": [F5, F8, F13],  # 5, 8, 13
    "trend_ema": [F233, F144, F89],  # Long Fibonacci EMAs
    # Trade sizes: Higher Phi progression
    "min_trade": [4.236, F8, F13],  # Φ³, 8, 13
    "max_trade": [F13, F21, F34],  # Fibonacci
}

# ==============================================================================
# RUNTIME CONFIGURATION (from trader.json)
# ==============================================================================
TradingMode = Literal["mitraillette", "sniper", "ia", "manual"]


@dataclass
class TraderConfig:
    """
    Runtime configuration loaded from trader.json.

    Modes:
    - mitraillette: Fast scalping, many small trades
    - sniper: Precision, few high-confidence trades
    - ia: AI dynamically chooses strategy per trade
    - manual: Full user control

    Levels:
    - 0: PASSIVE (conservative parameters)
    - 1: NORMAL (default parameters)
    - 2: AGGRESSIVE (high-risk parameters)
    """

    mode: TradingMode = "mitraillette"
    level: int = 1  # 0=PASSIVE, 1=NORMAL, 2=AGGRESSIVE
    ai_enabled: bool = True
    earn: bool = True
    paused: bool = False
    panopticon_enabled: bool = True
    whales_enabled: bool = True
    quantum_enabled: bool = True  # ⚛️ SOTA: Global Coherence Detection
    ghost_mode_enabled: bool = True  # 👻 Ghost Mode: Hide stops from exchange
    ai_buy_validation: bool = True  # Strict AI check before buy

    # Notifications
    notify_buys: bool = True
    notify_sells: bool = True
    notify_reports: bool = True
    notify_mutations: bool = True
    notify_circuit_breaker: bool = True  # Alert when trading halted

    # Timing
    report_interval: int = 89  # Minutes (Default F89)

    # Safety & AI
    circuit_breaker_enabled: bool = True
    ai_lock_level: bool = (
        False  # Lock level to prevent optimizer from changing it (user manual control)
    )
    use_golden_ratchet: bool = True  # SOTA v5.8: True = trailing stop, False = fixed TP
    golden_memory_autoexec: bool = (
        False  # SOTA 2026: Auto-execute on 89%+ pattern match
    )
    dca_enabled: bool = False  # DCA (Dollar Cost Averaging) - disabled by user mandate
    manual_strategy: Optional[Dict[str, float | int]] = (
        None  # User overrides for Manual Mode
    )

    @classmethod
    def load(cls) -> "TraderConfig":
        """Load configuration from trader.json."""
        try:
            if TRADER_JSON.exists():
                with open(TRADER_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(
                    mode=data.get("mode", "mitraillette"),
                    level=data.get("level", 1),
                    ai_enabled=data.get("ai_enabled", True),
                    earn=data.get("earn", True),
                    paused=data.get("paused", False),
                    panopticon_enabled=data.get("panopticon_enabled", False),
                    whales_enabled=data.get("whales_enabled", True),
                    quantum_enabled=data.get("quantum_enabled", True),
                    ghost_mode_enabled=data.get("ghost_mode_enabled", True),
                    ai_buy_validation=data.get("ai_buy_validation", True),
                    notify_buys=data.get("notify_buys", True),
                    notify_sells=data.get("notify_sells", True),
                    notify_reports=data.get("notify_reports", True),
                    notify_mutations=data.get("notify_mutations", True),
                    notify_circuit_breaker=data.get("notify_circuit_breaker", True),
                    report_interval=data.get("report_interval", 89),
                    circuit_breaker_enabled=data.get("circuit_breaker_enabled", True),
                    ai_lock_level=data.get("ai_lock_level", False),
                    use_golden_ratchet=data.get("use_golden_ratchet", True),
                    golden_memory_autoexec=data.get("golden_memory_autoexec", False),
                    dca_enabled=data.get("dca_enabled", False),
                    manual_strategy=data.get("manual_strategy", {}),
                )
        except Exception:
            pass
        return cls()

    def save(self) -> None:
        """Persist configuration to trader.json."""
        TRADER_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(TRADER_JSON, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "mode": self.mode,
                    "level": self.level,
                    "ai_enabled": self.ai_enabled,
                    "earn": self.earn,
                    "paused": self.paused,
                    "panopticon_enabled": self.panopticon_enabled,
                    "whales_enabled": self.whales_enabled,
                    "quantum_enabled": self.quantum_enabled,
                    "ghost_mode_enabled": self.ghost_mode_enabled,
                    "ai_buy_validation": self.ai_buy_validation,
                    "notify_buys": self.notify_buys,
                    "notify_sells": self.notify_sells,
                    "notify_reports": self.notify_reports,
                    "notify_mutations": self.notify_mutations,
                    "notify_circuit_breaker": self.notify_circuit_breaker,
                    "report_interval": self.report_interval,
                    "circuit_breaker_enabled": self.circuit_breaker_enabled,
                    "ai_lock_level": self.ai_lock_level,
                    "use_golden_ratchet": self.use_golden_ratchet,
                    "golden_memory_autoexec": self.golden_memory_autoexec,
                    "dca_enabled": self.dca_enabled,
                    "manual_strategy": self.manual_strategy or {},
                },
                f,
                indent=4,
            )

    def get_strategy(self) -> MitrailletteConfig | SniperConfig:
        """
        Get strategy config based on current mode AND level.

        SOTA v5.9: Returns dynamic instance with level-specific parameters
        from RANGES instead of frozen defaults.

        For mode='ia', reads active_config.json for both active_mode AND
        active_variation (level).
        """

        def _build_strategy(
            base_class, ranges: dict, level_idx: int
        ) -> MitrailletteConfig | SniperConfig:
            """Build strategy instance with level-specific params from RANGES."""
            # Get defaults from frozen instance
            if base_class == SniperConfig:
                defaults = asdict(SNIPER)
            else:
                defaults = asdict(MITRAILLETTE)

            # Override with level-specific values from RANGES
            params = {}
            for key, default_val in defaults.items():
                if key in ranges and len(ranges[key]) >= 3:
                    params[key] = ranges[key][level_idx]
                else:
                    params[key] = default_val

            return base_class(**params)

        # Determine mode and level
        mode = self.mode
        level_idx = max(0, min(2, self.level))  # Clamp to 0-2

        # SOTA v5.9: IA mode reads both active_mode AND active_variation
        if mode == "ia":
            try:
                config_path = MEMORIES_DIR / "trader" / "active_config.json"
                if config_path.exists():
                    with open(config_path, "r") as f:
                        active_conf = json.load(f)
                    mode = active_conf.get("active_mode", "mitraillette")
                    variation = active_conf.get("active_variation", "DEFAULT")
                    level_idx = {"LOW": 0, "DEFAULT": 1, "HIGH": 2}.get(variation, 1)
            except Exception:
                mode = "mitraillette"  # Fallback
                level_idx = 1

        # Build dynamic strategy based on mode
        if mode == "sniper":
            return _build_strategy(SniperConfig, SNIPER_RANGES, level_idx)

        if mode == "manual":
            # Start with SNIPER defaults (safest)
            base = asdict(SNIPER)
            # Override with manual params
            if self.manual_strategy:
                base.update(self.manual_strategy)
            return SniperConfig(**base)

        # Default: mitraillette
        return _build_strategy(MitrailletteConfig, MITRAILLETTE_RANGES, level_idx)

    def get_strategy_dict(self) -> Dict:
        """Get strategy as dict (for backward compat)."""
        strategy = self.get_strategy()
        return {
            "rsi_oversold": strategy.rsi_oversold,
            "rsi_overbought": strategy.rsi_overbought,
            "rsi_period": strategy.rsi_period,
            "stop_loss": strategy.stop_loss,
            "tp1": strategy.tp1,
            "tp2": strategy.tp2,
            "min_confidence": strategy.min_confidence,
            "max_positions": strategy.max_positions,
            "trend_ema": strategy.trend_ema,
            "min_trade": strategy.min_trade,
            "max_trade": strategy.max_trade,
        }


# ==============================================================================
# EXPORTS
# ==============================================================================
__all__ = [
    # PHI Constants
    "PHI",
    "INV_PHI",
    "INV_PHI_SQUARED",
    "F5",
    "F8",
    "F13",
    "F21",
    "F34",
    "F55",
    "F89",
    "F144",
    "F233",
    "F377",
    "F18",
    # Paths
    "TRADER_DIR",
    "TRADER_JSON",
    "STATE_FILE",
    "POSITIONS_FILE",
    "MEMORIES_DIR",
    "JOBS_DIR",
    # BTC Rules
    "FORBIDDEN_SELL_ASSETS",
    "BTC_SACRED_PAIR",
    "CAGNOTTE_BTC_THRESHOLD",
    "CAGNOTTE_BTC_RATIO",
    "BTC_HEDGE_THRESHOLD",
    "BTC_STOP_TRADING",
    "BTC_WEAKNESS_THRESHOLD",
    # Global
    "SCAN_TOP_X",
    "DEEP_HISTORY",
    "CYCLE_INTERVAL",
    "NOISE_THRESHOLD",
    "ESTIMATED_FEES",
    # Take Profit
    "GOLDEN_STEPS",
    "GOLDEN_RATCHET_BASE",
    "get_golden_step",
    # Circuit Breaker
    "DAILY_LOSS_LIMIT",
    # Portfolio
    "MAX_SPREAD_DEFAULT",
    "SPREAD_EXCEPTIONS",
    "STAGNANT_PNL_THRESHOLD",
    "STAGNANT_AGE_MINUTES",
    "TURBO_AGE_MINUTES",
    "TURBO_PNL_THRESHOLD",
    "SELL_COOLDOWN",
    "DUST_THRESHOLD_EUR",
    "DUST_EJECTION_BUFFER",
    # Pump/Whale
    "PUMP_THRESHOLD",
    "SNIPER_THRESHOLD",
    "PUMP_VOLUME_RATIO",
    # Regime
    "REGIME_MULTIPLIERS",
    # Strategies
    "MITRAILLETTE",
    "MitrailletteConfig",
    "MITRAILLETTE_RANGES",
    "SNIPER",
    "SniperConfig",
    "SNIPER_RANGES",
    # Runtime Config
    "TraderConfig",
    "TradingMode",
]
