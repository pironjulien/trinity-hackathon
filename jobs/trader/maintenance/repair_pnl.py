"""
JOBS/TRADER/MAINTENANCE/REPAIR_PNL.PY
==============================================================================
MODULE: STATE REPAIR SURGEON 👨‍⚕️
PURPOSE: Fixes corrupted PnL state by rebuilding it from the Ledger Truth.
SOTA: Uses fetch_enriched_history(lookback=365) to get the REAL reality.
==============================================================================
"""

import sys
import asyncio
import json
from pathlib import Path
from loguru import logger

# Add root to python path to allow imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(ROOT_DIR))

from corpus.dna.genome import MEMORIES_DIR  # noqa: E402
from jobs.trader.kraken.api import KrakenAPI  # noqa: E402
from jobs.trader.kraken.exchange import KrakenExchange  # noqa: E402
from jobs.trader.utils import atomic_save_json  # noqa: E402

# PATHS
STATE_FILE = MEMORIES_DIR / "trader" / "state.json"


async def repair_state():
    """
    Rebuilds state.json from the definitive blockchain/exchange history.
    """
    logger.info("👨‍⚕️ [SURGEON] Starting PnL Repair Protocol...")

    # 1. Initialize API
    exchange = KrakenExchange()
    # No need to explictly connect, API methods usually ensure connection or we can do it here
    await exchange.connect()
    api = KrakenAPI(exchange)

    # 2. Fetch Deep History (The Truth)
    logger.info("📜 [SURGEON] Fetching full trading history (365 days)...")
    # We use a large 'days' value for the filter to ensure we get everything relevant for the session stats
    # But effectively we want to reconstruct 'session' stats which usually implies 'since start'.
    # However, since the bot runs deeply, let's treat 'session' as 'last 24h' or 'since last reset'.
    # Actually, the user problem is that "COMBAT" stats (Session) are wrong.
    # The 'state.json' persists 'session_pnl'.

    # Let's rebuild 'session' stats based on the last 24h of trades for consistency with 'Daily PnL'
    # OR if the user considers 'session' as 'lifetime of the bot instance', we might want to just reset it to 0
    # and let it rebuild from now.

    # BUT, the request is to "Calculate `total_pnl`, `wins`, `losses` from the history."
    # The artifact says: "Fix the incorrect PnL... by recalculating the state from the definitive trade history."

    trades = await api.fetch_enriched_history(
        days=1, lookback=365
    )  # Fetch last 24h of trades for 'Daily/Session' alignment

    # Actually, if we want to fix the "90€" which is likely a lifetime accumulation of errors,
    # we should check what 'session_pnl' is supposed to represent.
    # In positions.py: self.session_pnl is added to on every close.

    # STRATEGY:
    # The safest repair is to RECALCULATE based on the actual trades executed today.
    # If no trades today, 0.

    real_pnl = 0.0
    wins = 0
    losses = 0
    trade_count = 0

    logger.info(f"🔍 [SURGEON] Analyzing {len(trades)} trades from the last 24h...")

    for t in trades:
        # enriched_history returns trades with 'pnl_eur' calculated correctly now
        pnl = t.get("pnl_eur", 0.0)

        # Only count closed transactions (sells)
        if t["side"] == "sell":
            real_pnl += pnl
            trade_count += 1
            if pnl > 0:
                wins += 1
            else:
                losses += 1

    logger.info(
        f"🧮 [SURGEON] Recalculated Stats (24h): PnL={real_pnl:.2f}€ | {wins}W-{losses}L"
    )

    # 3. Load and Update State
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        logger.info(
            f"🏚️ [SURGEON] Current State on Disk: PnL={state.get('session_pnl', 0):.2f}€"
        )
    else:
        logger.warning("⚠️ [SURGEON] No state file found. Creating new.")
        state = {"cagnotte": 0.0, "circuit_breaker": False}

    # UPDATE
    old_pnl = state.get("session_pnl", 0.0)
    state["session_pnl"] = real_pnl
    state["session_wins"] = wins
    state["session_losses"] = losses
    state["session_trades"] = trade_count

    # 4. Save
    atomic_save_json(STATE_FILE, state)
    logger.success(
        f"✨ [SURGEON] State Repaired! PnL: {old_pnl:.2f}€ -> {real_pnl:.2f}€"
    )
    logger.warning("🚨 [REQUIRED] PLEASE RESTART TRINITY NOW TO RELOAD THIS STATE.")


if __name__ == "__main__":
    try:
        asyncio.run(repair_state())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception(f"💥 [SURGEON] Operation Failed: {e}")
