"""
JOBS/TRADER/STRATEGY/BRAIN.PY
==============================================================================
MODULE: TRADING BRAIN (Hybrid Decision Engine) 🧠
PURPOSE: Complete pipeline: Math Indicators → Signal Detection → Validation → AI Consultation
LOI: Respect Strict du Nombre d'Or (Phi = 1.618).
==============================================================================
"""

import time
import asyncio
import polars as pl
from typing import Dict, Optional, Tuple, Any
from functools import cached_property
from corpus.soma.nerves import logger  # SOTA: Use central nerves config (DEBUG level)

from jobs.trader.config import (
    TraderConfig,
    MITRAILLETTE,
    SNIPER,
    MITRAILLETTE_RANGES,
    SNIPER_RANGES,
    GOLDEN_STEPS,
    DAILY_LOSS_LIMIT,
    BTC_HEDGE_THRESHOLD,
    BTC_STOP_TRADING,
    REGIME_MULTIPLIERS,
    PHI,
    F5,
    F8,
    F13,
    F21,
    F55,
    F18,
    ESTIMATED_FEES,
    MEMORIES_DIR,
)

# Safe import for load_json (graceful degradation)
try:
    from corpus.soma.cells import load_json
except ImportError:
    import json

    def load_json(path, default=None):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return default


from jobs.trader.strategy.signals import Signal
from jobs.trader.data.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_bollinger,
    calculate_atr,
    calculate_ema,
    calculate_fibonacci_zones,
    calculate_volume_ratio,
    detect_divergence,
)

# Intelligence sub-modules (lazy imports in __init__ for graceful degradation)


class BrainContext:
    """
    SOTA v5.0: Lazy Evaluation Context.
    Calculates indicators only when accessed, saving CPU cycles.
    Acts as a read-only Dictionary/Object.
    """

    def __init__(
        self, df: pl.DataFrame, strategy: Any, brain: "TradingBrain", pair: str
    ):
        self.df = df
        self.strategy = strategy
        self.brain = brain
        self.pair = pair

        # Base Data (Eager)
        closes = df["close"].to_list() if not df.is_empty() else []
        if closes:
            self.current_price = closes[-2] if len(closes) > 1 else closes[-1]
            prev = (
                closes[-3]
                if len(closes) > 2
                else (closes[-2] if len(closes) > 1 else self.current_price)
            )
            self.price_change = (self.current_price - prev) / prev if prev else 0
        else:
            self.current_price = 0.0
            self.price_change = 0.0
        self.candle_count = df.height

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        # Simplified check
        return hasattr(self, key)

    @cached_property
    def price(self) -> float:
        return float(self.current_price)

    @cached_property
    def rsi_series(self):
        return calculate_rsi(self.df, period=self.strategy.rsi_period)

    @cached_property
    def rsi(self) -> float:
        s = self.rsi_series
        vals = s.to_list() if s.len() > 0 else [50]
        return vals[-1] if vals else 50.0

    @cached_property
    def rsi_prev(self) -> float:
        s = self.rsi_series
        vals = s.to_list()
        return vals[-2] if len(vals) > 1 else self.rsi

    @cached_property
    def rsi_rising(self) -> bool:
        return self.rsi > self.rsi_prev

    @cached_property
    def bb_tuple(self):
        return calculate_bollinger(self.df)

    @cached_property
    def bb_upper(self) -> float:
        u = self.bb_tuple[0]
        return u.to_list()[-1] if u.len() > 0 else self.current_price * 1.02

    @cached_property
    def bb_lower(self) -> float:
        lower = self.bb_tuple[2]
        return lower.to_list()[-1] if lower.len() > 0 else self.current_price * 0.98

    @cached_property
    def bb_middle(self) -> float:
        m = self.bb_tuple[1]
        return m.to_list()[-1] if m.len() > 0 else self.current_price

    @cached_property
    def bb_position(self) -> float:
        width = self.bb_upper - self.bb_lower
        return (self.current_price - self.bb_lower) / width if width > 0 else 0.5

    @cached_property
    def macd_tuple(self):
        return calculate_macd(self.df)

    @cached_property
    def macd(self) -> float:
        h = self.macd_tuple[2]  # Histogram
        vals = h.to_list() if h.len() > 0 else [0]
        return vals[-1] if vals else 0.0

    @cached_property
    def macd_prev(self) -> float:
        h = self.macd_tuple[2]
        vals = h.to_list()
        return vals[-2] if len(vals) > 1 else self.macd

    @cached_property
    def macd_strong(self) -> bool:
        return (self.macd > self.macd_prev) and (self.macd > 0)

    @cached_property
    def macd_crossover(self) -> bool:
        # Simplification: Current > 0 and Prev <= 0
        return self.macd > 0 and self.macd_prev <= 0

    @cached_property
    def is_uptrend(self) -> bool:
        ema = calculate_ema(self.df, period=self.strategy.trend_ema)
        val = ema.to_list()[-1] if ema.len() > 0 else self.current_price
        return self.current_price > val

    @cached_property
    def fib_tuple(self):
        return calculate_fibonacci_zones(self.df, lookback=F55)

    @cached_property
    def in_fib_zone(self) -> bool:
        return self.fib_tuple[2]

    @cached_property
    def volume_spike(self) -> bool:
        vr = calculate_volume_ratio(self.df, lookback=20)
        return vr > 2.618

    @cached_property
    def whale_activity(self) -> bool:
        # Check config flag first
        if not getattr(self.brain.config, "whales_enabled", True):
            return False
        if not self.brain.whale_tracker:
            return False
        try:
            # This is slower, so cached_property is perfect
            activities = self.brain.whale_tracker.detect(self.df)
            return len(activities) > 0
        except Exception:
            return False

    @cached_property
    def whale_sentiment(self) -> str:
        # Check config flag first
        if not getattr(self.brain.config, "whales_enabled", True):
            return "neutral"
        if not self.brain.whale_tracker:
            return "neutral"
        return self.brain.whale_tracker.get_sentiment()

    @cached_property
    def bearish_divergence(self) -> bool:
        div = detect_divergence(self.df, self.rsi_series, lookback=10)
        return div == "bearish"

    @cached_property
    def bullish_divergence(self) -> bool:
        div = detect_divergence(self.df, self.rsi_series, lookback=10)
        return div == "bullish"

    @cached_property
    def noise(self) -> float:
        # Approximate noise calculation or reuse price_change logic if strictness Needed
        return abs(self.price_change)

    @cached_property
    def rsi_oversold(self) -> bool:
        return self.rsi < self.strategy.rsi_oversold

    @cached_property
    def rsi_overbought(self) -> bool:
        return self.rsi > self.strategy.rsi_overbought

    @cached_property
    def rsi_buy_threshold(self) -> float:
        return self.strategy.rsi_oversold

    @cached_property
    def rsi_sell_threshold(self) -> float:
        return self.strategy.rsi_overbought

    @cached_property
    def bb_oversold(self) -> bool:
        return self.bb_position < 0.2

    @cached_property
    def bb_overbought(self) -> bool:
        return self.bb_position > 0.8

    @cached_property
    def atr_tuple(self):
        return calculate_atr(self.df)

    @cached_property
    def atr(self) -> float:
        a = self.atr_tuple[0]
        return a.to_list()[-1] if a.len() > 0 else 0.0

    @cached_property
    def atr_pct(self) -> float:
        p = self.atr_tuple[1]
        return p.to_list()[-1] if p.len() > 0 else 0.0

    @cached_property
    def fib_382(self) -> float:
        return self.fib_tuple[0]

    @cached_property
    def fib_618(self) -> float:
        return self.fib_tuple[1]

    @cached_property
    def btc_context(self) -> Dict:
        return self.brain.get_btc_context()

    @cached_property
    def order_flow(self) -> Dict:
        if not self.brain.order_flow:
            return {}
        try:
            return self.brain.order_flow.get_cvd_context(self.pair) or {}
        except Exception:
            return {}

    def to_dict(self, full: bool = False) -> Dict[str, Any]:
        """
        Convert context to dictionary (Snapshot).
        Args:
            full: If True, calculates ALL indicators (eagerly).
                  If False, returns only what is currently cached.
        """
        base = {
            "pair": self.pair,
            "price": self.price,
            "candle_count": self.candle_count,
            "noise": self.noise,
            "price_change": self.price_change,
        }

        keys_to_export = [
            "rsi",
            "rsi_rising",
            "rsi_oversold",
            "rsi_overbought",
            "rsi_buy_threshold",
            "rsi_sell_threshold",
            "bb_upper",
            "bb_lower",
            "bb_middle",
            "bb_position",
            "bb_oversold",
            "bb_overbought",
            "macd",
            "macd_strong",
            "macd_crossover",
            "atr",
            "atr_pct",
            "is_uptrend",
            "in_fib_zone",
            "fib_382",
            "fib_618",
            "volume_spike",
            "bearish_divergence",
            "bullish_divergence",
            "whale_activity",
            "whale_sentiment",
            "order_flow",
            "btc_context",
        ]

        data = base.copy()

        # Helper to safely get value without crashing if calc fails
        def safe_ext(k):
            try:
                return getattr(self, k)
            except Exception:
                return None

        if full:
            for k in keys_to_export:
                data[k] = safe_ext(k)
        else:
            # Check cache (lazy)
            for k in keys_to_export:
                if k in self.__dict__:
                    data[k] = self.__dict__[k]

        return data


