"""
JOBS/TRADER/EXECUTION/SCANNER.PY
==============================================================================
MODULE: MARKET SCANNER 🔍
PURPOSE: Identify tradeable pairs by volume, spread, and filters.
==============================================================================
"""

import time
import asyncio
from typing import Dict, List, Tuple, Set
from corpus.soma.nerves import logger  # SOTA: DEBUG level

from jobs.trader.config import (
    SCAN_TOP_X,
    SELL_COOLDOWN,
    MAX_SPREAD_DEFAULT,
    SPREAD_EXCEPTIONS,
    OHLCV_EXCLUDED_PAIRS,
    NO_OHLCV_BLACKLIST_DURATION,
)


class MarketScanner:
    """
    Market Scanner for identifying trading candidates.

    Features:
    - Filter by EUR pairs
    - Sort by volume
    - Spread validation
    - Blacklist management
    - Sell cooldown tracking
    """

    def __init__(self):
        self.blacklist: Set[str] = set()
        self.sell_log: Dict[str, float] = {}  # pair -> last_sell_timestamp

    async def scan(
        self,
        exchange,
        existing_positions: Dict = None,
        limit: int = None,
        feed=None,  # Optional KrakenFeed
    ) -> List[Tuple[str, Dict]]:
        """
        Scan market for trading candidates.

        Args:
            exchange: KrakenExchange instance
            existing_positions: Dict of current positions to exclude
            limit: Max pairs to return (default: SCAN_TOP_X)
            feed: Optional KrakenFeed instance for real-time data

        Returns:
            List of (pair, ticker) sorted by volume
        """
        limit = limit or SCAN_TOP_X
        existing_positions = existing_positions or {}

        try:
            # 1. Fetch tickers (Feed preferred, fallback to API)
            all_tickers = {}
            used_feed = False

            if feed and feed.is_connected:
                # Use cached data from WebSocket
                feed_data = feed.get_all_prices()
                if feed_data:
                    # Convert feed format to match scanner expectations
                    # Feed: {pair: {"price": x, "volume": y, ...}}
                    # Scanner expects CCXT ticker format for validation
                    for pair, data in feed.get_all_tickers().items():
                        # Filter EUR pairs here for efficiency
                        if "/EUR" in pair and "USD" not in pair:
                            all_tickers[pair] = {
                                "last": data.get("price"),
                                "bid": data.get("bid"),
                                "ask": data.get("ask"),
                                "baseVolume": data.get("volume"),  # 24h volume
                                "symbol": pair,
                            }
                    used_feed = True
                    logger.debug(f"🔍 Feed {len(all_tickers)}p")

            if not used_feed or not all_tickers:
                # Fallback to REST API
                if used_feed:
                    logger.warning("🔍 Feed Empty")
                all_tickers = await exchange.fetch_tickers()

            # 2. Filter EUR pairs (Redundant if feed used, but safe)
            eur_pairs = {
                pair: ticker
                for pair, ticker in all_tickers.items()
                if "/EUR" in pair and "USD" not in pair
            }

            # 3. Sort by volume
            sorted_pairs = sorted(
                eur_pairs.items(),
                key=lambda x: (x[1].get("baseVolume") or 0) if x[1] else 0,
                reverse=True,
            )[:limit]

            # 4. Filter excluded pairs
            candidates = []
            for pair, ticker in sorted_pairs:
                exclusion = self._check_exclusion(pair, ticker, existing_positions)
                if exclusion is None:
                    candidates.append((pair, ticker))

            logger.debug(f"🔍 {len(candidates)}/{len(sorted_pairs)} pairs")
            return candidates

        except Exception:
            logger.error("🔍 Scan Fail")
            return []

    def _check_exclusion(self, pair: str, ticker: Dict, positions: Dict) -> str | None:
        """
        Check if pair should be excluded.

        Returns:
            Exclusion reason or None if OK
        """
        # 1. Already in position (Fuzzy Check)
        if pair in positions:
            return "IN_POSITION"

        # Fuzzy Match (TRX/EUR == XTRX/EUR)
        norm_pair = pair.replace("XBT", "BTC").replace("XDG", "DOGE")
        if "/" in norm_pair:
            b, q = norm_pair.split("/")
            if len(b) == 4 and b[0] in ["X", "Z"]:
                b = b[1:]
            norm_pair = f"{b}/{q}"

        for pos_pair in positions:
            norm_pos = pos_pair.replace("XBT", "BTC").replace("XDG", "DOGE")
            if "/" in norm_pos:
                pb, pq = norm_pos.split("/")
                if len(pb) == 4 and pb[0] in ["X", "Z"]:
                    pb = pb[1:]
                norm_pos = f"{pb}/{pq}"

            if norm_pos == norm_pair:
                return "IN_POSITION_ALIAS"

        # 2. In blacklist
        if pair in self.blacklist:
            return "BLACKLISTED"

        # 3. BTC Sacred (treated separately - Strictly Forbidden for Trading)
        # SOTA: Robust check against XBT, XXBT, BTC aliases
        norm_check = (
            pair.replace("XXBT", "BTC").replace("XBT", "BTC").replace("ZBTC", "BTC")
        )
        if "BTC" in norm_check:
            return "BTC_SACRED"

        # 4. No OHLCV data available (WebSocket only)
        if pair in OHLCV_EXCLUDED_PAIRS:
            return "NO_OHLCV"

        # 4. Cooldown check
        if pair in self.sell_log:
            if time.time() - self.sell_log[pair] < SELL_COOLDOWN:
                return "COOLDOWN"

        # 5. Spread check
        if ticker:
            bid = ticker.get("bid", 0)
            ask = ticker.get("ask", 0)
            if bid and ask:
                spread = (ask - bid) / bid
                max_spread = SPREAD_EXCEPTIONS.get(pair, MAX_SPREAD_DEFAULT)
                if spread > max_spread:
                    return f"SPREAD_HIGH_{spread * 100:.1f}%"

        return None

    def add_to_blacklist(self, pair: str, duration_seconds: int = 3600) -> None:
        """
        Add pair to temporary blacklist.

        Args:
            pair: Pair to blacklist
            duration_seconds: Auto-remove after this duration
        """
        self.blacklist.add(pair)
        asyncio.create_task(self._remove_from_blacklist(pair, duration_seconds))
        logger.info(f"🔍 Blacklist {pair} {duration_seconds}s")

    def blacklist_no_ohlcv_pairs(self, exchange) -> None:
        """
        Auto-blacklist pairs detected as having no OHLCV data.
        Called after trading cycle to catch pairs that failed fetch_candles.
        Blacklists for 1 week (confirmed not a network error).
        """
        no_ohlcv = exchange.pop_no_ohlcv_pairs()
        for pair in no_ohlcv:
            if pair not in self.blacklist:
                self.add_to_blacklist(pair, NO_OHLCV_BLACKLIST_DURATION)
                logger.info(f"🔍 {pair} no-OHLCV blacklist")

    async def _remove_from_blacklist(self, pair: str, delay: int) -> None:
        """Remove pair from blacklist after delay."""
        await asyncio.sleep(delay)
        self.blacklist.discard(pair)
        logger.debug(f"🔍 [SCANNER] Unblacklisted {pair}")

    def record_sell(self, pair: str) -> None:
        """Record a sell for cooldown tracking."""
        self.sell_log[pair] = time.time()

    def clear_cooldown(self, pair: str) -> None:
        """Clear cooldown for a pair."""
        self.sell_log.pop(pair, None)

    def clear_all_cooldowns(self) -> None:
        """Clear all cooldowns."""
        self.sell_log.clear()


def create_scanner() -> MarketScanner:
    """Factory function to create MarketScanner."""
    return MarketScanner()
