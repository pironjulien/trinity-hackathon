"""
JOBS/TRADER/DATA/INDICATORS.PY
==============================================================================
MODULE: TECHNICAL INDICATORS (Pure Math) ⚡
PURPOSE: High-performance vectorized indicators using Polars (Rust-based).
STATELESS: All functions are pure - no side effects, no state.
==============================================================================
"""

import polars as pl
from typing import Tuple, Optional, List


def to_polars(ohlcv_list: List) -> Optional[pl.DataFrame]:
    """
    Convert standard OHLCV list to Polars DataFrame.

    Args:
        ohlcv_list: List of [timestamp, open, high, low, close, volume]

    Returns:
        Polars DataFrame or None if input is empty
    """
    if not ohlcv_list:
        return None

    try:
        return pl.DataFrame(
            ohlcv_list,
            schema=["timestamp", "open", "high", "low", "close", "volume"],
            orient="row",
        )
    except Exception:
        return None


def calculate_rsi(df: pl.DataFrame, period: int = 14) -> pl.Series:
    """
    RSI (Relative Strength Index) using Wilder's Smoothing.

    Args:
        df: DataFrame with 'close' column
        period: RSI period (default: 14)

    Returns:
        Polars Series with RSI values
    """
    delta = df["close"].diff()
    up = delta.clip(lower_bound=0)
    down = delta.clip(upper_bound=0).abs()

    # Wilder's smoothing: alpha = 1 / period
    avg_gain = up.ewm_mean(com=period - 1, ignore_nulls=True)
    avg_loss = down.ewm_mean(com=period - 1, ignore_nulls=True)

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(
    df: pl.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[pl.Series, pl.Series, pl.Series]:
    """
    MACD (Moving Average Convergence Divergence).

    Args:
        df: DataFrame with 'close' column
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = df["close"].ewm_mean(span=fast, adjust=False)
    ema_slow = df["close"].ewm_mean(span=slow, adjust=False)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm_mean(span=signal, adjust=False)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger(
    df: pl.DataFrame, period: int = 20, std_dev: float = 2.0
) -> Tuple[pl.Series, pl.Series, pl.Series]:
    """
    Bollinger Bands.

    Args:
        df: DataFrame with 'close' column
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    sma = df["close"].rolling_mean(window_size=period)
    std = df["close"].rolling_std(window_size=period)

    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower


def calculate_atr(df: pl.DataFrame, period: int = 14) -> Tuple[pl.Series, pl.Series]:
    """
    ATR (Average True Range).

    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: ATR period (default: 14)

    Returns:
        Tuple of (atr, atr_percent)
    """
    lf = df.lazy()

    lf = lf.with_columns([pl.col("close").shift(1).alias("prev_close")])

    # True Range calculation
    lf = lf.with_columns(
        pl.max_horizontal(
            pl.col("high") - pl.col("low"),
            (pl.col("high") - pl.col("prev_close")).abs(),
            (pl.col("low") - pl.col("prev_close")).abs(),
        ).alias("tr")
    )

    # Wilder's Smoothing on TR
    lf = lf.with_columns(
        pl.col("tr").ewm_mean(com=period - 1, ignore_nulls=True).alias("atr")
    )

    lf = lf.with_columns(((pl.col("atr") / pl.col("close")) * 100).alias("atr_pct"))

    result = lf.collect()
    return result["atr"], result["atr_pct"]


def calculate_ema(df: pl.DataFrame, period: int = 50) -> pl.Series:
    """
    EMA (Exponential Moving Average).

    Args:
        df: DataFrame with 'close' column
        period: EMA period (default: 50)

    Returns:
        Polars Series with EMA values
    """
    return df["close"].ewm_mean(span=period, adjust=False)


def calculate_adx(df: pl.DataFrame, period: int = 14) -> pl.Series:
    """
    ADX (Average Directional Index).

    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: ADX period (default: 14)

    Returns:
        Polars Series with ADX values
    """
    lf = df.lazy()

    lf = lf.with_columns(
        [
            pl.col("high").shift(1).alias("prev_high"),
            pl.col("low").shift(1).alias("prev_low"),
            pl.col("close").shift(1).alias("prev_close"),
        ]
    )

    lf = lf.with_columns(
        [
            (pl.col("high") - pl.col("prev_high")).alias("up_move"),
            (pl.col("prev_low") - pl.col("low")).alias("down_move"),
        ]
    )

    # Directional Movement
    lf = lf.with_columns(
        [
            pl.when((pl.col("up_move") > pl.col("down_move")) & (pl.col("up_move") > 0))
            .then(pl.col("up_move"))
            .otherwise(0)
            .alias("plus_dm"),
            pl.when(
                (pl.col("down_move") > pl.col("up_move")) & (pl.col("down_move") > 0)
            )
            .then(pl.col("down_move"))
            .otherwise(0)
            .alias("minus_dm"),
        ]
    )

    # True Range
    lf = lf.with_columns(
        pl.max_horizontal(
            pl.col("high") - pl.col("low"),
            (pl.col("high") - pl.col("prev_close")).abs(),
            (pl.col("low") - pl.col("prev_close")).abs(),
        ).alias("tr")
    )

    # Smoothed values
    lf = lf.with_columns(
        [
            pl.col("plus_dm")
            .ewm_mean(com=period - 1, ignore_nulls=True)
            .alias("smooth_plus"),
            pl.col("minus_dm")
            .ewm_mean(com=period - 1, ignore_nulls=True)
            .alias("smooth_minus"),
            pl.col("tr").ewm_mean(com=period - 1, ignore_nulls=True).alias("smooth_tr"),
        ]
    )

    # Directional Indicators
    lf = lf.with_columns(
        [
            (100 * pl.col("smooth_plus") / pl.col("smooth_tr")).alias("plus_di"),
            (100 * pl.col("smooth_minus") / pl.col("smooth_tr")).alias("minus_di"),
        ]
    )

    # DX
    lf = lf.with_columns(
        pl.when((pl.col("plus_di") + pl.col("minus_di")) > 0)
        .then(
            100
            * (pl.col("plus_di") - pl.col("minus_di")).abs()
            / (pl.col("plus_di") + pl.col("minus_di"))
        )
        .otherwise(0.0)
        .alias("dx")
    )

    # ADX
    lf = lf.with_columns(
        pl.col("dx").ewm_mean(com=period - 1, ignore_nulls=True).alias("adx")
    )

    return lf.collect()["adx"]


def calculate_cvd(trades_df: pl.DataFrame) -> pl.DataFrame:
    """
    CVD (Cumulative Volume Delta).

    Measures buying vs selling pressure.

    Args:
        trades_df: DataFrame with 'side' and 'volume' columns

    Returns:
        DataFrame with added 'delta' and 'cvd' columns
    """
    return (
        trades_df.lazy()
        .with_columns(
            pl.when(pl.col("side") == "buy")
            .then(pl.col("volume"))
            .otherwise(-pl.col("volume"))
            .alias("delta")
        )
        .with_columns(pl.col("delta").cum_sum().alias("cvd"))
        .collect()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED INDICATORS
# ═══════════════════════════════════════════════════════════════════════════════


def calculate_fibonacci_zones(
    df: pl.DataFrame, lookback: int = 55
) -> Tuple[float, float, bool]:
    """
    Calculate Fibonacci retracement zones.

    Args:
        df: DataFrame with 'close' column
        lookback: Period to find high/low

    Returns:
        (fib_382, fib_618, in_zone)
    """
    closes = df["close"].to_list()[-lookback:]
    if len(closes) < lookback:
        return 0, 0, False

    high = max(closes)
    low = min(closes)
    diff = high - low

    fib_382 = high - (diff * 0.382)
    fib_618 = high - (diff * 0.618)

    current = closes[-1]
    in_zone = fib_618 <= current <= fib_382

    return fib_382, fib_618, in_zone


def calculate_volume_ratio(df: pl.DataFrame, lookback: int = 20) -> float:
    """
    Calculate current volume vs average ratio.

    Args:
        df: DataFrame with 'volume' column
        lookback: Period for average calculation

    Returns:
        Volume ratio (>1 = above average)
    """
    if df.height < lookback:
        return 1.0

    volumes = df["volume"].to_list()
    avg_volume = (
        sum(volumes[-lookback:-1]) / (lookback - 1) if lookback > 1 else volumes[-1]
    )
    current_volume = volumes[-1]

    return current_volume / avg_volume if avg_volume > 0 else 1.0


def detect_divergence(
    df: pl.DataFrame, rsi_series: pl.Series, lookback: int = 10
) -> Optional[str]:
    """
    Detect RSI divergence (bullish or bearish).

    Args:
        df: DataFrame with 'close' column
        rsi_series: Calculated RSI series
        lookback: Period to check for divergence

    Returns:
        "bullish", "bearish", or None
    """
    if df.height < lookback:
        return None

    prices = df["close"].to_list()[-lookback:]
    rsi = rsi_series.to_list()[-lookback:]

    # Bullish divergence: price making lower lows, RSI making higher lows
    if prices[-1] < prices[0] and rsi[-1] > rsi[0]:
        return "bullish"

    # Bearish divergence: price making higher highs, RSI making lower highs
    if prices[-1] > prices[0] and rsi[-1] < rsi[0]:
        return "bearish"

    return None