class TradingBrain:
    """
    Cerveau Financier Unifié (Hybrid Pipeline).

    Pipeline Complet:
    1. Évaluation technique (RSI, MACD, BB, ATR...)
    2. Détection de signal (selon profil)
    3. Validation (cash, risque, limites, RSI-rising)
    4. Consultation IA (Gattaca)
    5. Signal Final

    Note: L'IA est OBLIGATOIRE dans le flux de décision.
    """

    def __init__(self, config: TraderConfig = None):
        """
        Initialize brain with configuration and intelligence modules.

        Args:
            config: Runtime configuration (optional, loads from file if not provided)
        """
        self.config = config or TraderConfig.load()
        self._rejection_log: list = []
        self._daily_pnl: float = 0.0
        self._portfolio_peak: float = 0.0

        # Config cache for dynamic pair configs (Hot Reload via mtime)
        self._config_cache: Dict = {}

        # Intelligence sub-modules (graceful degradation)
        self._init_intelligence()

    def _init_intelligence(self) -> None:
        """Initialize intelligence modules with graceful degradation."""
        # Whale Tracker (respect whales_enabled flag)
        if getattr(self.config, "whales_enabled", True):
            try:
                from jobs.trader.intelligence.whales import create_whale_tracker

                self.whale_tracker = create_whale_tracker()
            except Exception:
                logger.warning("🧠 Whale N/A")
                self.whale_tracker = None
        else:
            self.whale_tracker = None

        # Golden Memory
        try:
            from jobs.trader.intelligence.memory import create_memory

            self.memory = create_memory()
        except Exception:
            logger.warning("🧠 Memory N/A")
            self.memory = None

        # Order Flow (CVD)
        try:
            from jobs.trader.intelligence.order_flow import create_order_flow

            self.order_flow = create_order_flow()
        except Exception:
            logger.warning("🧠 CVD N/A")
            self.order_flow = None

        # Portfolio Manager
        try:
            from jobs.trader.intelligence.portfolio import create_portfolio_manager

            self.portfolio_manager = create_portfolio_manager()
        except Exception as e:
            logger.debug(f"🧠 [BRAIN] Portfolio manager unavailable: {e}")
            self.portfolio_manager = None

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT: HYBRID DECISION PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════

    async def decide(
        self,
        pair: str,
        candles: pl.DataFrame,
        cash: float = 1000.0,
        positions: Dict = None,
        btc_24h: float = 0.0,
        mode: str = None,
        candles_h4: Optional[pl.DataFrame] = None,
    ) -> Signal:
        """
        Complete hybrid decision pipeline: Math → Signal → Validate → AI → Execute.

        Args:
            pair: Trading pair (e.g., "BTC/EUR")
            candles: Polars DataFrame with OHLCV (15m)
            cash: Available cash in EUR
            positions: Current open positions dict
            btc_24h: BTC 24h change percentage (-0.05 = -5%)
            mode: Override mode ("mitraillette" or "sniper")
            candles_h4: Optional H4 DataFrame for Trend Filtering (SOTA v5.0)

        Returns:
            Signal with action, price, confidence, stop_loss, take_profit
        """
        positions = positions or {}
        mode = mode or self.config.mode

        # ─────────────────────────────────────────────────────────────────────
        # 1. TECHNICAL EVALUATION
        # ─────────────────────────────────────────────────────────────────────
        indicators = self.evaluate(pair, candles)
        if "error" in indicators:
            logger.info(f"🧠 {pair} Eval Error")
            return Signal.hold(pair, f"Évaluation échouée: {indicators['error']}")

        current_price = indicators["price"]

        # ═══════════════════════════════════════════════════════════════════
        # 📊 DEBUG: Log indicateurs techniques clés
        # ═══════════════════════════════════════════════════════════════════
        logger.info(
            f"📈 [{pair}] RSI={indicators.get('rsi', 0):.1f} (↗={indicators.get('rsi_rising', False)}) | "
            f"MACD={indicators.get('macd_strong', False)} | Uptrend={indicators.get('is_uptrend', False)}"
        )

        # 🧠 MODE IA: Resolve to actual mode from optimizer's active_config.json
        # This MUST read the file HERE, not in detect_signal (which receives resolved mode)
        override_level = None  # For SNIPER/MITRAILLETTE level from optimizer
        if mode == "ia":
            try:
                import json
                from jobs.trader.config import MEMORIES_DIR

                config_path = MEMORIES_DIR / "trader" / "active_config.json"
                if config_path.exists():
                    with open(config_path, "r") as f:
                        active_conf = json.load(f)
                    resolved_mode = active_conf.get("active_mode", "mitraillette")
                    # Extract variation (LOW/DEFAULT/HIGH) -> override_level (0/1/2)
                    variation = active_conf.get("active_variation", "DEFAULT")
                    override_level = {"LOW": 0, "DEFAULT": 1, "HIGH": 2}.get(
                        variation, 1
                    )
                    mode = resolved_mode
                else:
                    mode = "mitraillette"
                    pass  # Default: MITRAILLETTE
            except Exception:
                mode = "mitraillette"
                pass  # Fallback: MITRAILLETTE

        # ─────────────────────────────────────────────────────────────────────
        # 2. SIGNAL DETECTION
        # ─────────────────────────────────────────────────────────────────────
        # Pass resolved mode explicitly
        action, confidence, reason = self.detect_signal(
            indicators, mode, override_level
        )

        # ═══════════════════════════════════════════════════════════════════
        # 📊 DEBUG: Log signal detection result
        # ═══════════════════════════════════════════════════════════════════
        if action == "HOLD":
            logger.info(f"⏸️ [{pair}] HOLD → {reason}")
        else:
            logger.info(
                f"🎯 [{pair}] {action} Signal Détecté | Conf={confidence:.0f}% | {reason}"
            )

        if action == "HOLD":
            return Signal.hold(pair, reason, current_price, indicators)

        # ─────────────────────────────────────────────────────────────────────
        # 2a. MTF TREND FILTER (H4) - SOTA v5.0
        # ─────────────────────────────────────────────────────────────────────
        if action == "BUY" and candles_h4 is not None:
            trend_ind = self.evaluate_trend(candles_h4)
            if not trend_ind.get("is_uptrend", True) and not trend_ind.get(
                "macd_strong", False
            ):
                # Weakness on H4 -> Downgrade or Reject
                if mode == "sniper":
                    return Signal.hold(
                        pair,
                        "H4 Trend Bearish (Sniper Filter)",
                        current_price,
                        indicators,
                    )
                else:
                    # Mitraillette: Penalize confidence
                    confidence -= 15
                    reason += " | ⚠️ H4 Bearish"

        # ─────────────────────────────────────────────────────────────────────
        # 3. VALIDATION (Risk, Limits, Circuit Breakers, RSI-rising)
        # ─────────────────────────────────────────────────────────────────────
        approved, reject_reason, context = await self._validate(
            pair=pair,
            action=action,
            confidence=confidence,
            indicators=indicators,
            cash=cash,
            positions=positions,
            btc_24h=btc_24h,
            mode=mode,
            override_level=override_level,  # SOTA v5.9: Pass optimizer level
        )
        if not approved:
            self._log_rejection(pair, reject_reason, confidence)
            return Signal.hold(
                pair, f"Rejeté: {reject_reason}", current_price, indicators
            )

        # ─────────────────────────────────────────────────────────────────────
        # 4. AI CONSULTATION (Gattaca)
        # ─────────────────────────────────────────────────────────────────────
        # ─────────────────────────────────────────────────────────────────────
        # 4. AI CONSULTATION (Gattaca)
        # ─────────────────────────────────────────────────────────────────────
        # SOTA: Resolve BrainContext to Full Dict for AI
        indicators_full = (
            indicators.to_dict(full=True)
            if hasattr(indicators, "to_dict")
            else indicators
        )

        ai_ok, ai_reason = await self._consult_ai(
            pair, action, confidence, indicators_full, btc_24h, mode, candles
        )
        if not ai_ok:
            self._log_rejection(pair, f"IA: {ai_reason}", confidence)
            return Signal.hold(pair, f"IA: {ai_reason}", current_price, indicators)

        # ─────────────────────────────────────────────────────────────────────
        # 5. BUILD FINAL SIGNAL
        # ─────────────────────────────────────────────────────────────────────
        strategy = SNIPER if mode == "sniper" else MITRAILLETTE
        sl_pct = context.get("stop_loss_pct", strategy.stop_loss)
        tp1_pct = context.get("tp1", strategy.tp1)  # SOTA v5.9: Dynamic TP

        if action == "BUY":
            # SOTA: Fee-Aware Stop Loss (AI Mode)
            # We tighten the stop so that (Loss + Fees) <= Max Risk.
            # sl_pct is negative (e.g. -0.01618). Adding fees (positive) makes it closer to 0 (tighter).
            fees_buffer = 2 * ESTIMATED_FEES
            adjusted_sl_pct = sl_pct + fees_buffer
            stop_loss_price = current_price * (1 + adjusted_sl_pct)

            # SOTA v5.9: Fee-Aware Take Profit with dynamic TP from level
            take_profit_price = current_price * (1 + tp1_pct + fees_buffer)

            golden_steps = [current_price * (1 + step) for step in GOLDEN_STEPS]
        else:  # SELL
            stop_loss_price = current_price * (1 - sl_pct)
            take_profit_price = current_price * (1 - tp1_pct)
            golden_steps = []

        logger.success(f"🧠 ✅ {pair} {action} {confidence:.0f}%")

        if action == "BUY":
            return Signal.buy(
                pair=pair,
                price=current_price,
                reason=f"{reason} | {ai_reason}",
                confidence=confidence,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price,
                mode=mode,
                golden_steps=golden_steps,
                indicators=indicators_full,  # Use Full Dict
            )
        else:
            return Signal.sell(
                pair=pair,
                price=current_price,
                reason=f"{reason} | {ai_reason}",
                confidence=confidence,
                indicators=indicators,
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. TECHNICAL EVALUATION
    # ═══════════════════════════════════════════════════════════════════════════

    def evaluate(self, pair: str, df: pl.DataFrame) -> Dict[str, Any]:
        """
        Calculate all technical indicators for a pair.

        Args:
            pair: Trading pair (e.g., "BTC/EUR")
            df: OHLCV DataFrame (Polars)

        Returns:
            Dict with all indicator values, or {"error": "..."} on failure
        """
        if df.height < F21:  # Need minimum candles
            return {"error": f"Insufficient data ({df.height} < {F21})"}

        try:
            strategy = self.config.get_strategy()

            # SOTA v5.0: Return Lazy Context
            return BrainContext(df, strategy, self, pair)
        except Exception as e:
            logger.error(f"🧠 Eval Fail {pair}")
            return {"error": str(e)}

    def evaluate_trend(self, df: pl.DataFrame) -> Dict[str, Any]:
        """
        Evaluate H4 Trend context (Lightweight).
        """
        if df.height < 50:
            return {}

        # 1. EMA Trend
        strategy = self.config.get_strategy()
        ema = calculate_ema(df, period=strategy.trend_ema)
        closes = df["close"].to_list()
        current = closes[-1]
        ema_val = ema.to_list()[-1] if ema.len() > 0 else current

        # 2. MACD H4
        macd, sig, hist = calculate_macd(df)
        hist_val = hist.to_list()[-1] if hist.len() > 0 else 0

        return {"is_uptrend": current > ema_val, "macd_strong": hist_val > 0}

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. SIGNAL DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def detect_signal(
        self, indicators: Dict, mode: str = None, override_level: int = None
    ) -> Tuple[str, float, str]:
        """
        Detect trading signal based on indicators and profile.

        Args:
            indicators: Output from evaluate()
            mode: Override mode (optional)

        Returns:
            (action, confidence, reason)
        """
        if "error" in indicators:
            return "HOLD", 0.0, indicators["error"]

        mode = mode or self.config.mode
        pair = indicators.get("pair", "")

        # Mode is already resolved by decide() - no "ia" will reach here
        # SOTA v5.9: Keep override_level from optimizer (do NOT reset to None)
        # This allows AI mode to correctly apply LOW/DEFAULT/HIGH variations

        strategy = SNIPER if mode == "sniper" else MITRAILLETTE
        ranges = SNIPER_RANGES if mode == "sniper" else MITRAILLETTE_RANGES

        # SOTA v5.10: Calculate level_idx for dynamic RANGES lookup
        if override_level is not None:
            level_idx = max(0, min(2, override_level))
        else:
            level_idx = max(0, min(2, getattr(self.config, "level", 1)))

        # SOTA: Load Dynamic Config (Panel/Optimizer Values)
        # Returns: (conf, sl, exit_rsi, rsi_oversold)
        dyn_conf, dyn_sl, dyn_exit, dyn_rsi_oversold = self._load_dynamic_config(
            pair, mode, override_level=override_level
        )

        rsi = indicators.get("rsi", 50)
        price = indicators.get("price", 0)
        confidence = 0.0
        reasons = []
        action = "HOLD"

        # Use Dynamic Threshold if available, else usage strategy default
        rsi_buy_threshold = (
            dyn_rsi_oversold if dyn_rsi_oversold > 0 else strategy.rsi_oversold
        )

        # ─────────────────────────────────────────────────────────────────────
        # MODE MITRAILLETTE (Scalping)
        # ─────────────────────────────────────────────────────────────────────
        if mode == "mitraillette":
            # BUY SIGNAL
            if rsi < rsi_buy_threshold:
                action = "BUY"
                base_conf = dyn_conf  # Use Dynamic Confidence detected
                confidence = base_conf + ((rsi_buy_threshold - rsi) * PHI)
                reasons.append(f"RSI Survendu ({rsi:.1f} < {rsi_buy_threshold})")

                if price < indicators.get("bb_lower", price):
                    confidence += F8
                    reasons.append("BB Low")
                if indicators.get("is_uptrend", False):
                    confidence += F5
                    reasons.append("Uptrend")
                if indicators.get("in_fib_zone", False):
                    confidence += F5
                    reasons.append("Fib Zone")

            # SELL SIGNAL (REMOVED - STRICT SL/TP ONLY)
            # User Mandate: "Maths are for Buying. Selling is SL/TP."
            # elif rsi > strategy.rsi_overbought: ...

            # COMPOSITE TRIGGER (The "Rebound" Catch)
            # SOTA: Capture dips that don't hit 34 but show structural weakness + reversal
            # RSI < 42.36 (Phi^3 * 10) + Price < BB Lower + RSI Rising
            # SOTA v5.10: Use dynamic rsi_composite_limit from level
            dyn_rsi_composite = (
                ranges["rsi_composite_limit"][level_idx]
                if "rsi_composite_limit" in ranges
                and len(ranges["rsi_composite_limit"]) >= 3
                else getattr(strategy, "rsi_composite_limit", 42.36)
            )
            if (
                action == "HOLD"
                and rsi < dyn_rsi_composite
                and indicators.get("rsi_rising", False)
                and indicators.get("bb_position", 0.5) < 0.1
            ):
                action = "BUY"
                confidence = dyn_conf  # SOTA v5.10: Use dynamic confidence from level
                reasons.append(
                    f"Composite Rebound (RSI {rsi:.1f} < {dyn_rsi_composite:.2f} + BB Low)"
                )

            # LOGGING: Why did we reject? (Only if no signal found)
            if action == "HOLD" and rsi < 55:  # Only log interesting candidates
                f"🧠 Reject {indicators.get('pair')}: RSI={rsi:.1f}"

        # ─────────────────────────────────────────────────────────────────────
        # MODE SNIPER (Swing)
        # ─────────────────────────────────────────────────────────────────────
        elif mode == "sniper":
            # SOTA v5.8: Use dynamic threshold from Level (was hardcoded to 13)
            if rsi < rsi_buy_threshold:
                action = "BUY"
                confidence = dyn_conf  # Use dynamic confidence from Level
                reasons.append(f"SNIPER ENTRY (RSI {rsi:.1f} < {rsi_buy_threshold})")

                if indicators.get("macd_strong", False):
                    confidence += F5
                    reasons.append("MACD Strong")
                if indicators.get("macd_crossover", False):
                    confidence += F8
                    reasons.append("MACD Crossover")

            # SELL SIGNAL (REMOVED - STRICT SL/TP ONLY)
            # elif rsi > strategy.rsi_overbought: ...

        # ─────────────────────────────────────────────────────────────────────
        # MODIFIERS (Apply to detected signals)
        # ─────────────────────────────────────────────────────────────────────
        if action == "BUY":
            # Volume spike bonus
            if indicators.get("volume_spike", False):
                confidence += F8
                reasons.append("VOL SPIKE")

            # Divergence adjustments
            if indicators.get("bearish_divergence", False):
                confidence -= 10
                reasons.append("BEAR DIV ⚠️")
            if indicators.get("bullish_divergence", False):
                confidence += F5
                reasons.append("BULL DIV")

            # Whale confirmation
            if (
                indicators.get("whale_activity")
                and indicators.get("whale_sentiment") == "whale_bullish"
            ):
                confidence += F13
                reasons.append("🐋 Whale Accumulation")

            # Golden Memory boost
            if self.memory:
                try:
                    memory_boost = self.memory.recall(
                        indicators.get("pair", ""), indicators
                    )
                    if memory_boost > 0:  # type: ignore[operator]
                        confidence += min(memory_boost, 20)  # type: ignore[operator]
                        reasons.append(f"MEMORY(+{memory_boost:.0f})")
                except Exception:
                    pass

            # SOTA v5.5: ORDER FLOW (CVD) - The Pulse 💓
            if self.order_flow:
                pressure = self.order_flow.get_pressure_signal(pair)
                if pressure == "BUY":
                    confidence += F8  # +8% (Fibonacci)
                    reasons.append("⚡ CVD Bullish")
                elif pressure == "SELL":
                    confidence -= F13  # -13% (Fibonacci)
                    reasons.append("⚡ CVD Bearish")

        # Cap confidence
        confidence = min(confidence, 100.0)

        # ═══════════════════════════════════════════════════════════════════
        # Explain WHY no signal was detected (for debugging)
        # ═══════════════════════════════════════════════════════════════════
        if not reasons and action == "HOLD":
            # Build explanation for HOLD
            hold_reasons = []
            rsi_thresh = (
                rsi_buy_threshold if mode == "mitraillette" else strategy.rsi_oversold
            )
            if rsi >= rsi_thresh:
                hold_reasons.append(f"RSI={rsi:.0f}>{rsi_thresh:.0f}")
            dyn_rsi_composite = (
                ranges["rsi_composite_limit"][level_idx]
                if "rsi_composite_limit" in ranges
                and len(ranges["rsi_composite_limit"]) >= 3
                else getattr(strategy, "rsi_composite_limit", 42.36)
            )
            if rsi >= dyn_rsi_composite:
                hold_reasons.append(f">{dyn_rsi_composite:.0f}(comp)")
            if not indicators.get("rsi_rising", False):
                hold_reasons.append("RSI↘")
            if not indicators.get("is_uptrend", False):
                hold_reasons.append("↓trend")
            reason = (
                "WAIT: " + " | ".join(hold_reasons) if hold_reasons else "Neutral zone"
            )
        else:
            reason = " + ".join(reasons) if reasons else "No signal"
        return action, confidence, reason

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    async def _validate(
        self,
        pair: str,
        action: str,
        confidence: float,
        indicators: Dict,
        cash: float,
        positions: Dict,
        btc_24h: float,
        mode: str,
        override_level: Optional[int] = None,  # SOTA v5.9: Level from optimizer
    ) -> Tuple[bool, str, Dict]:
        """
        Validate signal against risk rules and constraints.

        Returns:
            (approved, reason, context)
        """
        context = {}
        strategy = SNIPER if mode == "sniper" else MITRAILLETTE
        ranges = SNIPER_RANGES if mode == "sniper" else MITRAILLETTE_RANGES

        # Load dynamic config (pair-specific overrides)
        min_conf, sl_dynamic, exit_rsi, _ = self._load_dynamic_config(
            pair, mode, override_level
        )
        context["stop_loss_pct"] = sl_dynamic
        context["exit_rsi"] = exit_rsi
        context["mode"] = mode

        # SOTA v5.9: Use override_level from optimizer, else panel config
        if override_level is not None:
            level_idx = max(0, min(2, override_level))
        else:
            level_idx = max(0, min(2, getattr(self.config, "level", 1)))

        context["level_idx"] = level_idx  # Store for debugging

        # SOTA v5.10: Load ALL dynamic parameters from RANGES based on level
        def get_level_val(param_name, default_val):
            if param_name in ranges and len(ranges[param_name]) >= 3:
                return ranges[param_name][level_idx]
            return default_val

        context["tp1"] = get_level_val("tp1", strategy.tp1)
        context["max_positions"] = get_level_val(
            "max_positions", strategy.max_positions
        )
        context["min_trade"] = get_level_val("min_trade", strategy.min_trade)
        context["min_confidence"] = (
            min_conf  # Already dynamic from _load_dynamic_config
        )
        context["rsi_composite_limit"] = get_level_val(
            "rsi_composite_limit", getattr(strategy, "rsi_composite_limit", 42.36)
        )

        # ═══════════════════════════════════════════════════════════════
        # DEBUG: Log active trading parameters
        # ═══════════════════════════════════════════════════════════════
        level_names = ["PASSIVE", "NORMAL", "AGGRESSIVE"]
        logger.info(
            f"🎚️ [BRAIN] Mode={mode.upper()} Level={level_names[level_idx]} ({level_idx})"
        )
        logger.info(
            f"📊 [BRAIN] SL={context['stop_loss_pct'] * 100:.2f}% | "
            f"TP1={context['tp1'] * 100:.2f}% | "
            f"MinConf={context['min_confidence']:.1f}%"
        )
        logger.info(
            f"⚙️ [BRAIN] MaxPos={context['max_positions']} | "
            f"MinTrade={context['min_trade']}€ | "
            f"RSI_Comp={context['rsi_composite_limit']:.1f}"
        )

        # ─────────────────────────────────────────────────────────────────────
        # Confidence check
        # ─────────────────────────────────────────────────────────────────────
        if confidence < min_conf:
            return (
                False,
                f"Confiance insuffisante ({confidence:.1f}% < {min_conf:.1f}%)",
                context,
            )

        # ─────────────────────────────────────────────────────────────────────
        # RSI Rising check (falling knife protection) - CRITICAL
        # ─────────────────────────────────────────────────────────────────────
        if action == "BUY" and not indicators.get("rsi_rising", False):
            return False, "RSI en baisse (falling knife)", context

        # ─────────────────────────────────────────────────────────────────────
        # Ownership Check (No Shorting)
        # ─────────────────────────────────────────────────────────────────────
        if action == "SELL" and pair not in positions:
            return False, "Pas de position ouverte (Spot Only)", context

        # ─────────────────────────────────────────────────────────────────────
        # Daily loss limit (circuit breaker)
        # ─────────────────────────────────────────────────────────────────────
        if self._daily_pnl <= DAILY_LOSS_LIMIT:
            return False, f"Limite perte journalière ({self._daily_pnl:.1%})", context

        # ─────────────────────────────────────────────────────────────────────
        # BTC Market Conditions
        # ─────────────────────────────────────────────────────────────────────
        if btc_24h <= BTC_STOP_TRADING:
            return False, f"BTC Crash Mode ({btc_24h:.1f}%)", context

        if btc_24h <= BTC_HEDGE_THRESHOLD and action == "BUY":
            context["hedge_mode"] = True
            logger.warning(
                f"🧠 [BRAIN] BTC Hedge Active: {btc_24h:.1f}% (< {BTC_HEDGE_THRESHOLD * 100:.1f}%)"
            )

        # ─────────────────────────────────────────────────────────────────────
        # Portfolio Correlation (Sniper only)
        # ─────────────────────────────────────────────────────────────────────
        if mode == "sniper" and positions and self.portfolio_manager:
            try:
                existing_pairs = list(positions.keys())
                is_safe, warnings = await self.portfolio_manager.check_correlation(
                    pair, existing_pairs
                )
                if warnings:
                    for w in warnings:
                        if hasattr(w, "action") and w.action == "avoid":
                            return False, f"Corrélation: {w.warning}", context
                    if any(
                        hasattr(w, "action") and w.action in ["reduce", "caution"]
                        for w in warnings
                    ):
                        confidence -= F5
                        context["correlation_penalty"] = F5
            except Exception:
                pass

        # ─────────────────────────────────────────────────────────────────────
        # Exposure limit
        # ─────────────────────────────────────────────────────────────────────
        regime = self.detect_regime(btc_24h)
        multiplier = REGIME_MULTIPLIERS.get(regime, 1.0)
        context["regime"] = regime
        context["multiplier"] = multiplier

        current_exposure = sum(p.get("cost", 0) for p in positions.values())
        max_exposure = cash * multiplier
        if current_exposure >= max_exposure and action == "BUY":
            return (
                False,
                f"Limite exposition ({current_exposure:.0f}/{max_exposure:.0f})",
                context,
            )

        # ─────────────────────────────────────────────────────────────────────
        # Position count limit (SOTA v5.10: Dynamic from level)
        # ─────────────────────────────────────────────────────────────────────
        max_positions = context.get("max_positions", strategy.max_positions)
        if len(positions) >= max_positions and action == "BUY":
            return False, f"Max positions ({max_positions}) atteint", context

        # ─────────────────────────────────────────────────────────────────────
        # Cash check (SOTA v5.10: Dynamic from level)
        # ─────────────────────────────────────────────────────────────────────
        min_trade = context.get("min_trade", strategy.min_trade)
        if action == "BUY" and cash < min_trade:
            return (
                False,
                f"Cash insuffisant ({cash:.2f}€ < {min_trade}€)",
                context,
            )

        return True, "Validation OK", context

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. AI CONSULTATION (GATTACA)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _consult_ai(
        self,
        pair: str,
        action: str,
        confidence: float,
        indicators: Dict,
        btc_24h: float,
        mode: str,
        candles: pl.DataFrame,
    ) -> Tuple[bool, str]:
        """
        Consult Gattaca AI for final trading validation.

        Returns:
            (approved, reason)
        """
        # SOTA v5.8: Use specific "Buy Validation" toggle (Ghost button fixed)
        ai_validation_enabled = getattr(self.config, "ai_buy_validation", True)
        if not ai_validation_enabled:
            logger.info(f"🤖 [AI] {pair} → Validation IA désactivée (bypass)")
            return True, "Validation désactivée"
        else:
            logger.info(f"🤖 [AI] {pair} → Consultation IA en cours...")

        # Format candles for prompt
        candles_str = "No data"
        try:
            recent = candles.tail(F18)
            candles_str = recent.select(
                ["timestamp", "open", "high", "low", "close", "volume"]
            ).write_csv()
        except Exception:
            pass

        btc_ctx = indicators.get("btc_context", {})
        order_flow = indicators.get("order_flow", {})

        # SOTA v5.5: PANOPTICON (Vision Integration) 👁️
        vision_analysis = {}
        if getattr(self.config, "panopticon_enabled", False):
            try:
                from jobs.trader.intelligence.panopticon import panopticon

                logger.info(f"👁️ [PANOPTICON] {pair} → Analyse visuelle en cours...")
                vision_analysis = await panopticon.gaze(pair)
                if vision_analysis.get("sentiment"):
                    logger.info(
                        f"👁️ [PANOPTICON] {pair} → {vision_analysis.get('sentiment')} (Conf: {vision_analysis.get('confidence', 0)}%)"
                    )
            except Exception as e:
                logger.warning(f"👁️ [BRAIN] Panopticon failed: {e}")

        # ⚛️ SOTA v6.0: QUANTUM PULSE (Tsunami Detector)
        quantum_ctx = "N/A"
        if getattr(self.config, "quantum_enabled", True):
            try:
                from jobs.trader.intelligence.quantum import quantum

                # Use stored state from singleton
                q_score = quantum.coherence_score
                q_state = (
                    "QUANTUM_ALIGNMENT"
                    if q_score > 0.8
                    else ("RESONANCE" if q_score > 0.6 else "CHAOS")
                )
                quantum_ctx = f"{q_state} (Score: {q_score:.2f})"
                logger.info(f"⚛️ [QUANTUM] {pair} → {q_state} | Score={q_score:.2f}")
            except Exception:
                pass

        strategy = SNIPER if mode == "sniper" else MITRAILLETTE
        sl_pct_display = abs(strategy.stop_loss * 100)

        # SOTA: Dynamic Prompt based on Action (BUY or SELL)
        verb = "ACHAT" if action == "BUY" else "VENTE"
        expected_response = "BUY" if action == "BUY" else "SELL"

        prompt = f"""Je suis un trader crypto en mode {mode.upper()} (scalping avec stop-loss serrés à -{sl_pct_display:.2f}%).
On envisage une {verb} sur {pair}. Voici les données complètes.

CONTEXTE:
- Action Prévue: {action}
- Confidence: {confidence:.1f}%
- Confidence: {confidence:.1f}%
- BTC 24h: {btc_24h:+.2f}% (crash mode: {btc_ctx.get("is_crashing", False)})
- POULE QUANTIQUE: {quantum_ctx}

ANALYSE VISUELLE (GEMINI VISION):
- Sentiment: {vision_analysis.get("sentiment", "N/A")}
- Signal: {vision_analysis.get("signal", "Pas de chart disponible")}
- Confiance Visuelle: {vision_analysis.get("confidence", 0)}%


INDICATEURS TECHNIQUES (15m):
- RSI: {indicators.get("rsi", 0):.1f} (en hausse: {indicators.get("rsi_rising", False)})
- MACD fort: {indicators.get("macd_strong", False)}
- Tendance haussière: {indicators.get("is_uptrend", False)}
- Zone Fibonacci: {indicators.get("in_fib_zone", False)}
- ATR: {indicators.get("atr_pct", 0) * 100:.2f}%
- Bollinger Position: {indicators.get("bb_position", 0.5):.2f}

DIVERGENCES:
- Bearish: {indicators.get("bearish_divergence", False)}
- Bullish: {indicators.get("bullish_divergence", False)}

WHALES:
- Activité: {indicators.get("whale_activity", False)}
- Sentiment: {indicators.get("whale_sentiment", "neutral")}

ORDER FLOW (CVD):
- Pression: {order_flow.get("trend", "neutral")}
- Valeur: {order_flow.get("value", 0):.2f}

BOUGIES (2500+ dernières, ~1 mois de contexte):
{candles_str}

Analyse et réponds {expected_response} ou SKIP suivi d'une raison en 1 ligne max."""

        try:
            from corpus.brain.gattaca import gattaca

            # ⚡ CIRCUIT BREAKER: Latency protection (F144 = 144s)
            try:
                # SOTA 2026: Explicit source attribution for logs
                response = await asyncio.wait_for(
                    gattaca.think(
                        prompt, route_id=gattaca.ROUTE_FLASH, source="TRADER:brain"
                    ),
                    timeout=144,  # Increased from F89 (89s) to 144s for API stability
                )
            except asyncio.TimeoutError:
                logger.warning("⚡ [BRAIN] AI Latency Timeout (>144s)")
                # Fail-Open Logic: If signal is very strong mathematically, we proceed.
                if confidence > 80:
                    return True, "AI Timeout (Fail Open - High Conf)"
                else:
                    return False, "AI Timeout (Fail Safe)"

            response_upper = response.upper()

            # 📊 Log AI Response (visibility on decisions)
            decision = (
                expected_response
                if expected_response in response_upper
                else ("SKIP" if "SKIP" in response_upper else "UNCLEAR")
            )
            reason_preview = (
                response.replace(expected_response, "").replace("SKIP", "").strip()[:60]
            )
            logger.info(f"🤖 [AI] {pair} [{action}]: {decision} → {reason_preview}")

            if expected_response in response_upper:
                approved = True
            elif "SKIP" in response_upper:
                approved = False
            else:
                # Fallback: high confidence = approve
                approved = confidence >= 70

            reason = (
                response.replace(expected_response, "").replace("SKIP", "").strip()[:80]
            )
            if not reason:
                reason = "OK" if approved else "Pass"

            return approved, reason

        except Exception as e:
            logger.warning(f"🧠 [BRAIN] IA indisponible: {e}")
            # Graceful degradation: approve if high confidence
            return confidence >= 70, "IA indisponible - décision basée sur confiance"

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_dynamic_config(
        self, pair: str, mode: str, override_level: Optional[int] = None
    ) -> Tuple[float, float, Optional[float], float]:
        """
        Load pair-specific dynamic configuration with HOT RELOAD (mtime).
        Returns: (min_conf, stop_loss, exit_rsi, rsi_oversold)
        """
        import json
        import os

        if mode == "sniper":
            strategy = SNIPER
            ranges = SNIPER_RANGES
        else:
            strategy = MITRAILLETTE
            ranges = MITRAILLETTE_RANGES

        # SOTA v5.5: Respect Config Level (0=Low, 1=Default, 2=High)
        # Verify self.config is loaded
        if not self.config:
            from jobs.trader.config import TraderConfig

            self.config = TraderConfig.load()

        # Use override if provided (AI Mode), else User Config
        if override_level is not None:
            level = override_level
        else:
            level = getattr(self.config, "level", 1)

        # Ensure level is 0, 1, or 2
        level_idx = max(0, min(2, level))

        # Get defaults based on Level from Ranges
        # If range has 3 items, take index. If not, fallback to strategy default.
        def get_level_val(param_name, default_val):
            if param_name in ranges and len(ranges[param_name]) >= 3:
                return ranges[param_name][level_idx]
            return default_val

        conf = get_level_val("min_confidence", strategy.min_confidence)
        sl = get_level_val("stop_loss", strategy.stop_loss)
        def_rsi_oversold = get_level_val("rsi_oversold", strategy.rsi_oversold)

        symbol_safe = pair.replace("/", "")
        # SOTA v5.8: Include level in cache key to prevent stale values on level change
        cache_key = f"{symbol_safe}_{mode}_{level_idx}"
        config_path = (
            MEMORIES_DIR / "trader" / "configs" / f"active_config_{symbol_safe}.json"
        )

        # 1. Check File State (Hot Reload)
        current_mtime = 0.0
        file_exists = False

        try:
            stat = os.stat(config_path)
            current_mtime = stat.st_mtime
            file_exists = True
        except OSError:
            pass  # File not found or inaccessible

        # 2. Cache Hit Check
        cached = self._config_cache.get(cache_key)

        if cached:
            # Check validity
            valid_cache = False
            if file_exists and cached["mtime"] == current_mtime:
                valid_cache = True
            elif not file_exists and cached["mtime"] == 0:
                valid_cache = True

            if valid_cache:
                return (
                    cached["conf"],
                    cached["sl"],
                    cached.get("exit_rsi"),
                    cached.get("rsi_oversold", def_rsi_oversold),
                )

        # 3. Cache Miss (Reload from disk or defaults)
        data = {}
        if file_exists:
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        params = data.get("parameters", {})
        raw_conf = params.get("min_confidence", conf)
        raw_sl = params.get("stop_loss_pct", sl)
        raw_exit_rsi = params.get("exit_rsi", 0)
        raw_rsi_oversold = params.get("rsi_oversold", def_rsi_oversold)

        # SOTA v5.8: Apply profile bounds correctly (handle inverted ranges)
        # For min_confidence: Passive=76.4, Aggressive=55 → bounds are 55-76.4
        # For rsi_oversold: Passive=21, Aggressive=42.36 → bounds are 21-42.36
        def clamp_to_range(value, range_values):
            """Clamp value to the range defined by min and max of range_values."""
            min_bound = min(range_values)
            max_bound = max(range_values)
            return max(min_bound, min(max_bound, float(value)))

        final_conf = clamp_to_range(raw_conf, ranges["min_confidence"])
        final_sl = clamp_to_range(raw_sl, ranges["stop_loss"])
        final_exit_rsi = float(raw_exit_rsi) if raw_exit_rsi > 0 else None
        final_rsi_oversold = clamp_to_range(raw_rsi_oversold, ranges["rsi_oversold"])

        # 4. Update Cache
        self._config_cache[cache_key] = {
            "conf": final_conf,
            "sl": final_sl,
            "exit_rsi": final_exit_rsi,
            "rsi_oversold": final_rsi_oversold,
            "mtime": current_mtime,
        }

        return final_conf, final_sl, final_exit_rsi, final_rsi_oversold

    def get_btc_context(self) -> Dict:
        """Get BTC market context for trading decisions."""
        try:
            import asyncio

            # Try to get from running loop or create sync version
            try:
                asyncio.get_running_loop()
                # We're in async context, can't do sync call
                return {"status": "async_context", "note": "Use btc_24h parameter"}
            except RuntimeError:
                pass

            # Sync fallback - not ideal but works for init
            return {"status": "no_data"}

        except Exception:
            return {"status": "error"}

    def detect_regime(self, btc_24h: float) -> str:
        """
        Detect market regime based on BTC 24h movement.

        Returns:
            'BULL', 'BEAR', 'CRASH', or 'RANGE'
        """
        if btc_24h > 3.0:
            return "BULL"
        elif btc_24h < -5.0:
            return "CRASH"
        elif btc_24h < -2.0:
            return "BEAR"
        return "RANGE"

    def _log_rejection(self, pair: str, reason: str, confidence: float) -> None:
        """Log rejected signals for analysis."""
        self._rejection_log.append(
            {
                "pair": pair,
                "reason": reason,
                "confidence": confidence,
                "timestamp": time.time(),
            }
        )
        # Keep only last 100
        self._rejection_log = self._rejection_log[-100:]
        logger.debug(f"🧠 [BRAIN] Rejeté: {pair} - {reason} ({confidence:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════════════
    # CIRCUIT BREAKER & DAILY TRACKING
    # ═══════════════════════════════════════════════════════════════════════════

    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily P&L for circuit breaker."""
        self._daily_pnl += pnl

    def reset_daily(self) -> None:
        """Reset daily metrics (call at midnight)."""
        self._daily_pnl = 0.0

    def get_daily_pnl(self) -> float:
        """Get current daily P&L."""
        return self._daily_pnl

    def update_portfolio_peak(self, value: float) -> None:
        """Update portfolio peak for drawdown calculation."""
        if value > self._portfolio_peak:
            self._portfolio_peak = value

    # ═══════════════════════════════════════════════════════════════════════════
    # LEGACY COMPATIBILITY (create_signal for backward compat)
    # ═══════════════════════════════════════════════════════════════════════════

    def create_signal(self, pair: str, df: pl.DataFrame, mode: str = None) -> Signal:
        """
        Legacy synchronous signal creation (without AI).

        For full pipeline with AI, use `await decide()` instead.
        """
        # 1. Evaluate
        indicators = self.evaluate(pair, df)

        if "error" in indicators:
            return Signal.hold(pair, indicators["error"], indicators=indicators)

        # 2. Detect
        action, confidence, reason = self.detect_signal(indicators, mode)
        price = indicators["price"]

        # 3. Create Signal (no validation or AI)
        if action == "HOLD":
            return Signal.hold(pair, reason, price=price, indicators=indicators)

        if action == "SELL":
            return Signal.sell(pair, price, reason, confidence, indicators=indicators)

        # BUY signal - calculate SL/TP
        strategy = self.config.get_strategy()

        # SOTA: Fee-Aware Logic (Creation Mode)
        fees_buffer = 2 * ESTIMATED_FEES

        # Stop Loss: Tighten to keep Net Loss within strategy limit
        # sl is negative. We add fees to make it less negative (tighter).
        adjusted_sl = strategy.stop_loss + fees_buffer
        stop_loss = price * (1 + adjusted_sl)

        # Take Profit: Increase target to ensure Net Profit = strategy.tp
        take_profit = price * (1 + strategy.tp1 + fees_buffer)

        golden_steps = [price * (1 + step) for step in GOLDEN_STEPS]

        return Signal.buy(
            pair=pair,
            price=price,
            reason=reason,
            confidence=confidence,
            stop_loss=stop_loss,
            take_profit=take_profit,
            mode=mode or self.config.mode,
            golden_steps=golden_steps,
            indicators=indicators,
        )

    def log_rejection(self, pair: str, reason: str, confidence: float) -> None:
        """Public alias for _log_rejection (backward compat)."""
        self._log_rejection(pair, reason, confidence)


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════


def create_brain(config: TraderConfig = None) -> TradingBrain:
    """Factory function to create a TradingBrain instance."""
    return TradingBrain(config)
