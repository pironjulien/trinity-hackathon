"""
JOBS/TRADER/DATA/HISTORY.PY
==============================================================================
MODULE: CHRONOS - Deep History Manager 🕐
PURPOSE: Manage millions of candles with DuckDB, incremental fetch, MTF support.
==============================================================================
"""

import asyncio
import polars as pl
from pathlib import Path
from typing import Optional, List, Dict
from corpus.soma.nerves import logger  # SOTA: DEBUG level
import os  # [NEW] For PID
import atexit
import signal

try:
    import fcntl

    HAS_FCNTL = True
except ImportError:
    fcntl = None  # type: ignore[assignment]
    HAS_FCNTL = False  # Windows fallback

try:
    import duckdb
except ImportError:
    duckdb = None
    logger.warning("🕐 DuckDB Missing")

from jobs.trader.config import (
    MEMORIES_DIR,
    F34,
    INV_PHI,
)


# Configuration
CHRONOS_DB = MEMORIES_DIR / "trader" / "chronos.duckdb"
DEEP_HISTORY_CANDLES = 46368  # F24 = ~1 year of 15m data
MIN_CANDLES_FOR_ANALYSIS = 100
AI_PROMPT_CANDLES = 10946  # F21 = ~115 days for AI

# Global Singleton
_CHRONOS_INSTANCE = None
_DEEP_HISTORY_READY = False  # Flag for optimizer to wait


def normalize_pair(pair: str) -> str:
    """
    Normalize pair format for consistent storage and lookup.

    WebSocket uses XBT/EUR, CCXT uses BTC/EUR.
    We standardize on the CCXT format (BTC, DOGE).
    """
    if not pair:
        return pair
    return pair.replace("XBT", "BTC").replace("XDG", "DOGE")


# Atexit handler to release lock on process exit (even SIGTERM)


def _cleanup_on_exit():
    """Release DuckDB lock on process exit."""
    global _CHRONOS_INSTANCE
    if _CHRONOS_INSTANCE:
        try:
            _CHRONOS_INSTANCE.close()
        except Exception:
            pass


atexit.register(_cleanup_on_exit)


# Also handle SIGTERM gracefully (NO SystemExit - breaks asyncio)
def _sigterm_handler(signum, frame):
    """Cleanup on SIGTERM without raising - let asyncio shutdown gracefully."""
    _cleanup_on_exit()
    # NOTE: Do NOT raise SystemExit here - it interrupts the asyncio event loop
    # and causes CancelledError cascades in Uvicorn/Starlette lifespan handlers.
    # The process will terminate naturally after cleanup.


try:
    signal.signal(signal.SIGTERM, _sigterm_handler)
except Exception:
    pass  # Windows or restricted environment


