"""
JOBS/TRADER/KRAKEN/EXCHANGE.PY
==============================================================================
MODULE: KRAKEN EXCHANGE ADAPTOR (SOTA v4.0) 🔌
PURPOSE: Unified CCXT wrapper for all Kraken operations.
FEATURES:
    - Connection management
    - Data fetching (candles, tickers, balances)
    - Order execution (limit, market, OTO stop-loss)
    - Spread protection
    - Error recovery
NO SINGLETON: Use create_exchange() factory instead.
==============================================================================
"""

from typing import Optional, Tuple, Dict, Any, List
import asyncio
import time
from dataclasses import dataclass
import ccxt.async_support as ccxt
import polars as pl
import aiohttp
import socket
import ssl
import certifi
from corpus.soma.nerves import logger  # SOTA: DEBUG level

from corpus.dna.secrets import vault
from jobs.trader.config import (
    ESTIMATED_FEES,
    MAX_SPREAD_DEFAULT,
    SPREAD_EXCEPTIONS,
    TRADER_DRY_RUN,
    TraderConfig,
)


@dataclass
class OrderResult:
    """Result of an order execution."""

    success: bool
    message: str
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_amount: Optional[float] = None
    raw: Optional[Dict] = None


class KrakenExchange:
    """
    SOTA Kraken Exchange Adaptor.

    Features:
    - Limit-then-Market fallback
    - OTO (One-Triggers-Other) Server-Side Stop Loss
    - Spread protection
    - Intelligent error recovery
    - Balance & ticker fetching
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize exchange adaptor.

        Args:
            api_key: Kraken API key (defaults to vault)
            api_secret: Kraken API secret (defaults to vault)
        """
        self._exchange: Optional[ccxt.kraken] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key = api_key or vault.KRAKEN_API_KEY
        self._api_secret = api_secret or vault.KRAKEN_SECRET
        self._markets_loaded = False
        self._markets_cache: Dict = {}
        self._limits_cache: Dict[str, Dict] = {}
        self._is_shutting_down: bool = (
            False  # SOTA v4.5: Prevent post-shutdown API calls
        )
        self._no_ohlcv_pairs: set = set()  # Pairs with no OHLCV data (auto-detected)
        self._api_lock = (
            asyncio.Lock()
        )  # SOTA v4.6: Serialize authenticated API calls (nonce protection)
        self._markets_lock = (
            asyncio.Lock()
        )  # SOTA v4.7: Prevent race condition on startup

    async def _invoke_private(self, func_name: str, *args, **kwargs) -> Any:
        """
        SOTA v4.6: Secure Private API Invocation (Nonce Protection).

        Args:
            func_name: Name of CCXT method to call (e.g. 'fetch_ledger')
            *args, **kwargs: Arguments for the CCXT method
        """
        async with self._api_lock:
            # Dynamically get method from ccxt instance
            method = getattr(self._exchange, func_name)
            return await method(*args, **kwargs)

    def pop_no_ohlcv_pairs(self) -> set:
        """Get and clear the set of pairs detected as having no OHLCV data."""
        pairs = self._no_ohlcv_pairs.copy()
        self._no_ohlcv_pairs.clear()
        return pairs

    def _normalize_pair(self, pair: str) -> str:
        """
        Normalize Kraken legacy symbols.

        Fixes:
        - XDG -> DOGE (Kraken returns XDG in tickers but expects DOGE in OHLCV)
        - XBT -> BTC (Safety measure, though CCXT usually handles it)
        """
        if not pair:
            return pair
        return pair.replace("XDG", "DOGE").replace("XBT", "BTC")

    @property
    def is_connected(self) -> bool:
        """Check if exchange is connected."""
        return self._exchange is not None

    # ═══════════════════════════════════════════════════════════════════════════
    # CONNECTION
    # ═══════════════════════════════════════════════════════════════════════════

    async def connect(self) -> None:
        """Initialize connection to Kraken."""
        self._is_shutting_down = False  # SOTA v4.5: Reset shutdown flag on (re)connect

        if self._exchange:
            return

        # SOTA IPv4 Enforcement: Prevent multiple sessions
        if self._session and not self._session.closed:
            await self._session.close()

        # Phase 6: Unset Proxies to avoid interference
        import os

        for p in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            if p in os.environ:
                del os.environ[p]
                logger.debug(f"🕵️ [EXCHANGE] Unset env var: {p}")

        # SOTA v4.3: DNS Bypass Protocol
        # Force aiodns.AsyncResolver with Google/Cloudflare DNS.
        # This completely BYPASSES variable Windows OS resolvers/hooks.
        # Requires 'aiodns' (verified installed).

        from aiohttp.resolver import AsyncResolver

        ssl_context = ssl.create_default_context(cafile=certifi.where())

        resolver = AsyncResolver(nameservers=["8.8.8.8", "1.1.1.1"])

        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            resolver=resolver,
            family=socket.AF_INET,  # Explicit IPv4 often plays nicer with AsyncResolver
            force_close=False,
            enable_cleanup_closed=True,
        )

        self._session = aiohttp.ClientSession(connector=connector, trust_env=False)

        self._exchange = ccxt.kraken(
            {
                "apiKey": self._api_key,
                "secret": self._api_secret,
                "enableRateLimit": True,
                "userAgent": "Trinity/4.3 (Sovereign Life Form)",
                "timeout": 10000,
                "verbose": False,
                "session": self._session,
                "nonce": self._get_nonce,  # SOTA v5.14: Monotonic Nonce
                "options": {
                    "adjustForTimeDifference": True,
                },
            }
        )
        # SOTA v5.15: Server Time Sync Check
        # Ensure our clock isn't lagging behind Kraken, which causes Invalid Nonce
        await self._sync_server_time()
        logger.debug("🔌 [EXCHANGE] Connected to Kraken (AsyncResolver 8.8.8.8)")

    async def _sync_server_time(self) -> None:
        """
        SOTA v5.15: Synchronize with Kraken Server Time.
        Calculates offset to ensure nonce is always accepted.
        """
        try:
            # Public call, no auth needed
            # Use raw aiohttp to avoid circular dependency or lock issues
            if self._session:
                start = time.time()
                async with self._session.get("https://api.kraken.com/0/public/Time") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Kraken returns unixtime (seconds)
                        server_time = data.get("result", {}).get("unixtime", 0)
                        if server_time > 0:
                            latency = (time.time() - start) / 2
                            # We target server time + small buffer
                            self._time_offset = (server_time - time.time()) + latency
                            logger.debug(f"🔌 [EXCHANGE] Time Offset: {self._time_offset:.3f}s")
                        else:
                            self._time_offset = 0
            else:
                self._time_offset = 0
        except Exception as e:
            logger.warning(f"🔌 [EXCHANGE] Time Sync Failed: {e}")
            self._time_offset = 0

    def _get_nonce(self) -> int:
        """
        SOTA v5.15: Monotonic synced Nonce Generator.
        Uses server offset + monotonic increment.
        """
        import time

        # Apply offset (if any)
        offset = getattr(self, "_time_offset", 0)
        now = int((time.time() + offset) * 1000)

        # Initialize if needed
        if not hasattr(self, "_last_nonce"):
            self._last_nonce = 0

        # SOTA Protection: Ensure strictly greater
        if now <= self._last_nonce:
            # Collision or clock drift: force increment
            self._last_nonce += 1
        else:
            # Normal time progression
            self._last_nonce = now

        return self._last_nonce

    async def close(self) -> None:
        """Close exchange connection."""
        self._is_shutting_down = (
            True  # SOTA v4.5: Signal shutdown to prevent race conditions
        )

        if self._exchange:
            await (
                self._exchange.close()
            )  # This might not close the injected session depending on CCXT version
            self._exchange = None

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

        self._markets_loaded = False
        self._markets_cache = {}
        logger.debug("🔌 [EXCHANGE] Disconnected")

    async def _execute_with_retry(
        self, operation: str, func, *args, max_retries: int = 5, **kwargs
    ) -> Any:
        """
        Execute an operation with exponential backoff retry.

        Args:
            operation: Name of the operation for logging
            func: Async function to execute
            max_retries: Custom retry limit (default: 5)
            *args, **kwargs: Arguments for the function

        Returns:
            Result of the function

        Raises:
            Exception: If all retries fail
        """
        # PHI IMPERATIVE: Use Golden Ratio for natural backoff curve
        phi = 1.618

        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (
                ccxt.NetworkError,
                ccxt.ExchangeNotAvailable,
                ccxt.RequestTimeout,
                ccxt.InvalidNonce,
            ) as e:
                is_last = attempt == max_retries - 1
                if is_last:
                    logger.error(
                        f"🔌 [EXCHANGE] {operation} failed permanently after {max_retries} attempts: {e}"
                    )
                    raise e

                # SOTA Backoff: 1, 1.6, 2.6, 4.2, 6.8 (Total survival ~16s)
                wait_time = max(1.0, phi**attempt)

                # Enhanced Logging: Reveal underlying cause (IPv6? SSL? DNS?)
                error_msg = str(e)
                error_type = type(e).__name__

                # SOTA 2026: HTML Spam Protection (Cloudflare 500 Errors)
                if "<html" in error_msg.lower() or "<!doctype" in error_msg.lower():
                    # Truncate massively to prevent log flooding
                    error_msg = f"{error_type}: Cloudflare/Server Error (HTML Content Truncated)"

                logger.warning(
                    f"🔌 [EXCHANGE] {operation} failed ({error_msg}), retrying in {wait_time:.2f}s ({attempt + 1}/{max_retries})..."
                )
                await asyncio.sleep(wait_time)
            except Exception as e:
                # Non-network errors raise immediately (e.g. AuthenticationError)
                logger.error(
                    f"🔌 [EXCHANGE] {operation} failed with non-retriable error: {type(e).__name__}: {e}"
                )
                raise e

    async def _ensure_connected(self) -> None:
        """Ensure exchange is connected."""
        if not self._exchange:
            await self._execute_with_retry("connect", self.connect, max_retries=3)

    async def _warm_connection(self) -> bool:
        """
        SOTA Async Warmup: Use the SAME aiohttp session for priming.
        This guarantees TCP+SSL handshake occurs on the correct stack.
        """
        if not self._session:
            return False

        try:
            async with self._session.get(
                "https://api.kraken.com/0/public/Time",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                await resp.json()
                # server_time = result.get("result", {}).get("unixtime", "N/A")
                logger.info(f"🔥 Kraken {resp.status}")
                return resp.status == 200
        except Exception as e:
            logger.warning(f"🔥 [WARMUP] Failed: {type(e).__name__}: {e}")
            return False

    async def _ensure_connection_with_warmup(self, max_attempts: int = 3) -> bool:
        """
        Ensure connection with proper async warmup and session recovery.
        If warmup fails, recreate the session before retrying.
        """
        phi = 1.618

        for attempt in range(max_attempts):
            await self._ensure_connected()

            if await self._warm_connection():
                return True

            # Session may be in bad state - recreate it
            logger.warning(
                f"🔌 [EXCHANGE] Warmup failed, recreating session ({attempt + 1}/{max_attempts})..."
            )
            await self.close()
            await asyncio.sleep(phi**attempt)

        return False

    async def _ensure_markets(self) -> None:
        """Ensure markets are loaded for precision calculations."""
        await self._ensure_connected()

        # Double-check pattern (optimization)
        if self._markets_loaded:
            return

        async with self._markets_lock:
            # Re-check inside lock
            if self._markets_loaded:
                return

            # SOTA Async Warmup: Use the same aiohttp session to warm TCP+SSL.
            if not await self._ensure_connection_with_warmup():
                raise ConnectionError(
                    "Unable to establish stable Kraken connection after warmup"
                )

            try:
                self._markets_cache = await self._execute_with_retry(
                    "load_markets", self._exchange.load_markets
                )
                self._markets_loaded = True
                logger.debug(f"🔌 [EXCHANGE] Loaded {len(self._markets_cache)} markets")
            except Exception as e:
                logger.error(f"🔌 [EXCHANGE] Critical: Failed to load markets: {e}")
                raise e

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA FETCHING
    # ═══════════════════════════════════════════════════════════════════════════

    async def fetch_candles(
        self, pair: str, timeframe: str = "15m", limit: int = 100
    ) -> pl.DataFrame:
        """
        Fetch OHLCV data as Polars DataFrame.

        Args:
            pair: Trading pair (e.g., "BTC/EUR")
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, etc.)
            limit: Number of candles to fetch

        Returns:
            Polars DataFrame with columns: timestamp, open, high, low, close, volume
        """
        await self._ensure_connected()

        # SOTA v4.4: Guard against race condition during WebSocket reconnect
        if not self._exchange:
            logger.warning(
                f"🔌 [EXCHANGE] Fetch candles skipped - no connection for {pair}"
            )
            return pl.DataFrame(
                schema={
                    "timestamp": pl.Int64,
                    "open": pl.Float64,
                    "high": pl.Float64,
                    "low": pl.Float64,
                    "close": pl.Float64,
                    "volume": pl.Float64,
                }
            )

        # Normalize symbol (e.g. XDG -> DOGE)
        pair = self._normalize_pair(pair)

        try:
            ohlcv = await self._exchange.fetch_ohlcv(pair, timeframe, limit=limit)
            if not ohlcv:
                return pl.DataFrame()

            return pl.DataFrame(
                ohlcv,
                schema=["timestamp", "open", "high", "low", "close", "volume"],
                orient="row",
            )
        except Exception as e:
            error_msg = str(e).lower()
            # Detect pairs with no OHLCV data (not a network error):
            # - "does not have market symbol" = CCXT error
            # - "unknown asset pair" = Kraken API error
            no_ohlcv_patterns = (
                "does not have market symbol",
                "unknown asset pair",
            )
            if any(p in error_msg for p in no_ohlcv_patterns):
                # Store in instance for caller to check (dedupe before logging)
                if not hasattr(self, "_no_ohlcv_pairs"):
                    self._no_ohlcv_pairs = set()
                if pair not in self._no_ohlcv_pairs:
                    logger.info(
                        f"🔌 [EXCHANGE] {pair} has NO OHLCV data (will be auto-blacklisted)"
                    )
                    self._no_ohlcv_pairs.add(pair)
            else:
                logger.error(f"🔌 [EXCHANGE] Fetch candles error {pair}: {e}")
            return pl.DataFrame(
                schema={
                    "timestamp": pl.Int64,
                    "open": pl.Float64,
                    "high": pl.Float64,
                    "low": pl.Float64,
                    "close": pl.Float64,
                    "volume": pl.Float64,
                }
            )

    async def fetch_tickers(self, symbols: List[str] = None) -> Dict[str, Dict]:
        """Fetch tickers (all or specific list)."""
        await self._ensure_connected()
        return await self._exchange.fetch_tickers(symbols)

    async def fetch_ticker(self, pair: str) -> Dict:
        """Fetch single ticker for a pair."""
        await self._ensure_connected()
        pair = self._normalize_pair(pair)
        return await self._exchange.fetch_ticker(pair)

    async def fetch_balance(self, asset: str = None) -> Dict[str, float]:
        """
        Fetch account balance.

        Args:
            asset: Specific asset (e.g., "EUR", "BTC"). If None, returns all.

        Returns:
            Dict with 'free', 'used', 'total' keys
        """
        # SOTA v4.5: Early exit if shutting down to prevent race conditions
        if self._is_shutting_down:
            return {"free": 0.0, "used": 0.0, "total": 0.0} if asset else {}

        await self._ensure_connected()

        # Ensure markets are loaded to prevent implicit loading failures during fetch_balance
        markets_ready = False
        try:
            if not self._markets_loaded:
                await self._ensure_markets()
            markets_ready = self._markets_loaded
        except Exception as e:
            logger.warning(
                f"🔌 [EXCHANGE] Market load failed ({e}), switching to fallback for balance check..."
            )
            # Do NOT try standard fetch_balance if markets failed, as it will trigger load_markets again.
            markets_ready = False

        if not markets_ready:
            balance = await self._fetch_balance_fallback()
        else:
            balance = {}
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    # Try standard CCXT fetch first
                    async with self._api_lock:
                        balance = await self._exchange.fetch_balance()
                    break
                except Exception as e:
                    is_last = attempt == max_retries - 1
                    if is_last:
                        # Fallback if CCXT fails (e.g. BalanceEx error or persistent connectivity)
                        logger.warning(
                            f"🔌 [EXCHANGE] Standard fetch_balance failed ({type(e).__name__}: {e}), using fallback..."
                        )
                        balance = await self._fetch_balance_fallback()
                    else:
                        logger.debug(
                            f"🔌 [EXCHANGE] fetch_balance retry {attempt + 1}/{max_retries}..."
                        )
                        await asyncio.sleep(0.5)

        try:
            if asset:
                return {
                    "free": balance.get("free", {}).get(asset, 0.0),
                    "used": balance.get("used", {}).get(asset, 0.0),
                    "total": balance.get("total", {}).get(asset, 0.0),
                }
            return balance
        except Exception as e:
            logger.error(f"🔌 [EXCHANGE] Balance processing error: {e}")
            return {"free": 0.0, "used": 0.0, "total": 0.0} if asset else {}

    async def _fetch_balance_fallback(self) -> Dict:
        """
        Fallback implementation using raw private_post_balance.
        Bypasses 'BalanceEx' errors in recent CCXT versions.
        """
        try:
            # 1. Fetch Raw Balance (Total only) with retry
            response = await self._fetch_raw_balance_with_retry()
            if not response or "result" not in response:
                return {}

            raw_balances = response["result"]

            # 2. Construct CCXT-like structure
            result = {"info": response, "free": {}, "used": {}, "total": {}}

            # NOTE: We cannot easily calculate 'used' without fetching all open orders.
            # For resilience, we set used=0 and free=total in this fallback.
            # Ideally we would fetch_open_orders() but that might double the API load.

            for raw_asset, amount_str in raw_balances.items():
                amount = float(amount_str)
                if amount > 0:
                    asset = self._normalize_asset_name(raw_asset)

                    result["total"][asset] = amount
                    result["used"][asset] = 0.0  # Approximation
                    result["free"][asset] = amount

                    result[asset] = {"free": amount, "used": 0.0, "total": amount}

            return result
        except Exception as e:
            logger.error(
                f"🔌 [EXCHANGE] Fallback balance fetch failed: {type(e).__name__}: {e}"
            )
            return {}

    async def _fetch_raw_balance_with_retry(self) -> Dict:
        """Execute private_post_balance with retry."""
        # SOTA v4.5: Don't attempt emergency connect if shutting down
        if self._is_shutting_down:
            return {}

        if not self._exchange:
            try:
                logger.warning(
                    "🔌 [EXCHANGE] Fallback found no active exchange, attempting emergency connect..."
                )
                await self.connect()
            except Exception as e:
                logger.error(f"🔌 [EXCHANGE] Fallback connect failed: {e}")
                return {}

        if not self._exchange:
            return {}

        async with self._api_lock:
            return await self._execute_with_retry(
                "fallback_balance", self._exchange.private_post_balance
            )

    def _normalize_asset_name(self, asset: str) -> str:
        """
        Normalize asset names (handle Kraken suffixes).

        Examples:
        - XXBT -> BTC
        - XBT.M -> BTC
        - XBT.S -> BTC
        - ZEUR -> EUR
        """
        # Remove suffixes
        base = asset.split(".")[0]

        # Handle legacy prefixes
        if len(base) == 4 and (base.startswith("X") or base.startswith("Z")):
            base = base[1:]

        # Specific mappings
        if base == "XBT":
            return "BTC"
        if base == "XDG":
            return "DOGE"

        return base

    async def fetch_all_balances(self) -> Dict[str, Dict]:
        """
        Fetch all non-zero balances with EUR values, aggregated by asset.
        SOTA OPTIMIZATION: BATCH Price Fetching (One Shot).

        Returns:
            Dict[symbol, {total, free, used, value_eur, price}]
        """
        await self._ensure_connected()
        balances = {}

        try:
            # Use our robust fetch_balance (with fallback) instead of direct CCXT call
            full_balance = await self.fetch_balance()

            # 1. First pass: Aggregate by normalized asset
            raw_balances = {}  # normalized_asset -> {'total': 0, 'free': 0, 'used': 0}

            for symbol, data in full_balance.items():
                if symbol in ["info", "timestamp", "datetime", "free", "used", "total"]:
                    continue

                # specific validation for data structure
                if not isinstance(data, dict):
                    continue

                total = data.get("total", 0)
                if total > 0:
                    norm_asset = self._normalize_asset_name(symbol)

                    if norm_asset not in raw_balances:
                        raw_balances[norm_asset] = {
                            "total": 0.0,
                            "free": 0.0,
                            "used": 0.0,
                        }

                    raw_balances[norm_asset]["total"] += total
                    raw_balances[norm_asset]["free"] += data.get("free", 0)
                    raw_balances[norm_asset]["used"] += data.get("used", 0)

            # 2. Second pass: Batch Fetch Prices
            pairs_to_fetch = []
            asset_to_pair = {}  # asset -> pair

            for asset in raw_balances.keys():
                if asset == "EUR":
                    continue
                pair = f"{asset}/EUR"
                pairs_to_fetch.append(pair)
                asset_to_pair[asset] = pair

            # SOTA BATCH CALL
            tickers = {}
            if pairs_to_fetch:
                try:
                    logger.debug(
                        f"🔌 [EXCHANGE] Batch fetching prices for {len(pairs_to_fetch)} assets..."
                    )
                    tickers = await self.fetch_tickers(pairs_to_fetch)
                except Exception as e:
                    logger.warning(
                        f"🔌 [EXCHANGE] Batch fetch failed ({e}), falling back to serial..."
                    )

            # 3. Third pass: Calculate EUR values
            for asset, data in raw_balances.items():
                price = 0.0
                value_eur = 0.0

                if asset == "EUR":
                    price = 1.0
                    value_eur = data["total"]
                else:
                    pair = asset_to_pair.get(asset)
                    # Try batch result first
                    if pair and pair in tickers:
                        price = tickers[pair].get("last")
                        if price is None:
                            price = 0.0
                    elif pair:
                        # Fallback serial if batch missed/failed
                        try:
                            t = await self.fetch_ticker(pair)
                            price = t.get("last")
                            if price is None:
                                price = 0.0
                        except Exception:
                            price = 0.0

                    value_eur = data["total"] * price

                balances[asset] = {
                    "total": data["total"],
                    "free": data["free"],
                    "used": data["used"],
                    "value_eur": value_eur,
                    "price": price,
                }

            # Ensure BTC_TOTAL exists (as requested by User) concept
            if "BTC" in balances:
                balances["BTC_TOTAL"] = balances["BTC"].copy()

            return balances
        except Exception as e:
            logger.error(f"🔌 [EXCHANGE] Fetch all balances error: {e}")
            return {}

    async def get_daily_stats(self) -> Dict[str, Any]:
        """
        Get daily trading statistics (PnL, Wins/Losses, Volume).
        Uses a simple TTL cache (5 minutes).
        """
        import time

        # Check cache (5 minutes TTL)
        now = time.time()
        if hasattr(self, "_daily_stats_cache"):
            cached_data, cached_time = self._daily_stats_cache
            if now - cached_time < 300:  # 300 seconds = 5 min
                return cached_data

        await self._ensure_connected()

        stats = {
            "realized_pnl": 0.0,
            "wins": 0,
            "losses": 0,
            "volume": 0.0,
            "period": "24h",
        }

        try:
            # Fetch trades for last 24h
            since = int((now - 86400) * 1000)
            trades = await self._exchange.fetch_my_trades(since=since)

            if not trades:
                self._daily_stats_cache = (stats, now)
                return stats

            pair_stats = {}  # pair -> {'buy_cost', 'sell_cost', 'sells'}
            total_volume = 0.0
            total_fees = 0.0

            for trade in trades:
                pair = trade["symbol"]
                cost = trade["cost"]  # amount * price
                side = trade["side"]
                fee = trade["fee"]["cost"] if trade.get("fee") else 0

                total_volume += cost
                total_fees += fee

                if pair not in pair_stats:
                    pair_stats[pair] = {"buy_cost": 0.0, "sell_cost": 0.0, "sells": 0}

                if side == "buy":
                    pair_stats[pair]["buy_cost"] += cost
                elif side == "sell":
                    pair_stats[pair]["sell_cost"] += cost
                    pair_stats[pair]["sells"] += 1

            # Calculate PnL (Cash Flow)
            total_sell_value = sum(p["sell_cost"] for p in pair_stats.values())
            total_buy_value = sum(p["buy_cost"] for p in pair_stats.values())

            stats["realized_pnl"] = total_sell_value - total_buy_value - total_fees
            stats["volume"] = total_volume

            # Calculate Wins/Losses (Per pair daily outcome)
            for data in pair_stats.values():
                if data["sells"] > 0:
                    net = data["sell_cost"] - data["buy_cost"]
                    if net > 0:
                        stats["wins"] += 1
                    else:
                        stats["losses"] += 1

            # Update cache
            self._daily_stats_cache = (stats, now)

        except Exception as e:
            logger.error(f"📊 [STATS] Error calculating daily stats: {e}")

        return stats

    # ═══════════════════════════════════════════════════════════════════════════
    # MARKET LIMITS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_limits(self, pair: str) -> Dict:
        """
        Get trading limits for a pair.

        Returns:
            {min_amount, min_cost, max_amount, price_precision, amount_precision}
        """
        pair = self._normalize_pair(pair)

        if pair in self._limits_cache:
            return self._limits_cache[pair]

        await self._ensure_markets()

        if pair in self._markets_cache:
            market = self._markets_cache[pair]
            limits = {
                "min_amount": market["limits"]["amount"]["min"] or 0.0001,
                "min_cost": market["limits"]["cost"]["min"]
                if market["limits"].get("cost")
                else 5.0,
                "max_amount": market["limits"]["amount"]["max"],
                "price_precision": market["precision"]["price"],
                "amount_precision": market["precision"]["amount"],
            }
            self._limits_cache[pair] = limits
            return limits

        return {"min_amount": 0.0001, "min_cost": 5.0, "max_amount": None}

    async def can_trade(
        self, pair: str, amount: float, price: float
    ) -> Tuple[bool, str]:
        """
        Check if trade meets minimum requirements.

        Returns:
            (can_trade, reason)
        """
        pair = self._normalize_pair(pair)
        limits = await self.get_limits(pair)

        if amount < limits["min_amount"]:
            return False, f"Amount {amount} < min {limits['min_amount']}"

        value = amount * price
        if value < limits["min_cost"]:
            return False, f"Value {value:.2f}€ < min {limits['min_cost']}€"

        return True, "OK"

    async def get_trading_fee(self, pair: str, maker: bool = False) -> float:
        """
        Get trading fee for a pair.

        Args:
            pair: Trading pair
            maker: True for maker fee, False for taker fee

        Returns:
            Fee as decimal (e.g., 0.0026 for 0.26%)
        """
        await self._ensure_markets()
        pair = self._normalize_pair(pair)

        try:
            if pair in self._markets_cache:
                market = self._markets_cache[pair]
                return market.get("maker" if maker else "taker", ESTIMATED_FEES)
        except Exception:
            pass

        return ESTIMATED_FEES

    # ═══════════════════════════════════════════════════════════════════════════
    # ORDER EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════

    async def _create_order_locked(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: float = None,
        params: dict = None,
    ):
        """
        SOTA v4.6: Create order with nonce protection lock.

        Wraps CCXT create_order with asyncio.Lock to prevent
        EAPI:Invalid nonce errors from parallel authenticated requests.
        """
        async with self._api_lock:
            return await self._exchange.create_order(
                symbol, type, side, amount, price, params=params or {}
            )

    async def execute_order(
        self,
        pair: str,
        side: str,
        amount: Optional[float],
        price: float = None,
        cost: float = None,
        stop_loss_price: float = None,
        leverage: int = None,
        post_only: bool = False,
    ) -> OrderResult:
        """
        Execute a basic order (limit if price provided, market otherwise).
        SOTA v5.0: Supports Leverage (Margin).
        SOTA v5.16: Supports Cost-based Market Orders (Auto-calculate amount).
        """
        await self._ensure_connected()
        pair = self._normalize_pair(pair)

        # Build params
        params = {}
        if leverage:
            params["leverage"] = leverage
        if post_only:
            params["post_only"] = True

        try:
            # SOTA v5.16: Handle Cost-Based Orders (e.g. Cagnotte)
            if amount is None and cost is not None:
                # We must calculate amount based on current price
                ticker = await self.fetch_ticker(pair)
                current_price = ticker["ask"] if side == "buy" else ticker["bid"]
                if current_price > 0:
                    amount = cost / current_price
                    # Apply precision immediately to avoid "Invalid arguments"
                    amount = float(self._exchange.amount_to_precision(pair, amount))
                    logger.debug(f"🔌 [ORDER] Cost {cost}€ -> {amount} {pair} @ {current_price}")
                else:
                    return OrderResult(success=False, message="Price fetch failed for cost calc")

            order_type = "limit" if price else "market"

            if price:
                result = await self._create_order_locked(
                    pair, order_type, side, amount, price, params=params
                )
            else:
                # Market order
                result = await self._create_order_locked(
                    pair, order_type, side, amount, params=params
                )

            logger.success(f"🔌 [ORDER] {side.upper()} {pair}: {result['id']}")
            return OrderResult(
                success=True,
                message="Order executed",
                order_id=result["id"],
                filled_price=result.get("average") or result.get("price"),
                filled_amount=result.get("filled", amount),
                raw=result,
            )
        except ccxt.InsufficientFunds as e:
            return OrderResult(success=False, message=f"Insufficient funds: {e}")
        except ccxt.NetworkError as e:
            return OrderResult(success=False, message=f"Network error: {e}")
        except Exception as e:
            return OrderResult(success=False, message=f"Execution failed: {e}")

    async def execute_smart(
        self,
        pair: str,
        side: str,
        amount: float = None,
        cost: float = None,
        stop_loss_price: float = None,
        post_only: bool = False,
    ) -> OrderResult:
        """
        SOTA Execution: Limit-then-Market fallback with OTO Stop Loss.

        Args:
            pair: Trading pair (e.g., "BTC/EUR")
            side: 'buy' or 'sell'
            amount: Asset amount (for sell) or None if using cost
            cost: EUR amount to spend (for buy) or None if using amount
            stop_loss_price: Optional server-side SL price (for buys)
            post_only: If True, fail if order would execute immediately (Maker only)

        Returns:
            OrderResult with execution details
        """
        await self._ensure_connected()
        await self._ensure_markets()
        pair = self._normalize_pair(pair)

        try:
            # DRY RUN CHECK
            if TRADER_DRY_RUN:
                logger.warning(
                    f"🔌 [DRY RUN] Would {side.upper()} {pair} cost={cost} amount={amount}"
                )
                return OrderResult(
                    success=True,
                    message="DRY RUN - Order simulated",
                    order_id="DRY_RUN",
                    filled_price=0,
                    filled_amount=amount or 0,
                    raw={},
                )

            # 1. Get current price
            ticker = await self.fetch_ticker(pair)
            price = ticker["ask"] if side == "buy" else ticker["bid"]

            # 2. Calculate amount if cost provided
            if side == "buy" and cost and not amount:
                amount = cost / price

            # 3. Spread protection
            spread = (
                (ticker["ask"] - ticker["bid"]) / ticker["bid"] if ticker["bid"] else 0
            )
            max_spread = SPREAD_EXCEPTIONS.get(pair, MAX_SPREAD_DEFAULT)
            if spread > max_spread:
                return OrderResult(
                    success=False,
                    message=f"Spread too high: {spread * 100:.2f}% > {max_spread * 100:.1f}%",
                )

            # 4. Build OTO params for server-side SL
            oto_params = self._build_oto_params(side, price, stop_loss_price)

            # 5. Apply precision
            amount = float(self._exchange.amount_to_precision(pair, amount))
            price = float(self._exchange.price_to_precision(pair, price))

            if "close" in oto_params and "price" in oto_params["close"]:
                oto_params["close"]["price"] = float(
                    self._exchange.price_to_precision(
                        pair, oto_params["close"]["price"]
                    )
                )

            # 6. Try LIMIT order first
            try:
                # Add flags if post_only
                if post_only:
                    oto_params["flags"] = "post"

                order = await self._create_order_locked(
                    pair, "limit", side, amount, price, params=oto_params
                )
                logger.success(
                    f"🔌 [LIMIT] {side.upper()} {pair} @ {price} (Post: {post_only})"
                )
                return OrderResult(
                    success=True,
                    message="Limit order executed",
                    order_id=order["id"],
                    filled_price=price,
                    filled_amount=amount,
                    raw=order,
                )
            except (ccxt.OrderImmediatelyFillable, ccxt.InvalidOrder) as e:
                # Catch specific Post-Only rejection
                if post_only and "Post only" in str(
                    e
                ):  # Kraken often returns "Post only order cancelled" in message
                    logger.warning(f"🔌 [POST-ONLY] Skipped {pair} (Taker protection)")
                    return OrderResult(
                        success=False, message="Post-Only skipped (Taker protection)"
                    )

                # Normal fallback logic for other errors if NOT post-only enforcement
                if not post_only:
                    logger.warning(f"🔌 [LIMIT] Failed: {e}, trying MARKET fallback...")
                else:
                    # If post-only was requested but failed for another reason (or strictly immediately fillable)
                    # We should technically abort if we want to be STRICT about maker fees.
                    # But INVALID_ORDER (e.g. min size) should probably still fail.
                    if isinstance(
                        e, ccxt.OrderImmediatelyFillable
                    ) or "Post only" in str(e):
                        return OrderResult(
                            success=False,
                            message="Post-Only skipped (Taker protection)",
                        )
                    logger.warning(
                        f"🔌 [LIMIT] Failed: {e}, trying MARKET fallback (Post-only disabled on fallback)..."
                    )
            except ccxt.InsufficientFunds:
                # Try recovery for sells
                if side == "sell":
                    recovered = await self._try_recover_funds(pair, amount, price)
                    if recovered:
                        return recovered
                return OrderResult(success=False, message="Insufficient funds")

            # 7. MARKET fallback
            ticker = await self.fetch_ticker(pair)
            spread = (
                (ticker["ask"] - ticker["bid"]) / ticker["bid"] if ticker["bid"] else 0
            )
            if spread > max_spread:
                return OrderResult(
                    success=False,
                    message=f"Market fallback aborted: spread {spread * 100:.2f}%",
                )

            params = {}
            if side == "buy" and cost:
                params["cost"] = cost
                amount = None  # type: ignore[assignment]
            params.update(oto_params)

            order = await self._create_order_locked(
                pair, "market", side, amount, None, params=params
            )
            logger.success(f"🔌 [MARKET] {side.upper()} {pair} (fallback)")
            return OrderResult(
                success=True,
                message="Market order executed (fallback)",
                order_id=order["id"],
                filled_price=order.get("average") or ticker["last"],
                filled_amount=order.get("filled", amount),
                raw=order,
            )
        except Exception as e:
            logger.error(f"🔌 [SMART] Execution failed: {e}")
            return OrderResult(success=False, message=str(e))

    def _build_oto_params(
        self, side: str, entry_price: float, sl_price: float = None
    ) -> Dict:
        """Build OTO (One-Triggers-Other) params for server-side Stop Loss."""
        if side != "buy":
            return {}

        # Calculate SL if not provided
        if sl_price:
            final_sl = sl_price
        else:
            # SOTA: If no SL provided (e.g. Ghost Mode), we return EMPTY.
            # We do NOT auto-assign a default SL here anymore.
            # Caller must be explicit.
            return {}

        oto_params = {
            "close": {
                "ordertype": "stop-loss",
                "price": final_sl,
            }
        }

        logger.debug(f"🛡️ [OTO] Server-Side SL: {final_sl:.4f}")
        return oto_params

    async def _try_recover_funds(
        self, pair: str, amount: float, price: float
    ) -> Optional[OrderResult]:
        """
        Attempt to recover from insufficient funds for sells.

        Strategies:
        1. Cancel pending orders to unlock funds
        2. Resize to available balance (dust/rounding)
        """
        try:
            pair = self._normalize_pair(pair)
            base = pair.split("/")[0]
            balance = await self.fetch_balance(base)

            free = balance["free"]
            total = balance["total"]
            locked = total - free

            logger.info(f"🔧 [RECOVERY] {base}: Free={free:.6f} Locked={locked:.6f}")

            # Case 1: Funds locked in pending orders → Cancel and retry
            if free < amount and total >= amount * 0.99 and locked > 0:
                logger.warning(
                    f"🔧 [RECOVERY] Cancelling orders to unlock {locked:.6f} {base}..."
                )
                try:
                    await self.cancel_all_orders(pair)
                    order = await self._create_order_locked(
                        pair, "limit", "sell", amount, price
                    )
                    return OrderResult(
                        success=True,
                        message="Order executed after unlocking funds",
                        order_id=order["id"],
                        filled_price=price,
                        filled_amount=amount,
                        raw=order,
                    )
                except Exception as e:
                    logger.error(f"🔧 [RECOVERY] Unlock failed: {e}")

            # Case 2: Use available balance (dust/rounding)
            if 0 < free < amount and free >= 0.0001:
                logger.info(f"🔧 [RECOVERY] Resizing to available: {free:.6f}")
                order = await self._create_order_locked(
                    pair, "limit", "sell", free, price
                )
                return OrderResult(
                    success=True,
                    message=f"Order resized to {free:.6f}",
                    order_id=order["id"],
                    filled_price=price,
                    filled_amount=free,
                    raw=order,
                )
        except Exception as e:
            logger.error(f"🔧 [RECOVERY] Failed: {e}")

        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # ORDER MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_open_orders(self, pair: str = None) -> List[Dict]:
        """Get all open orders, optionally filtered by pair."""
        await self._ensure_connected()

        try:
            if pair:
                pair = self._normalize_pair(pair)
                async with self._api_lock:
                    return await self._exchange.fetch_open_orders(pair)
            async with self._api_lock:
                return await self._exchange.fetch_open_orders()
        except Exception as e:
            logger.error(f"🔌 [ORDERS] Fetch error: {e}")
            return []

    async def cancel_order(self, order_id: str, pair: str = None) -> bool:
        """Cancel a specific order."""
        await self._ensure_connected()

        try:
            if pair:
                pair = self._normalize_pair(pair)
            async with self._api_lock:
                await self._exchange.cancel_order(order_id, pair)
            logger.info(f"🔌 [ORDERS] Cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"🔌 [ORDERS] Cancel failed: {e}")
            return False

    async def cancel_all_orders(self, pair: str = None) -> int:
        """Cancel all open orders. Returns count of cancelled orders."""
        orders = await self.get_open_orders(pair)
        cancelled = 0

        for order in orders:
            if await self.cancel_order(order["id"], order.get("symbol")):
                cancelled += 1

        return cancelled


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION (replaces singleton)
# ═══════════════════════════════════════════════════════════════════════════════


def create_exchange(api_key: str = None, api_secret: str = None) -> KrakenExchange:
    """
    Factory function to create a KrakenExchange instance.

    Args:
        api_key: Optional custom API key
        api_secret: Optional custom API secret

    Returns:
        New KrakenExchange instance
    """
    return KrakenExchange(api_key, api_secret)


# Legacy compatibility
def calculate_stop_loss_price(entry_price: float, sl_pct: float = None) -> float:
    """Calculate stop loss price."""
    if sl_pct is not None:
        pct = sl_pct
    else:
        strategy = TraderConfig.load().get_strategy()
        pct = strategy.stop_loss
    return entry_price * (1 + pct)


async def get_minimum_entry_cost(exchange: KrakenExchange, pair: str) -> float:
    """Get minimum entry cost for a pair."""
    limits = await exchange.get_limits(pair)
    return limits.get("min_cost", 5.0)


async def can_sell_position(
    exchange: KrakenExchange, pair: str, amount: float, price: float
) -> Tuple[bool, str]:
    """
    Check if a position can be sold (above minimum order size).

    Returns:
        (can_sell, reason)
    """
    from jobs.trader.config import FORBIDDEN_SELL_ASSETS

    # Check forbidden assets first
    asset = pair.split("/")[0] if "/" in pair else pair
    if asset in FORBIDDEN_SELL_ASSETS:
        return False, f"🚫 {asset} is SACRED - selling forbidden"

    limits = await exchange.get_limits(pair)
    value_eur = amount * price

    # Check minimum cost (EUR value)
    if value_eur < limits.get("min_cost", 5.0):
        return False, f"⚠️ Value {value_eur:.2f}€ < min {limits.get('min_cost', 5.0)}€"

    # Check minimum amount
    if amount < limits.get("min_amount", 0.0001):
        return False, f"⚠️ Amount {amount} < min {limits.get('min_amount', 0.0001)}"

    return True, "✅ Can sell"


async def check_position_near_minimum(
    exchange: KrakenExchange, pair: str, amount: float, price: float
) -> Dict:
    """
    Check if a position is approaching minimum sell threshold.

    Returns:
        {is_near_min, value_eur, min_cost, buffer_pct}
    """
    limits = await exchange.get_limits(pair)
    value_eur = amount * price
    min_cost = limits.get("min_cost", 5.0)

    # Calculate buffer percentage
    buffer_pct = ((value_eur - min_cost) / min_cost * 100) if min_cost > 0 else 100

    return {
        "pair": pair,
        "value_eur": value_eur,
        "min_cost": min_cost,
        "buffer_pct": buffer_pct,
        "is_near_min": buffer_pct < 20,
        "is_unsellable": value_eur < min_cost,
        "recommendation": "SELL_NOW"
        if 0 < buffer_pct < 20
        else ("DUST" if buffer_pct <= 0 else "OK"),
    }


async def sweep_dust(
    exchange: KrakenExchange, threshold_eur: float = 1.0, dry_run: bool = True
) -> List[Dict]:
    """
    Sweep dust positions by selling them.

    Args:
        threshold_eur: Positions below this value are considered dust
        dry_run: If True, only report what would be swept

    Returns:
        List of swept positions with results
    """
    await exchange._ensure_connected()
    balances = await exchange.fetch_all_balances()

    results = []
    for asset, data in balances.items():
        if asset in ("EUR", "ZEUR") or data.get("total", 0) <= 0:
            continue

        pair = f"{asset}/EUR"
        amount = data.get("total", 0)

        # Get price
        try:
            ticker = await exchange.fetch_ticker(pair)
            price = ticker.get("last", 0)
        except Exception:
            continue

        value = amount * price if price else 0
        limits = await exchange.get_limits(pair)
        min_cost = limits.get("min_cost", 5.0)

        result = {
            "pair": pair,
            "amount": amount,
            "value_eur": value,
            "min_cost": min_cost,
            "action": "KEEP",
        }

        if value < min_cost:
            result["action"] = "UNSELLABLE"
            result["reason"] = f"Below min order {min_cost}€"
        elif value < threshold_eur:
            if dry_run:
                result["action"] = "WOULD_SWEEP"
            else:
                success, msg, _ = await exchange.execute_order(pair, "sell", amount)  # type: ignore[misc]
                result["action"] = "SWEPT" if success else "FAILED"
                result["result"] = msg

        if result["action"] != "KEEP":
            results.append(result)

    return results


async def get_dust_positions(
    exchange: KrakenExchange, threshold_eur: float = 1.0
) -> List[Dict]:
    """
    Find positions below dust threshold.

    Returns:
        List of dust positions [{symbol, amount, value_eur}]
    """
    await exchange._ensure_connected()
    balances = await exchange.fetch_all_balances()
    dust = []

    for asset, data in balances.items():
        if asset in ("EUR", "ZEUR", "BTC"):  # Never dust BTC
            continue

        # Get price
        pair = f"{asset}/EUR"
        try:
            ticker = await exchange.fetch_ticker(pair)
            value_eur = data.get("total", 0) * ticker.get("last", 0)
        except Exception:
            continue

        if 0 < value_eur < threshold_eur:
            dust.append(
                {
                    "symbol": asset,
                    "amount": data.get("total", 0),
                    "value_eur": value_eur,
                }
            )

    return dust


async def discover_orphan_positions(
    exchange: KrakenExchange, known_positions: List[str]
) -> List[Dict]:
    """
    Discover positions on Kraken not tracked by Trinity.

    Returns:
        List of orphan positions with discovery price
    """
    await exchange._ensure_connected()
    balances = await exchange.fetch_all_balances()
    orphans = []

    for asset, data in balances.items():
        if asset in ("EUR", "ZEUR", "BTC"):
            continue

        pair = f"{asset}/EUR"

        if pair not in known_positions and data.get("total", 0) > 0:
            try:
                ticker = await exchange.fetch_ticker(pair)
                value_eur = data.get("total", 0) * ticker.get("last", 0)

                if value_eur > 0.5:
                    orphans.append(
                        {
                            "pair": pair,
                            "symbol": asset,
                            "amount": data.get("total", 0),
                            "value_eur": value_eur,
                            "discovery_price": ticker.get("last", 0),
                            "is_orphan": True,
                        }
                    )
            except Exception:
                continue

    return orphans


async def cancel_stale_orders(
    exchange: KrakenExchange, max_age_minutes: int = 60
) -> List[Dict]:
    """Cancel orders older than specified age."""
    await exchange._ensure_connected()
    orders = await exchange.get_open_orders()
    cancelled = []

    import time

    now = time.time() * 1000  # ms
    max_age_ms = max_age_minutes * 60 * 1000

    for order in orders:
        order_time = order.get("timestamp", now)
        if now - order_time > max_age_ms:
            if await exchange.cancel_order(order["id"], order.get("symbol")):
                cancelled.append(order)

    return cancelled


async def check_duplicate_order(
    exchange: KrakenExchange,
    pair: str,
    side: str,
    amount: float,
    tolerance: float = 0.01,
) -> bool:
    """Check if a similar order already exists."""
    await exchange._ensure_connected()
    orders = await exchange.get_open_orders(pair)

    for order in orders:
        if order.get("side") == side:
            order_amount = order.get("amount", 0)
            if abs(order_amount - amount) / amount < tolerance:
                return True

    return False


async def fetch_order_book(
    exchange: KrakenExchange, pair: str, depth: int = 10
) -> Dict:
    """
    Fetch order book for slippage estimation.

    Returns:
        {bids, asks, spread, mid_price}
    """
    await exchange._ensure_connected()

    try:
        book = await exchange._exchange.fetch_order_book(pair, depth)

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2  # type: ignore[operator]
            spread = (best_ask - best_bid) / mid_price  # type: ignore[operator]
        else:
            best_bid = best_ask = mid_price = 0
            spread = 0

        return {
            "bids": bids,
            "asks": asks,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid_price,
            "spread": spread,
            "spread_pct": spread * 100,
        }
    except Exception as e:
        logger.error(f"🔌 [BOOK] Error: {e}")
        return {"bids": [], "asks": [], "spread": 0, "mid_price": 0}
