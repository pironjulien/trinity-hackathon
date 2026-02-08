"""
JOBS/TRADER/KRAKEN/API.PY
==============================================================================
MODULE: KRAKEN RAW API (Earn + History + Ledger) 🔧
PURPOSE: Direct Kraken API calls for features not in CCXT.
==============================================================================
"""

from typing import Dict, List
import time
from datetime import datetime, timedelta
from corpus.soma.nerves import logger  # SOTA: DEBUG level

from jobs.trader.kraken.exchange import KrakenExchange


# Ledger types (Kraken mapping)
LEDGER_TYPES = {
    "trade": "Trade",
    "deposit": "Dépôt",
    "withdrawal": "Retrait",
    "transfer": "Transfert",
    "margin": "Margin",
    "rollover": "Rollover",
    "spend": "Dépense",
    "receive": "Réception",
    "settled": "Règlement",
    "staking": "Staking",
    "dividend": "Dividende",
}


class KrakenAPI:
    """
    Raw Kraken API for advanced operations.

    Features:
    - Earn (Staking) management
    - Trade history
    - Ledger access
    """

    def __init__(self, exchange: KrakenExchange):
        """
        Initialize with an exchange instance.

        Args:
            exchange: Connected KrakenExchange instance
        """
        self._exchange = exchange
        self._earn_cache = None
        self._earn_cache_time = 0

    # ═══════════════════════════════════════════════════════════════════════════
    # EARN (STAKING)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_earn_allocations(self) -> List[Dict]:
        """
        Get current Kraken Earn allocations.
        SOTA v5.1: Hybrid strategy (Allocations API + Balance Fallback)
        """
        # SOTA v5.3: LONG MEMORY Cache (24h TTL) - User Mandate
        # Earn data is stable. Don't spam API. 86400s = 1 day.
        if self._earn_cache and (time.time() - self._earn_cache_time < 86400):
            return self._earn_cache

        await self._exchange._ensure_connected()

        allocations = []

        # Strategy 1: The Modern "Earn" API
        try:
            # SOTA v5.0: Force hide_zero=False to debug
            params = {"converted_asset": "EUR", "hide_zero": False}
            response = await self._exchange._invoke_private(
                "private_post_earn_allocations", params=params
            )
            logger.debug(f"🎁 [EARN] API Raw: {response}")

            items = response.get("result", {}).get("items", [])
            for item in items:
                asset_code = item.get("native_asset") or item.get("asset")

                # SOTA v5.2: Correct JSON Path (amount_allocated -> total -> native)
                # API returns strings like "0.0020266306" or "0"
                amount_alloc = item.get("amount_allocated", {})
                if isinstance(amount_alloc, dict):
                    native_amount_str = amount_alloc.get("total", {}).get("native", "0")
                    total_amount_str = item.get("total_allocated", {}).get(
                        "native", native_amount_str
                    )
                else:
                    native_amount_str = "0"
                    total_amount_str = "0"

                amount = float(native_amount_str) if native_amount_str else 0.0
                total = float(total_amount_str) if total_amount_str else 0.0

                if total > 0:
                    allocations.append(
                        {
                            "strategy_id": item.get("strategy_id"),
                            "asset": asset_code,
                            "amount": amount,
                            "total": total,
                            "payout_period": item.get("payout_frequency"),
                            "source": "api_earn",
                        }
                    )

        except Exception as e:
            logger.warning(f"🎁 [EARN] API Fail: {e}")

        # Strategy 2: Legacy/Staking Balance Suffix Scan (Fallback & Supplement)
        # We scan for legacy .M (Off-chain) or .S (Staking) assets in the main balance.
        # CRITICAL: Only add if NOT already present in API results to avoid double counting.
        try:
            # Track assets we already have from API
            api_assets = {a["asset"] for a in allocations}  # e.g. {'BTC', 'DOT'}

            balances = await self._exchange.fetch_balance()
            total_balances = balances.get("total", {})

            for asset, amount in total_balances.items():
                if amount <= 0:
                    continue

                # Check for Earn suffixes
                if asset.endswith(".M") or asset.endswith(".S"):
                    base_asset = asset.split(".")[0]
                    if base_asset.startswith("X") or base_asset.startswith("Z"):
                        base_asset = (
                            base_asset[1:] if len(base_asset) == 4 else base_asset
                        )
                    if base_asset == "XBT":
                        base_asset = "BTC"

                    # If API didn't return this asset, we claim it from Legacy balance
                    if base_asset not in api_assets:
                        logger.info(
                            f"🎁 [EARN] Found Legacy/Suffix Balance (uncaptured): {asset} = {amount}"
                        )
                        allocations.append(
                            {
                                "strategy_id": "legacy_suffix",
                                "asset": base_asset,
                                "amount": amount,
                                "total": amount,
                                "payout_period": "unknown",
                                "source": "balance_suffix",
                            }
                        )
                    else:
                        # Log that we skipped it (it's likely the same funds shown in API)
                        logger.debug(
                            f"🎁 [EARN] Skipping suffix asset {asset} (covered by API {base_asset})"
                        )

        except Exception as e:
            logger.error(f"🎁 [EARN] Balance Scan Fail: {e}")

        logger.info(f"🎁 Earn: {len(allocations)}")

        # Update cache
        self._earn_cache = allocations
        self._earn_cache_time = time.time()

        return allocations

    async def get_earn_strategies(self, asset: str = None) -> List[Dict]:
        """
        Get available Kraken Earn strategies.

        Args:
            asset: Filter by asset (optional)

        Returns:
            List of strategies [{id, asset, apy, min_amount, can_allocate}]
        """
        await self._exchange._ensure_connected()

        try:
            response = await self._exchange._invoke_private(
                "private_post_earn_strategies"
            )

            strategies = []
            items = response.get("result", {}).get("items", [])

            for item in items:
                if asset and item.get("asset") != asset:
                    continue

                yield_info = item.get("yield_source", {})
                apy_str = yield_info.get("apy", "0") if yield_info else "0"
                apy = (
                    float(apy_str.replace("%", ""))
                    if isinstance(apy_str, str)
                    else float(apy_str)
                )

                strategies.append(
                    {
                        "id": item.get("id"),
                        "asset": item.get("asset"),
                        "apy": apy,
                        "min_amount": self._extract_min_amount(item),
                        "lock_type": item.get("lock_type", {}).get("type"),
                        "can_allocate": item.get("can_allocate", False),
                    }
                )

            return strategies
        except Exception as e:
            logger.error(f"🎁 [EARN] Error fetching strategies: {e}")
            return []

    def _extract_min_amount(self, item: Dict) -> float:
        """Extract minimum amount from strategy item."""
        restrictions = item.get("allocation_restriction_info", [])
        if restrictions and len(restrictions) > 0:
            return float(restrictions[0].get("amount", 0))
        return 0.0

    async def allocate_to_earn(
        self, asset: str, amount: float, strategy_id: str = None
    ) -> Dict:
        """
        Allocate funds to Kraken Earn (staking).

        Args:
            asset: Asset to stake (e.g., "BTC")
            amount: Amount to stake
            strategy_id: Strategy ID (auto-selected if not provided)

        Returns:
            {success, message, result}
        """
        await self._exchange._ensure_connected()

        try:
            # Auto-select strategy if not provided
            if not strategy_id:
                strategies = await self.get_earn_strategies(asset)
                available = [s for s in strategies if s["can_allocate"]]
                if not available:
                    return {
                        "success": False,
                        "message": f"No available strategy for {asset}",
                    }
                strategy_id = available[0]["id"]

            params = {"strategy_id": strategy_id, "amount": str(amount)}

            response = await self._exchange._invoke_private(
                "private_post_earn_allocate", params=params
            )

            if response.get("result"):
                logger.success(f"🎁 [EARN] Allocated {amount} {asset}")
                return {
                    "success": True,
                    "message": f"Allocated {amount} {asset}",
                    "result": response["result"],
                }

            # Invalidate Cache
            self._earn_cache = None

            return {
                "success": False,
                "message": str(response.get("error", "Unknown error")),
            }
        except Exception as e:
            logger.error(f"🎁 [EARN] Allocation error: {e}")
            return {"success": False, "message": str(e)}

    async def deallocate_from_earn(
        self, asset: str, amount: float, strategy_id: str = None
    ) -> Dict:
        """
        Unstake funds from Kraken Earn.

        Args:
            asset: Asset to unstake
            amount: Amount to unstake
            strategy_id: Strategy ID (auto-detected if not provided)

        Returns:
            {success, message}
        """
        await self._exchange._ensure_connected()

        try:
            if not strategy_id:
                allocations = await self.get_earn_allocations()
                asset_allocs = [a for a in allocations if a["asset"] == asset]
                if not asset_allocs:
                    return {
                        "success": False,
                        "message": f"No allocation found for {asset}",
                    }
                strategy_id = asset_allocs[0]["strategy_id"]

            params = {"strategy_id": strategy_id, "amount": str(amount)}

            response = await self._exchange._invoke_private(
                "private_post_earn_deallocate", params=params
            )

            if response.get("result"):
                logger.success(f"🎁 [EARN] Deallocated {amount} {asset}")
                return {"success": True, "message": f"Unstaked {amount} {asset}"}

            # Invalidate Cache
            self._earn_cache = None

            return {
                "success": False,
                "message": str(response.get("error", "Unknown error")),
            }
        except Exception as e:
            logger.error(f"🎁 [EARN] Deallocation error: {e}")
            return {"success": False, "message": str(e)}

    async def auto_stake_btc(self, amount: float) -> Dict:
        """Auto-stake BTC from cagnotte purchase."""
        logger.info(f"🔸 [EARN] Auto-staking {amount:.8f} BTC...")
        return await self.allocate_to_earn("BTC", amount)

    async def get_earn_summary(self) -> Dict:
        """
        Get summary of Earn performance.

        Returns:
            {total_staked_btc, total_staked_eur, allocations}
        """
        try:
            allocations = await self.get_earn_allocations()

            total_btc = sum(
                a["amount"]
                for a in allocations
                if a["asset"] == "BTC" or a["asset"] == "XBT"
            )

            # Get BTC price
            ticker = await self._exchange.fetch_ticker("BTC/EUR")
            btc_price = ticker.get("last", 0)

            return {
                "total_staked_btc": total_btc,
                "total_staked_eur": total_btc * btc_price,
                "allocations": allocations,
            }
        except Exception as e:
            logger.error(f"🎁 [EARN] Summary error: {e}")
            return {"total_staked_btc": 0, "total_staked_eur": 0, "allocations": []}

    # ═══════════════════════════════════════════════════════════════════════════
    # TRADE HISTORY
    # ═══════════════════════════════════════════════════════════════════════════

    async def fetch_trade_history(self, days: int = 30) -> List[Dict]:
        """
        Fetch trade history from Kraken.

        Args:
            days: Number of days to fetch

        Returns:
            List of trades [{id, pair, side, amount, price, cost, fee, timestamp}]
        """
        await self._exchange._ensure_connected()
        await self._exchange._ensure_markets()

        try:
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            trades = await self._exchange._invoke_private(
                "fetch_my_trades", since=since
            )

            result = []
            for t in trades:
                result.append(
                    {
                        "id": t["id"],
                        "pair": t["symbol"],
                        "side": t["side"],
                        "amount": t["amount"],
                        "price": t["price"],
                        "cost": t["cost"],
                        "fee": t["fee"]["cost"] if t.get("fee") else 0,
                        "fee_currency": t["fee"]["currency"] if t.get("fee") else "EUR",
                        "timestamp": t["timestamp"],
                        "datetime": t["datetime"],
                    }
                )

            logger.debug(f"📜 [HISTORY] Fetched {len(result)} trades")
            return result
        except Exception as e:
            logger.exception(f"📜 [HISTORY] Error: {e}")
            return []

    async def fetch_enriched_history(
        self, days: int = 7, lookback: int = 60, closed_positions: List[Dict] = None
    ) -> List[Dict]:
        """
        Fetch trade history with PnL calculation (FIFO).
        Requires fetching deeper history (lookback) to find Buy cost basis.

        SOTA v5.12: Added closed_positions fallback for orphan trades that
        were reconciled from Kraken and don't have a matching buy in history.

        Args:
            days: Days to return in final list
            lookback: Days to scan for cost basis (must be > days)
            closed_positions: Optional list of closed Position dicts with entry_price

        Returns:
            List of trades with 'pnl_eur', 'pnl_pct', 'time' added.
        """
        # Build fallback cost basis from closed positions (orphan support)
        orphan_entry_prices: Dict[str, float] = {}
        if closed_positions:
            for pos in closed_positions:
                pair = pos.get("pair") or pos.get("symbol")
                entry = pos.get("entry_price", 0)
                if pair and entry > 0:
                    orphan_entry_prices[pair] = entry
        # Fetch deep history for matching
        all_trades = await self.fetch_trade_history(days=lookback)
        all_trades.sort(key=lambda x: x["timestamp"])  # Sort chronological for FIFO

        inventory: Dict[str, List[Dict]] = {}
        enriched_trades = {}  # Map ID -> Enriched Trade

        for t in all_trades:
            pair = t["pair"]
            side = t["side"]
            amount = float(t["amount"])
            cost = float(t["cost"])
            fee = float(t["fee"])

            # Base Enrichment
            t["time"] = t["timestamp"]  # UI expects 'time'

            if pair not in inventory:
                inventory[pair] = []

            if side == "buy":
                price = cost / amount if amount > 0 else 0
                inventory[pair].append({"amount": amount, "cost": cost, "price": price})
                # Buys don't have PnL yet
                t["pnl_eur"] = 0
                t["pnl_pct"] = 0

            elif side == "sell":
                remaining_sell = amount
                matched_cost = 0.0

                # FIFO Match
                temp_inventory = inventory[pair]  # Mutable ref
                while remaining_sell > 0.00000001 and temp_inventory:
                    buy_lot = temp_inventory[0]

                    if buy_lot["amount"] <= remaining_sell:
                        consumed = buy_lot["amount"]
                        temp_inventory.pop(0)
                    else:
                        consumed = remaining_sell
                        buy_lot["amount"] -= consumed

                    matched_cost += consumed * buy_lot["price"]
                    remaining_sell -= consumed

                # Calculate PnL
                if matched_cost > 0:
                    revenue = cost - fee
                    profit = revenue - matched_cost
                    roi = profit / matched_cost

                    t["pnl_eur"] = profit
                    t["pnl_pct"] = roi
                else:
                    # SOTA v5.12: Fallback to closed_positions entry price (orphan trades)
                    fallback_entry = orphan_entry_prices.get(pair, 0)
                    if fallback_entry > 0:
                        matched_cost = fallback_entry * amount
                        revenue = cost - fee
                        profit = revenue - matched_cost
                        roi = profit / matched_cost if matched_cost > 0 else 0

                        t["pnl_eur"] = profit
                        t["pnl_pct"] = roi
                        logger.debug(
                            f"📊 [ENRICHED] Orphan PnL for {pair}: {roi * 100:.1f}%"
                        )
                    else:
                        t["pnl_eur"] = 0
                        t["pnl_pct"] = 0

            enriched_trades[t["id"]] = t

        # Filter for requested days (newer first)
        cutoff = (datetime.now() - timedelta(days=days)).timestamp() * 1000

        final_list = [t for t in enriched_trades.values() if t["timestamp"] >= cutoff]
        final_list.sort(
            key=lambda x: x["timestamp"], reverse=True
        )  # Newest first for UI

        return final_list

    async def fetch_ledger(self, days: int = 30, entry_type: str = None) -> List[Dict]:
        """
        Fetch ledger entries from Kraken.

        Args:
            days: Number of days to fetch
            entry_type: Filter by type (trade, staking, deposit, etc.)

        Returns:
            List of ledger entries
        """
        await self._exchange._ensure_connected()
        await self._exchange._ensure_markets()

        try:
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

            params = {}
            if entry_type:
                params["type"] = entry_type

            ledger = await self._exchange._invoke_private(
                "fetch_ledger", since=since, params=params
            )

            result = []
            for entry in ledger:
                result.append(
                    {
                        "id": entry["id"],
                        "type": entry["type"],
                        "currency": entry["currency"],
                        "amount": entry["amount"],
                        "fee": entry["fee"]["cost"] if entry.get("fee") else 0,
                        "balance": entry.get("after"),
                        "timestamp": entry["timestamp"],
                        "datetime": entry["datetime"],
                    }
                )

            return result
        except Exception as e:
            logger.exception(f"📒 [LEDGER] Error: {e}")
            return []

    async def calculate_real_pnl(self, days: int = 30) -> Dict:
        """
        Calculate real PnL from trade history.

        Returns:
            {total_pnl, total_fees, wins, losses, win_rate}
        """
        trades = await self.fetch_trade_history(days)

        if not trades:
            return {
                "total_pnl": 0,
                "total_fees": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
            }

        # SOTA v5.5: Use Enriched History for PnL (Unified Logic)
        # This handles the "Missing Buy" case correctly (0 PnL instead of 100% Profit)
        # and leverages the deep lookback to find cost basis.
        enriched_trades = await self.fetch_enriched_history(days=days, lookback=365)

        total_pnl = 0.0
        total_fees = 0.0
        wins = 0
        losses = 0
        gross_profit = 0.0
        gross_loss = 0.0

        for t in enriched_trades:
            pnl = t.get("pnl_eur", 0.0)
            fee = t.get("fee", 0.0)

            # Fee is already subtracted in pnl_eur for 'sell' trades in enriched_history
            # But we track total fees separately
            total_fees += fee

            if pnl == 0:
                continue

            total_pnl += pnl

            if pnl > 0:
                wins += 1
                gross_profit += pnl
            else:
                losses += 1
                gross_loss += abs(pnl)

        total_trades = wins + losses
        avg_win = gross_profit / wins if wins > 0 else 0.0
        avg_loss = gross_loss / losses if losses > 0 else 0.0
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        return {
            "total_pnl": total_pnl,
            "total_fees": total_fees,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "trades": total_trades,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    async def get_staking_rewards(self, days: int = 30) -> Dict:
        """Get staking rewards from ledger."""
        ledger = await self.fetch_ledger(days, entry_type="staking")

        rewards_by_asset: Dict[str, float] = {}
        for entry in ledger:
            if entry["amount"] > 0:
                currency = entry["currency"]
                rewards_by_asset[currency] = (
                    rewards_by_asset.get(currency, 0) + entry["amount"]
                )

        return {"by_asset": rewards_by_asset, "total_entries": len(ledger)}

    async def get_trade_history(self, days: int = 30) -> List[Dict]:
        """Get trade-only ledger entries."""
        return await self.fetch_ledger(days=days, entry_type="trade")

    async def calculate_actual_pnl(self, days: int = 30) -> Dict:
        """
        Calculate actual PnL from ledger data.

        This is more accurate than estimated PnL as it uses
        real executed prices and fees from the exchange.

        Returns:
            Dict with PnL by asset and total EUR PnL
        """
        trades = await self.get_trade_history(days)

        pnl_by_asset: Dict[str, float] = {}
        total_pnl_eur = 0.0

        for trade in trades:
            asset = trade["currency"]
            amount = trade["amount"]

            if asset not in pnl_by_asset:
                pnl_by_asset[asset] = 0.0
            pnl_by_asset[asset] += amount

            # If EUR, it's direct PnL
            if asset in ["ZEUR", "EUR"]:
                total_pnl_eur += amount

        return {
            "by_asset": pnl_by_asset,
            "total_eur": total_pnl_eur,
            "trade_count": len(trades),
            "period_days": days,
        }

    async def get_deposits_withdrawals(self, days: int = 30) -> Dict:
        """
        Get deposits and withdrawals summary.

        Returns:
            Dict with deposits, withdrawals, and totals
        """
        ledger = await self.fetch_ledger(days)

        deposits = []
        withdrawals = []

        for entry in ledger:
            if entry["type"] == "deposit":
                deposits.append(entry)
            elif entry["type"] == "withdrawal":
                withdrawals.append(entry)

        return {
            "deposits": deposits,
            "withdrawals": withdrawals,
            "total_deposited": sum(e["amount"] for e in deposits),
            "total_withdrawn": sum(abs(e["amount"]) for e in withdrawals),
        }

    def format_ledger_summary(self, transactions: List[Dict]) -> str:
        """
        Generate a formatted text summary of transactions.

        Args:
            transactions: List of transaction dicts

        Returns:
            HTML-formatted string for notifications
        """
        if not transactions:
            return "📒 No recent transactions"

        # Group by type
        by_type: Dict[str, List] = {}
        for tx in transactions:
            t = tx["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(tx)

        lines = ["📒 <b>Ledger Summary</b>\n"]

        for tx_type, txs in by_type.items():
            lines.append(f"\n<b>{tx_type.title()}</b> ({len(txs)})")
            for tx in txs[:3]:  # Max 3 per type
                sign = "+" if tx["amount"] > 0 else ""
                lines.append(
                    f"  • {tx['datetime'][:16]} | {sign}{tx['amount']:.4f} {tx['currency']}"
                )
            if len(txs) > 3:
                lines.append(f"  ... and {len(txs) - 3} more")

        return "\n".join(lines)


async def get_ledger_summary(exchange: KrakenExchange, days: int = 7) -> str:
    """Quick helper to get formatted ledger summary."""
    api = KrakenAPI(exchange)
    transactions = await api.fetch_ledger(days=days)
    return api.format_ledger_summary(transactions)


def create_api(exchange: KrakenExchange) -> KrakenAPI:
    """Factory function to create KrakenAPI."""
    return KrakenAPI(exchange)