class Chronos:
    """
    Deep History Manager.

    Features:
    - Stores millions of candles in DuckDB
    - Incremental fetch (only new candles)
    - Multi-timeframe support (15m, 1h, 4h)
    - Pattern-ready data for AI analysis
    - Async I/O for non-blocking operations
    - Persistent Connection (Singleton) to avoid file locks
    """

    def __init__(self, db_path: Path = None):
        """
        Initialize Chronos.

        Args:
            db_path: Optional custom database path
        """
        self._db_path = str(db_path or CHRONOS_DB)
        self._initialized = False
        self.con = None
        self._lock_file = None
        self._lock_fd = None

        if duckdb is None:
            logger.warning("⚠️ Chronos Disabled")
            return

        # Ensure directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Acquire OS-level file lock to prevent inter-process conflicts
        if HAS_FCNTL:
            lock_path = Path(self._db_path).with_suffix(".lock")

            # [SOTA] Stale Lock Removal
            if lock_path.exists():
                try:
                    with open(lock_path, "r") as f:
                        pid = int(f.read().strip())

                    # Check if process is running
                    try:
                        os.kill(pid, 0)
                        logger.debug(f"🕐 [CHRONOS] Lock held by PID {pid}")
                    except OSError:
                        logger.info(f"♻️ Stale Lock PID {pid} - Cleared")
                        os.remove(lock_path)
                except Exception:
                    # Broken lock file content or permission issue
                    pass

            # [SOTA 2026] Re-entrant Lock Check (Singleton Resilience)
            try:
                if lock_path.exists():
                    with open(lock_path, "r") as f:
                        owner = f.read().strip()
                        if owner and int(owner) == os.getpid():
                            logger.warning(f"⚠️ Re-entrant Lock {owner}")
                            self._initialized = True
                            return
            except Exception:
                pass

            try:
                # [SOTA 2026] Fix: Use 'a+' to avoid truncating file before lock
                self._lock_fd = open(lock_path, "a+")

                # Try non-blocking lock
                if HAS_FCNTL:
                    fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Now we own the lock, we can write our PID
                self._lock_fd.seek(0)
                self._lock_fd.truncate()
                self._lock_fd.write(f"{os.getpid()}")
                self._lock_fd.flush()
                self._lock_file = lock_path
            except (IOError, OSError):
                # Another process holds the lock
                if self._lock_fd:
                    self._lock_fd.close()
                    self._lock_fd = None

                # Try to read who has it
                owner = "UNKNOWN"
                try:
                    with open(lock_path, "r") as f:
                        owner = f.read().strip()
                except Exception:
                    pass

                logger.warning(f"⚠️ DB Locked by {owner}")
                self._initialized = False
                return

        # Retry with exponential backoff for transient locks
        max_retries = 3
        base_delay = 0.5  # seconds

        for attempt in range(max_retries):
            try:
                # Persistent Connection (DuckDB has WAL enabled by default)
                self.con = duckdb.connect(self._db_path)
                self._ensure_tables()
                self._initialized = True

                # SOTA v5.6: Set flag if we already have data (persistence!)
                global _DEEP_HISTORY_READY
                stats = self.get_stats()
                if stats["total_candles"] > 10000:  # Significant data exists
                    _DEEP_HISTORY_READY = True
                    logger.success(
                        f"✅ Chronos Ready ({stats['total_candles']}c/{stats['pairs']}p)"
                    )
                else:
                    logger.success("✅ Chronos Ready (cold start)")
                return  # Success - exit __init__
            except Exception as e:
                if "lock" in str(e).lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)  # 0.5, 1.0, 2.0
                        logger.debug(
                            f"🕐 [CHRONOS] DB locked, retry {attempt + 1}/{max_retries} in {delay}s..."
                        )
                        import time

                        time.sleep(delay)
                        continue
                    # Final attempt failed - try read-only fallback
                    try:
                        self.con = duckdb.connect(self._db_path, read_only=True)
                        self._initialized = True
                        logger.warning("⚠️ Chronos Read-Only")
                        return
                    except Exception:
                        self._release_lock()
                        logger.warning("⚠️ Chronos Disabled")
                        self._initialized = False
                        return
                else:
                    self._release_lock()
                    logger.error("🕐 Connection Error")
                    self._initialized = False
                    return

    def _release_lock(self):
        """Release OS-level file lock."""
        if self._lock_fd:
            try:
                if HAS_FCNTL and fcntl is not None:
                    fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
                self._lock_fd.close()
                # Remove file only if we own it
                if self._lock_file and self._lock_file.exists():
                    try:
                        os.remove(self._lock_file)
                    except OSError:
                        pass
            except Exception:
                pass
            finally:
                self._lock_fd = None

    def close(self):
        """Close the database connection."""
        global _CHRONOS_INSTANCE
        if self.con:
            try:
                self.con.close()
                self.con = None
                self._initialized = False
                logger.debug("[CHRONOS] Connection closed")
            except Exception:
                logger.error("🕐 Close Error")
            finally:
                self._release_lock()
                if _CHRONOS_INSTANCE is self:
                    _CHRONOS_INSTANCE = None

    def _get_connection(self):
        """Get DuckDB cursor from persistent connection."""
        if not self.con:
            return None
        try:
            return self.con.cursor()
        except Exception:
            return None

    def _ensure_tables(self) -> None:
        """Create tables if not exist."""
        try:
            con = self._get_connection()
            if not con:
                return

            con.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    pair VARCHAR,
                    timeframe VARCHAR,
                    timestamp BIGINT,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    PRIMARY KEY (pair, timeframe, timestamp)
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_candles_pair_tf_ts 
                ON candles (pair, timeframe, timestamp)
            """)

            # Trades Table (Ticks)
            con.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    pair VARCHAR,
                    price DOUBLE,
                    volume DOUBLE,
                    side VARCHAR,
                    timestamp BIGINT
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_pair_ts
                ON trades (pair, timestamp)
            """)

            # Note: We do NOT close the connection here if it's the main self.con
            # But since _get_connection returns a cursor, we should close the cursor.
            con.close()

            # [SOTA 2026] Enforce Unique Constraint on Trades (Migration)
            self._ensure_trades_uniqueness()

            # [SOTA 2026] Normalize pair format (XBT→BTC, XDG→DOGE)
            self._migrate_pair_format()

        except Exception as e:
            logger.warning(f"🕐 Table Warn: {e}")

    def _ensure_trades_uniqueness(self):
        """Migration: Ensure trades table has unique index, dedupe if needed."""
        try:
            con = self._get_connection()
            if not con:
                return

            # Try creating index directly
            try:
                con.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_unique 
                    ON trades (pair, timestamp, price, volume, side)
                """)
            except Exception:
                logger.warning("🕐 Deduping Trades")

                # Heavy Migration: Dedupe
                con.execute("BEGIN TRANSACTION")
                con.execute("""
                    CREATE TABLE IF NOT EXISTS trades_temp AS 
                    SELECT DISTINCT * FROM trades
                """)
                con.execute("DROP TABLE trades")
                con.execute("ALTER TABLE trades_temp RENAME TO trades")

                # Recreate indices
                con.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_pair_ts
                    ON trades (pair, timestamp)
                """)
                con.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_unique 
                    ON trades (pair, timestamp, price, volume, side)
                """)
                con.execute("COMMIT")
                logger.success("✅ Trades Deduped")

            con.close()
        except Exception as e:
            logger.error(f"🕐 Unique Fail: {e}")

    def _migrate_pair_format(self) -> None:
        """
        Migration: Normalize pair names (XBT→BTC, XDG→DOGE).

        This ensures all pairs are stored in CCXT format for consistent lookups.
        """
        try:
            con = self._get_connection()
            if not con:
                return

            # Check if migration needed
            result = con.execute("""
                SELECT COUNT(*) FROM candles 
                WHERE pair LIKE '%XBT%' OR pair LIKE '%XDG%'
            """).fetchone()

            xbt_count = result[0] if result else 0

            if xbt_count > 0:
                logger.info(f"🕐 [CHRONOS] Migrating {xbt_count:,} XBT/XDG pairs...")

                # Update candles
                con.execute("""
                    UPDATE candles 
                    SET pair = REPLACE(REPLACE(pair, 'XBT', 'BTC'), 'XDG', 'DOGE')
                    WHERE pair LIKE '%XBT%' OR pair LIKE '%XDG%'
                """)

                # Update trades
                con.execute("""
                    UPDATE trades 
                    SET pair = REPLACE(REPLACE(pair, 'XBT', 'BTC'), 'XDG', 'DOGE')
                    WHERE pair LIKE '%XBT%' OR pair LIKE '%XDG%'
                """)

                logger.success(f"✅ Migrated {xbt_count:,} pairs to CCXT format")

            con.close()
        except Exception as e:
            logger.warning(f"🕐 Migration Warn: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_last_timestamp_sync(
        self, pair: str, timeframe: str = "15m"
    ) -> Optional[int]:
        """Get the most recent timestamp for a pair (Sync)."""
        if not self._initialized:
            return None

        pair = normalize_pair(pair)  # Normalize for consistent lookup

        try:
            con = self._get_connection()
            result = con.execute(
                """
                SELECT MAX(timestamp) FROM candles 
                WHERE pair = ? AND timeframe = ?
            """,
                [pair, timeframe],
            ).fetchone()
            con.close()
            return result[0] if result and result[0] else None
        except Exception:
            logger.error("🕐 Timestamp Error")
            return None

    async def get_last_timestamp(
        self, pair: str, timeframe: str = "15m"
    ) -> Optional[int]:
        """Get the most recent timestamp for a pair (Async)."""
        return await asyncio.to_thread(self._get_last_timestamp_sync, pair, timeframe)

    def _count_candles_sync(self, pair: str, timeframe: str = "15m") -> int:
        """Count stored candles for a pair (Sync)."""
        if not self._initialized:
            return 0
        pair = normalize_pair(pair)  # Normalize for consistent lookup

        try:
            con = self._get_connection()
            result = con.execute(
                """
                SELECT COUNT(*) FROM candles 
                WHERE pair = ? AND timeframe = ?
            """,
                [pair, timeframe],
            ).fetchone()
            con.close()
            return result[0] if result else 0
        except Exception:
            return 0

    async def count_candles(self, pair: str, timeframe: str = "15m") -> int:
        """Count stored candles for a pair (Async)."""
        return await asyncio.to_thread(self._count_candles_sync, pair, timeframe)

    def _get_candles_sync(
        self, pair: str, timeframe: str = "15m", limit: int = 1000
    ) -> pl.DataFrame:
        """
        Get candles from DuckDB as Polars DataFrame (Sync).
        """
        empty = pl.DataFrame(
            schema={
                "timestamp": pl.Int64,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Float64,
            }
        )

        if not self._initialized:
            return empty

        pair = normalize_pair(pair)  # Normalize for consistent lookup

        try:
            con = self._get_connection()
            if not con:
                logger.warning("🕐 [CHRONOS] No connection available for get_candles")
                return empty

            result = con.execute(
                """
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE pair = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                [pair, timeframe, limit],
            ).fetchall()

            con.close()

            if not result:
                return empty

            # Convert to DataFrame and reverse (oldest first)
            return pl.DataFrame(
                result,
                schema=["timestamp", "open", "high", "low", "close", "volume"],
                orient="row",
            ).reverse()

        except Exception:
            logger.error("🕐 Get Candles Error")
            return empty

    async def get_candles(
        self, pair: str, timeframe: str = "15m", limit: int = 1000
    ) -> pl.DataFrame:
        """
        Get candles from DuckDB as Polars DataFrame (Async).
        """
        return await asyncio.to_thread(self._get_candles_sync, pair, timeframe, limit)

    # ═══════════════════════════════════════════════════════════════════════════
    # STORAGE METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    async def fetch_and_store(
        self, exchange, pair: str, timeframe: str = "15m", target_candles: int = None
    ) -> int:
        """
        Fetch candles incrementally and store in DuckDB.

        Args:
            exchange: KrakenExchange instance
            pair: Trading pair
            timeframe: Candle timeframe
            target_candles: Target number of candles

        Returns:
            Number of new candles added
        """
        if not self._initialized or not exchange:
            return 0

        target_candles = target_candles or DEEP_HISTORY_CANDLES

        # Get current count and last timestamp
        current_count = await self.count_candles(pair, timeframe)
        last_ts = await self.get_last_timestamp(pair, timeframe)

        # Calculate how many to fetch
        needed = target_candles - current_count

        if needed <= 0 and last_ts:
            # Just update recent candles
            needed = 100
            since = last_ts
        elif last_ts:
            since = last_ts
        else:
            since = None

        logger.debug(
            f"🕐 [CHRONOS] {pair}: Have {current_count}, fetching {needed} more"
        )

        total_added = 0
        batch_size = min(1000, needed)

        try:
            while total_added < needed:
                # Fetch via exchange
                if hasattr(exchange, "fetch_candles"):
                    # KrakenExchange wrapper
                    df = await exchange.fetch_candles(pair, timeframe, limit=batch_size)
                    ohlcv = df.to_dicts() if not df.is_empty() else []
                    ohlcv = [
                        [
                            d["timestamp"],
                            d["open"],
                            d["high"],
                            d["low"],
                            d["close"],
                            d["volume"],
                        ]
                        for d in ohlcv
                    ]
                else:
                    # Direct CCXT
                    ohlcv = await exchange.fetch_ohlcv(
                        pair, timeframe, since=since, limit=batch_size
                    )

                if not ohlcv:
                    break

                # Store in DuckDB
                added = await self._store_candles(pair, timeframe, ohlcv)
                total_added += added

                # Update since for next batch
                if ohlcv:
                    since = ohlcv[-1][0] + 1

                # Stop if we got fewer than requested
                if len(ohlcv) < batch_size:
                    break

                # Prevent rate limiting
                await asyncio.sleep(INV_PHI)

            logger.debug(f"🕐 [CHRONOS] {pair}: Added {total_added} candles")
            return total_added

        except Exception:
            logger.error(f"🕐 Fetch Error {pair}")
            return total_added

    def _store_candles_sync(self, pair: str, timeframe: str, ohlcv: List) -> int:
        """Store candles in DuckDB with upsert (Sync)."""
        if not ohlcv or not self._initialized:
            return 0

        pair = normalize_pair(pair)  # Normalize for consistent storage

        try:
            con = self._get_connection()
            if not con:
                return 0

            # Prepare data
            data = [
                (pair, timeframe, c[0], c[1], c[2], c[3], c[4], c[5]) for c in ohlcv
            ]

            # Insert with conflict handling
            con.executemany(
                """
                INSERT OR REPLACE INTO candles 
                (pair, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                data,
            )

            con.close()
            return len(data)

        except Exception as e:
            logger.error(f"🕐 Store Error: {e}")
            return 0

    async def _store_candles(self, pair: str, timeframe: str, ohlcv: List) -> int:
        """Store candles in DuckDB with upsert (Async)."""
        return await asyncio.to_thread(self._store_candles_sync, pair, timeframe, ohlcv)

    async def store_from_df(self, pair: str, timeframe: str, df: pl.DataFrame) -> int:
        """
        Store candles from a Polars DataFrame (Async).

        Args:
            pair: Trading pair
            timeframe: Candle timeframe
            df: DataFrame with OHLCV columns

        Returns:
            Number of candles stored
        """
        if df.is_empty():
            return 0

        ohlcv = [
            [
                row["timestamp"],
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"],
            ]
            for row in df.to_dicts()
        ]
        return await self._store_candles(pair, timeframe, ohlcv)

    def _store_trades_sync(self, trades: List[Dict]) -> int:
        """Store batch of trades in DuckDB (Sync)."""
        if not trades or not self._initialized:
            return 0

        try:
            con = self._get_connection()
            if not con:
                return 0

            # Prepare data
            data = [
                (t["pair"], t["price"], t["volume"], t["side"], t["timestamp"])
                for t in trades
            ]

            con.executemany(
                """
                INSERT OR IGNORE INTO trades (pair, price, volume, side, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                data,
            )

            con.close()
            return len(data)

        except Exception as e:
            logger.error(f"🕐 Trades Store Error: {e}")
            return 0

    async def store_trade_batch(self, trades: List[Dict]) -> int:
        """Store batch of trades in DuckDB (Async)."""
        if not trades:
            return 0
        return await asyncio.to_thread(self._store_trades_sync, trades)

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCESSORS (API SUPPORT)
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_latest_price_sync(self) -> float:
        """Get latest BTC price (Sync)."""
        if not self._initialized:
            return 0.0

        try:
            con = self._get_connection()
            # Try to get latest close from candles first
            result = con.execute(
                "SELECT close FROM candles WHERE pair IN ('XBT/EUR', 'BTC/EUR') ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()

            # Fallback to trades if needed (optional, but keeping simple for now)

            con.close()
            return float(result[0]) if result else 0.0
        except Exception:
            return 0.0

    async def get_latest_price(self) -> float:
        """Get latest BTC price (Async)."""
        return await asyncio.to_thread(self._get_latest_price_sync)

    def _get_recent_trades_sync(self, limit: int = 50) -> List[Dict]:
        """Get recent trades for UI (Sync)."""
        if not self._initialized:
            return []

        try:
            con = self._get_connection()
            rows = con.execute(
                "SELECT pair, side, price, timestamp FROM trades ORDER BY timestamp DESC LIMIT ?",
                [limit],
            ).fetchall()
            con.close()

            # Format for UI
            trades = []
            from datetime import datetime

            for r in rows:
                trades.append(
                    {
                        "pair": r[0],
                        "side": r[1],
                        "price": r[2],
                        "time": datetime.fromtimestamp(r[3]).isoformat(),
                    }
                )
            return trades
        except Exception as e:
            logger.error(f"🕐 Trades Read Error: {e}")
            return []

    async def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent trades for UI (Async)."""
        return await asyncio.to_thread(self._get_recent_trades_sync, limit)

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict:
        """Get database statistics."""
        if not self._initialized:
            return {"pairs": 0, "total_candles": 0, "data": []}

        try:
            con = self._get_connection()

            pairs = con.execute("""
                SELECT pair, timeframe, COUNT(*) as count,
                       MIN(timestamp) as oldest, MAX(timestamp) as newest
                FROM candles
                GROUP BY pair, timeframe
            """).fetchall()

            con.close()

            return {
                "pairs": len(set(p[0] for p in pairs)),
                "total_candles": sum(p[2] for p in pairs),
                "data": [(p[0], p[1], p[2]) for p in pairs],
            }

        except Exception:
            logger.error("🕐 Stats Error")
            return {"pairs": 0, "total_candles": 0, "data": []}

    def clear(self, pair: str = None, timeframe: str = None) -> None:
        """
        Clear stored candles.

        Args:
            pair: Specific pair to clear (all if None)
            timeframe: Specific timeframe to clear (all if None)
        """
        if not self._initialized:
            return

        try:
            con = self._get_connection()

            if pair and timeframe:
                con.execute(
                    "DELETE FROM candles WHERE pair = ? AND timeframe = ?",
                    [pair, timeframe],
                )
            elif pair:
                con.execute("DELETE FROM candles WHERE pair = ?", [pair])
            else:
                con.execute("DELETE FROM candles")

            con.close()
            logger.info(f"🕐 Cleared {pair or 'all'}")
        except Exception:
            logger.error("🕐 Clear Error")


def create_history(db_path: Path = None) -> Chronos:
    """Factory function to create Chronos (Singleton)."""
    global _CHRONOS_INSTANCE
    if _CHRONOS_INSTANCE is None:
        _CHRONOS_INSTANCE = Chronos(db_path)
    return _CHRONOS_INSTANCE


async def initialize_deep_history(
    exchange, pairs: List[str], target: int = 10000
) -> Dict:
    """
    Initialize deep history for multiple pairs across multiple timeframes.

    Args:
        exchange: KrakenExchange instance
        pairs: List of pairs to initialize
        target: Target candles per pair per timeframe

    Returns:
        Stats dict
    """
    chronos = create_history()

    # Multi-timeframe support
    timeframes = ["15m", "1h", "4h"]

    # Limit pairs at startup (F34 = 34)
    startup_limit = min(F34, len(pairs))
    # total_ops = startup_limit * len(timeframes)  # Reserved for future progress tracking

    logger.info(f"🕐 Init {startup_limit}p×{len(timeframes)}TF")

    for pair in pairs[:startup_limit]:
        for tf in timeframes:
            tf_target = target if tf == "15m" else target // 4
            await chronos.fetch_and_store(exchange, pair, tf, tf_target)

    global _DEEP_HISTORY_READY
    _DEEP_HISTORY_READY = True
    stats = chronos.get_stats()
    logger.success(f"🕐 Ready {stats['total_candles']}c/{stats['pairs']}p")
    return stats


def is_deep_history_ready() -> bool:
    """Check if deep history initialization is complete."""
    return _DEEP_HISTORY_READY
