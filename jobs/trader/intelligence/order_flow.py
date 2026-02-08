"""
JOBS/TRADER/INTELLIGENCE/ORDER_FLOW.PY
==============================================================================
MODULE: ORDER FLOW ANALYZER (CVD) 📊
PURPOSE: Aggregate real-time trades and calculate Cumulative Volume Delta.
==============================================================================
"""

import time
import json
from collections import deque
from typing import Dict, Optional
import polars as pl
from loguru import logger

from jobs.trader.config import MEMORIES_DIR


CVD_STATE_FILE = MEMORIES_DIR / "trader" / "cvd_state.json"


class OrderFlowAnalyzer:
    """
    Order Flow Analyzer.

    Calculates CVD (Cumulative Volume Delta) to detect market pressure.
    Includes persistence for restart recovery.
    """

    def __init__(self, max_trades: int = 5000, imbalance_threshold: float = 2.618):
        self._max_trades = max_trades
        self._imbalance_threshold = imbalance_threshold
        self._trade_buffers: Dict[str, deque] = {}
        self._cvd_state: Dict[str, Dict] = {}
        self._last_signal_time: Dict[str, float] = {}
        self._load_state()

    def add_trade(self, symbol: str, trade_data: Dict) -> None:
        """
        Ingest a single trade.

        Args:
            symbol: Pair (e.g., "BTC/EUR")
            trade_data: {'side': 'buy', 'price': 50000, 'volume': 0.1}
        """
        if symbol not in self._trade_buffers:
            self._trade_buffers[symbol] = deque(maxlen=self._max_trades)

        trade = {
            "price": float(trade_data.get("price", trade_data.get("last", 0))),
            "volume": float(trade_data.get("volume", trade_data.get("qty", 0))),
            "side": trade_data.get("side", "unknown"),
            "timestamp": trade_data.get("timestamp", time.time()),
        }
        self._trade_buffers[symbol].append(trade)

        # ⚡ TICK-BY-TICK ANALYSIS (Real-Time Impulse)
        # We don't wait for the cycle. We check immediate market pressure.
        impulse = self._check_tick_imbalance(symbol)
        if impulse:
            # In a full event-driven system, we would emit('signal', impulse) here.
            # For now, we log it, and it will be picked up by the next high-freq loop check or stored in state.
            logger.debug(f"⚡ [ORDER FLOW] {symbol} {impulse}")

    def compute_cvd(self, symbol: str) -> Optional[Dict]:
        """
        Calculate CVD for a symbol.

        CVD = Sum(buy_volume) - Sum(sell_volume)
        Positive = buying pressure, Negative = selling pressure

        Returns:
            {'value': float, 'trend': str, 'buy_volume': float, 'sell_volume': float}
        """
        trades = list(self._trade_buffers.get(symbol, []))
        if not trades:
            return None

        try:
            df = pl.DataFrame(trades)

            buy_vol = df.filter(pl.col("side") == "buy")["volume"].sum()
            sell_vol = df.filter(pl.col("side") == "sell")["volume"].sum()
            cvd_value = buy_vol - sell_vol

            trend = (
                "bullish"
                if cvd_value > 0
                else ("bearish" if cvd_value < 0 else "neutral")
            )

            self._cvd_state[symbol] = {
                "value": float(cvd_value),
                "trend": trend,
                "buy_volume": float(buy_vol),
                "sell_volume": float(sell_vol),
                "trade_count": len(trades),
                "timestamp": time.time(),
            }
            return self._cvd_state[symbol]

        except Exception as e:
            logger.error(f"[CVD] Error {symbol}: {e}")
            return None

    def _check_tick_imbalance(self, symbol: str) -> Optional[str]:
        """
        Check for immediate order flow imbalance (Tick-by-Tick).

        Logic:
        - Analyze last 100 ticks (rolling window)
        - Calculate Buy/Sell Volume Ratio
        - Detect impulses using Golden Ratio (Phi)

        Returns:
            "IMPULSE_BUY", "IMPULSE_SELL", or None
        """
        # Anti-spam protection (Limit to 1 signal every 5 seconds per pair)
        now = time.time()
        if now - self._last_signal_time.get(symbol, 0) < 5.0:
            return None

        buffer = self._trade_buffers.get(symbol)
        if not buffer or len(buffer) < 20:  # Need at least some trades
            return None

        # Get last 100 trades efficiently
        # Deque doesn't support slicing easily, so we convert to list (costly but ok for 100 items)
        # Optimization: iterate purely on deque from right

        recent_trades = list(buffer)[-100:]

        buy_vol = 0.0
        sell_vol = 0.0

        for t in recent_trades:
            if t["side"] == "buy":
                buy_vol += t["volume"]
            elif t["side"] == "sell":
                sell_vol += t["volume"]

        # Avoid division by zero
        if sell_vol == 0:
            ratio = 100.0 if buy_vol > 0 else 0.0
        else:
            ratio = buy_vol / sell_vol

        # Thresholds (Phi-based)
        # Bullish > 2.618 (Phi^2)
        # Bearish < 0.382 (1/Phi^2)

        signal = None

        # We also check minimum volume to avoid noise on micro-trades
        # total_vol = buy_vol + sell_vol
        # This volume threshold should ideally be dynamic or per-pair (e.g. > 1 BTC or > 1000 EUR)
        # For generic usage, we stick to ratio driven, assuming '100 ticks' filters out single dust trades noise

        if ratio > 2.618:
            signal = "IMPULSE_BUY"
        elif ratio < 0.382:
            signal = "IMPULSE_SELL"

        if signal:
            self._last_signal_time[symbol] = now
            # Update state immediately for external readers
            if symbol not in self._cvd_state:
                self._cvd_state[symbol] = {}
            self._cvd_state[symbol]["last_impulse"] = signal
            self._cvd_state[symbol]["impulse_ratio"] = ratio

        return signal

    def get_cvd_context(self, symbol: str) -> Optional[Dict]:
        """Get CVD context, computing if needed."""
        if symbol in self._trade_buffers and len(self._trade_buffers[symbol]) > 10:
            self.compute_cvd(symbol)
            if len(self._trade_buffers[symbol]) % 100 == 0:
                self._save_state()
        return self._cvd_state.get(symbol)

    def get_pressure_signal(self, symbol: str) -> str:
        """
        Get simple signal based on CVD.

        Returns:
            'BUY', 'SELL', or 'NEUTRAL'
        """
        cvd = self._cvd_state.get(symbol, {})
        # value = cvd.get("value", 0)

        if cvd.get("value", 0) > 100:
            return "BUY"
        elif cvd.get("value", 0) < -100:
            return "SELL"
        return "NEUTRAL"

    def clear_buffer(self, symbol: str) -> None:
        """Clear buffer for a symbol."""
        if symbol in self._trade_buffers:
            self._trade_buffers[symbol].clear()
        if symbol in self._cvd_state:
            del self._cvd_state[symbol]

    def get_all_cvd(self) -> Dict[str, Dict]:
        """Get all CVD states."""
        return self._cvd_state.copy()

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_state(self) -> None:
        """Load CVD state from disk."""
        try:
            if CVD_STATE_FILE.exists():
                with open(CVD_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._cvd_state = data.get("cvd_state", {})
                logger.debug(f"📊 [CVD] Loaded state for {len(self._cvd_state)} pairs")
        except Exception as e:
            logger.warning(f"📊 [CVD] Could not load state: {e}")

    def _save_state(self) -> None:
        """Save CVD state to disk."""
        try:
            CVD_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CVD_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"cvd_state": self._cvd_state, "timestamp": time.time()},
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"📊 [CVD] Could not save state: {e}")

    def save(self) -> None:
        """Public method to save state."""
        self._save_state()


def create_order_flow(max_trades: int = 5000) -> OrderFlowAnalyzer:
    """Factory function to create OrderFlowAnalyzer."""
    return OrderFlowAnalyzer(max_trades)
