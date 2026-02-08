"""
JOBS/TRADER/DATA/FEED.PY
==============================================================================
MODULE: WEBSOCKET PRICE FEED ⚡
PURPOSE: Real-time price data from Kraken WebSocket.
FEATURES:
    - Auto-reconnect with exponential backoff
    - Progressive subscription (batched)
    - Trade feed for CVD (optional)
==============================================================================
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable
from corpus.soma.nerves import logger  # SOTA: DEBUG level

try:
    import websockets
except ImportError:
    websockets = None
    logger.warning("⚡ WebSockets Missing")

from jobs.trader.config import PHI, F34


WS_URL = "wss://ws.kraken.com"


class KrakenFeed:
    """
    WebSocket client for Kraken real-time data.

    Features:
    - Ticker subscriptions
    - Trade feed for CVD analysis
    - Auto-reconnect with backoff
    - Local price cache
    """

    def __init__(self):
        self._connection = None
        self._tickers: Dict[str, Dict] = {}
        self._subscribed_pairs: List[str] = []
        self._is_running: bool = False
        self._lock = asyncio.Lock()
        self._retry_count: int = 0
        self._trade_enabled: bool = False
        self._trade_callback: Optional[Callable] = None
        self._price_callbacks: List[Callable] = []

    def on_price_update(self, callback: Callable) -> None:
        """Register callback for price updates."""
        self._price_callbacks.append(callback)

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connection is not None and self._is_running

    # ═══════════════════════════════════════════════════════════════════════════
    # CONNECTION
    # ═══════════════════════════════════════════════════════════════════════════

    async def connect(self) -> None:
        """Connect to Kraken WebSocket with exponential backoff."""
        if websockets is None:
            logger.error("⚡ WS Library Missing")
            return

        try:
            # SOTA: Add ping/pong to keep connection alive through idle periods
            self._connection = await websockets.connect(
                WS_URL, ping_interval=20, ping_timeout=20, close_timeout=10
            )
            self._is_running = True
            self._retry_count = 0
            logger.success("⚡ Feed Connected")

            # Resubscribe if we had previous subscriptions
            if self._subscribed_pairs:
                await self._send_subscribe(self._subscribed_pairs)

            # Start listener
            asyncio.create_task(self._listen())

        except Exception:
            wait_time = min(60, 2**self._retry_count)
            logger.error(f"⚡ Connect Fail, retry {wait_time}s")
            self._retry_count += 1
            await asyncio.sleep(wait_time)
            if self._is_running:
                await self.connect()

    async def close(self) -> None:
        """Close WebSocket connection."""
        self._is_running = False
        if self._connection:
            await self._connection.close()
            self._connection = None
        logger.debug("[FEED] Disconnected")

    # ═══════════════════════════════════════════════════════════════════════════
    # SUBSCRIPTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def subscribe(self, pairs: List[str]) -> None:
        """
        Subscribe to ticker updates for pairs.

        Args:
            pairs: List of pairs (e.g., ["BTC/EUR", "ETH/EUR"])
        """
        async with self._lock:
            # Normalize pairs for Kraken (BTC -> XBT)
            normalized = [p.replace("BTC", "XBT").upper() for p in pairs]
            self._subscribed_pairs = normalized

            if self._connection:
                await self._send_subscribe(normalized)

    async def subscribe_progressive(
        self, pairs: List[str], batch_size: int = F34
    ) -> None:
        """
        Subscribe to pairs in batches to avoid overwhelming WebSocket.

        Args:
            pairs: Full list of pairs
            batch_size: Pairs per batch (default: F34 = 34)
        """
        normalized = [p.replace("BTC", "XBT").upper() for p in pairs]
        total = len(normalized)
        batches = [normalized[i : i + batch_size] for i in range(0, total, batch_size)]

        logger.debug(
            f"[FEED] Progressive subscribe: {total} pairs in {len(batches)} batches"
        )

        for i, batch in enumerate(batches):
            async with self._lock:
                for pair in batch:
                    if pair not in self._subscribed_pairs:
                        self._subscribed_pairs.append(pair)

                if self._connection:
                    await self._send_subscribe(batch)

            # Wait between batches
            if i < len(batches) - 1:
                await asyncio.sleep(PHI)

        logger.success(f"⚡ All {total} Subscribed")

    async def _send_subscribe(self, pairs: List[str]) -> None:
        """Send subscription message to WebSocket."""
        if not self._connection:
            return

        # Ticker subscription
        ticker_payload = {
            "event": "subscribe",
            "pair": pairs,
            "subscription": {"name": "ticker"},
        }
        await self._connection.send(json.dumps(ticker_payload))

        # Trade subscription (if enabled)
        if self._trade_enabled:
            trade_payload = {
                "event": "subscribe",
                "pair": pairs,
                "subscription": {"name": "trade"},
            }
            await self._connection.send(json.dumps(trade_payload))

        logger.debug(f"⚡ [FEED] Subscribed to {len(pairs)} pairs")

    # ═══════════════════════════════════════════════════════════════════════════
    # LISTENER
    # ═══════════════════════════════════════════════════════════════════════════

    async def _listen(self) -> None:
        """Main WebSocket listener loop."""
        while self._is_running and self._connection:
            try:
                msg = await self._connection.recv()
                data = json.loads(msg)

                # Skip heartbeats
                if isinstance(data, dict) and data.get("event") == "heartbeat":
                    continue

                # Parse ticker/trade updates
                # Format: [channelID, data, channelName, pair]
                if isinstance(data, list) and len(data) >= 4:
                    channel_name = data[-2]
                    pair_name = data[-1]

                    if channel_name == "ticker":
                        self._process_ticker(pair_name, data[1])
                    elif channel_name == "trade" and self._trade_enabled:
                        await self._process_trades(pair_name, data[1])

            except Exception as e:
                if "ConnectionClosed" in str(type(e).__name__):
                    # Capture close details if available
                    code = getattr(e, "code", "Unknown")
                    logger.warning(f"⚡ Closed {code}, reconnecting")
                    # SOTA v4.5: Only reconnect if still running, don't break
                    if self._is_running:
                        self._connection = None  # Clear stale connection
                        await asyncio.sleep(PHI)  # Brief backoff before reconnect
                        await self.connect()
                    return  # Exit this listener instance (new one started by connect())
                else:
                    logger.error("⚡ Listener Error")
                    await asyncio.sleep(PHI)

    def _process_ticker(self, pair: str, ticker_data: Dict) -> None:
        """Process ticker update."""
        if "c" in ticker_data:  # Close price
            close_price = float(ticker_data["c"][0])
            self._tickers[pair] = {
                "price": close_price,
                "pair": pair,
                "bid": float(ticker_data.get("b", [0])[0]),
                "ask": float(ticker_data.get("a", [0])[0]),
                "volume": float(ticker_data.get("v", [0, 0])[1]),  # 24h volume
            }

            # SOTA: Event-Driven Dispatch
            for cb in self._price_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        asyncio.create_task(cb(pair, close_price))
                    else:
                        cb(pair, close_price)
                except Exception:
                    logger.error("⚡ Callback Error")

    async def _process_trades(self, pair: str, trades: List) -> None:
        """Process trade data for CVD."""
        if not self._trade_callback:
            return

        for trade in trades:
            if len(trade) >= 4:
                trade_data = {
                    "pair": pair,
                    "price": float(trade[0]),
                    "volume": float(trade[1]),
                    "timestamp": float(trade[2]),
                    "side": "buy" if trade[3] == "b" else "sell",
                }
                # Support both async and sync callbacks
                res = self._trade_callback(trade_data)
                if asyncio.iscoroutine(res):
                    await res

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA ACCESS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_price(self, pair: str) -> float:
        """
        Get cached price for a pair.

        Args:
            pair: Trading pair (e.g., "BTC/EUR")

        Returns:
            Last price or 0.0 if not available
        """
        key = pair.replace("BTC", "XBT").replace("/", "")
        # Try different formats
        for k in [key, pair.replace("BTC", "XBT"), pair]:
            if k in self._tickers:
                return self._tickers[k].get("price", 0.0)
        return 0.0

    def get_ticker(self, pair: str) -> Optional[Dict]:
        """Get full ticker data for a pair."""
        key = pair.replace("BTC", "XBT")
        return self._tickers.get(key)

    def get_all_prices(self) -> Dict[str, float]:
        """Get all cached prices."""
        return {pair: data.get("price", 0) for pair, data in self._tickers.items()}

    def get_all_tickers(self) -> Dict[str, Dict]:
        """
        Get all cached ticker objects.

        Returns:
            Dict[str, Dict]: Map of pair -> ticker data
        """
        return self._tickers.copy()

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════

    def enable_trade_feed(
        self, enabled: bool = True, callback: Callable = None
    ) -> None:
        """
        Enable/disable trade feed for CVD analysis.

        Args:
            enabled: Whether to enable
            callback: Function to call with trade data
        """
        self._trade_enabled = enabled
        self._trade_callback = callback
        logger.debug(f"[FEED] Trade feed {'enabled' if enabled else 'disabled'}")


def create_feed() -> KrakenFeed:
    """Factory function to create KrakenFeed."""
    return KrakenFeed()
