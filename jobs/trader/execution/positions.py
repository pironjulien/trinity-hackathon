"""
JOBS/TRADER/EXECUTION/POSITIONS.PY
==============================================================================
MODULE: POSITION MANAGER 📊
PURPOSE: Position lifecycle management with trailing stops and circuit breaker.
==============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import json
from corpus.soma.nerves import logger  # SOTA: DEBUG level

from jobs.trader.config import (
    POSITIONS_FILE,
    STATE_FILE,
    PORTFOLIO_FILE,
    MEMORIES_DIR,
    get_golden_step,
    DAILY_LOSS_LIMIT,
    CAGNOTTE_BTC_RATIO,
    DUST_EJECTION_BUFFER,
    FORBIDDEN_SELL_ASSETS,
    STAGNANT_PNL_THRESHOLD,
    STAGNANT_AGE_MINUTES,
)
from jobs.trader.reporting.gamification import create_gamification
from jobs.trader.intelligence.memory import create_memory
from jobs.trader.utils import atomic_save_json


@dataclass
class Position:
    """A trading position."""

    id: str
    pair: str
    side: str  # "long" or "short"
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float
    take_profits: List[float] = field(default_factory=list)
    current_price: float = 0.0
    pnl_pct: float = 0.0
    pnl_pct: float = 0.0
    status: str = "open"  # open, closed, liquidated
    best_price: float = 0.0  # Renamed from highest_price (Max for Long, Min for Short)
    entry_context: Dict = field(default_factory=dict)
    virtual_stop_loss: float = 0.0  # SOTA: Golden Ratchet / Trailing Stop visualization

    @property
    def value(self) -> float:
        """Current position value in EUR."""
        return self.current_price * self.quantity

    @property
    def cost(self) -> float:
        """Original entry cost in EUR."""
        return self.entry_price * self.quantity

    @property
    def pnl_eur(self) -> float:
        """Unrealized PnL in EUR."""
        return self.value - self.cost

    @property
    def age_minutes(self) -> float:
        """Position age in minutes."""
        return (datetime.now() - self.entry_time).total_seconds() / 60

    def update_price(self, price: float) -> None:
        """Update current price and recalculate PnL."""
        self.current_price = price
        if self.entry_price > 0:
            if self.side == "short":
                self.pnl_pct = (self.entry_price - price) / self.entry_price
            else:
                self.pnl_pct = (price - self.entry_price) / self.entry_price

        if self.side == "short":
            if self.best_price == 0 or price < self.best_price:
                self.best_price = price
        else:
            if price > self.best_price:
                self.best_price = price

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "pair": self.pair,
            "side": self.side,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "entry_time": self.entry_time.isoformat(),
            "stop_loss": self.stop_loss,
            "take_profits": self.take_profits,
            "current_price": self.current_price,
            "pnl_pct": self.pnl_pct,
            "status": self.status,
            "best_price": self.best_price,
            "entry_context": self.entry_context,
            "virtual_stop_loss": self.virtual_stop_loss,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Position":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            pair=data["pair"],
            side=data.get("side", "long"),
            entry_price=data["entry_price"],
            quantity=data["quantity"],
            entry_time=datetime.fromisoformat(data["entry_time"])
            if isinstance(data["entry_time"], str)
            else data["entry_time"],
            stop_loss=data.get("stop_loss", 0),
            take_profits=data.get("take_profits", []),
            current_price=data.get("current_price", 0),
            pnl_pct=data.get("pnl_pct", 0),
            status=data.get("status", "open"),
            # Migration: old highest_price -> best_price
            best_price=data.get(
                "best_price", data.get("highest_price", data["entry_price"])
            ),
            entry_context=data.get("entry_context", {}),
            virtual_stop_loss=data.get("virtual_stop_loss", 0.0),
        )


class PositionManager:
    """
    SOTA Position Manager with Circuit Breaker.

    Features:
    - Position lifecycle (open, update, close)
    - Golden Ratchet (All-or-Nothing trailing stop)
    - Dust Guard (Minimum value protection)
    - Circuit breaker (loss limits)
    - Cagnotte (piggy bank) for BTC accumulation
    - Session statistics
    """

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.closed_today: List[Position] = []

        # Stats
        self.session_pnl: float = 0.0
        self.session_trades: int = 0
        self.session_wins: int = 0
        self.session_losses: int = 0

        # Daily stats
        self.daily_pnl: float = 0.0
        self.daily_wins: int = 0
        self.daily_losses: int = 0
        self.last_stat_date: Optional[date] = None

        # Circuit breaker
        self.circuit_breaker_active: bool = False
        self.circuit_breaker_reason: str = ""

        # Cagnotte (piggy bank for BTC)
        self.cagnotte: float = 0.0

        # Lifetime Stats (Portfolio)
        self.portfolio_stats: Dict = {
            "total_profit": 0.0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "btc_piggy_bank": 0.0,
        }

        # Subsystems
        self.gamification = create_gamification()
        self.memory = create_memory()

        # Load persisted state
        self._load()

    def _load(self) -> None:
        """Load positions and state from disk."""
        try:
            if POSITIONS_FILE.exists():
                with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pos_data in data.get("positions", []):
                    pos = Position.from_dict(pos_data)
                    if pos.status == "open":
                        self.positions[pos.pair] = pos
                # SOTA v5.12: Load closed_today for orphan PnL enrichment
                for closed_data in data.get("closed_today", []):
                    pos = Position.from_dict(closed_data)
                    self.closed_today.append(pos)
                logger.debug(
                    f"📊 [POSITIONS] Loaded {len(self.positions)} open, {len(self.closed_today)} closed"
                )

            if STATE_FILE.exists():
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.cagnotte = state.get("cagnotte", 0.0)
                self.session_pnl = state.get("session_pnl", 0.0)
                # FIX: Load session counters to avoid "Zombie PnL" (PnL without trades)
                self.session_trades = state.get("session_trades", 0)
                self.session_wins = state.get("session_wins", 0)
                self.session_losses = state.get("session_losses", 0)
                self.circuit_breaker_active = state.get("circuit_breaker", False)

            if PORTFOLIO_FILE.exists():
                with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                    p_data = json.load(f)
                self.portfolio_stats = p_data.get("performance", self.portfolio_stats)
                # Ensure defaults
                for k in [
                    "total_profit",
                    "total_trades",
                    "wins",
                    "losses",
                    "btc_piggy_bank",
                ]:
                    if k not in self.portfolio_stats:
                        self.portfolio_stats[k] = 0.0

        except Exception:
            logger.warning("📊 Load Error")

    def _save(self) -> None:
        """Persist positions and state to disk (ATOMICALLY)."""
        try:
            # Save Positions (with closed_today for PnL enrichment after restart)
            positions_data = [pos.to_dict() for pos in self.positions.values()]
            closed_today_data = [pos.to_dict() for pos in self.closed_today]
            atomic_save_json(
                POSITIONS_FILE,
                {
                    "positions": positions_data,
                    "closed_today": closed_today_data,  # SOTA v5.12: Persist for orphan PnL
                },
            )

            # Save State
            state = {
                "cagnotte": self.cagnotte,
                "session_pnl": self.session_pnl,
                "session_trades": self.session_trades,
                "session_wins": self.session_wins,
                "session_losses": self.session_losses,
                "circuit_breaker": self.circuit_breaker_active,
            }
            atomic_save_json(STATE_FILE, state)

            # Save Portfolio (Lifetime)
            # Update cagnotte mirror in portfolio stats for consistency
            self.portfolio_stats["btc_piggy_bank"] = self.cagnotte

            portfolio_data = {
                "positions": positions_data,  # Mirror current positions
                "pairs": list(self.positions.keys()),
                "performance": self.portfolio_stats,
            }
            atomic_save_json(PORTFOLIO_FILE, portfolio_data)

        except Exception:
            logger.error("📊 Save Error")

    # ═══════════════════════════════════════════════════════════════════════════
    # POSITION LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def open_position(
        self,
        pair: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profits: List[float] = None,
        context: Dict = None,
        side: str = "long",
    ) -> Position:
        """
        Open a new position or add to existing (DCA).

        Returns:
            Created or updated Position object
        """
        # 1. Fuzzy Duplicate Detection (SOTA Protection)
        # Prevent "TRX/EUR" vs "XTRX/EUR" duplicates
        normalized_new = pair.replace("XBT", "BTC").replace("XDG", "DOGE")
        if "/" in normalized_new:
            base, quote = normalized_new.split("/")
            # Remove 4-char legacy prefixes (X/Z)
            if len(base) == 4 and base[0] in ["X", "Z"]:
                base = base[1:]
            normalized_new = f"{base}/{quote}"

        for existing_pair in self.positions.keys():
            normalized_existing = existing_pair.replace("XBT", "BTC").replace(
                "XDG", "DOGE"
            )
            if "/" in normalized_existing:
                base, quote = normalized_existing.split("/")
                if len(base) == 4 and base[0] in ["X", "Z"]:
                    base = base[1:]
                normalized_existing = f"{base}/{quote}"

            if normalized_existing == normalized_new:
                if existing_pair != pair:
                    logger.warning(f"🔄 Alias Detected: {pair} -> {existing_pair}")
                # Check dca_enabled flag from config
                if not getattr(self.config, "dca_enabled", False):
                    logger.warning(f"🚫 DCA Rejected {pair} (dca_enabled=OFF)")
                    return self.positions[existing_pair]
                else:
                    # DCA allowed - will add to position below
                    logger.info(f"📈 DCA Adding to {existing_pair}")
                    return self._add_to_position(
                        self.positions[existing_pair], entry_price, quantity
                    )

        # 2. Strict Check (Fallback)
        if pair in self.positions:
            if not getattr(self.config, "dca_enabled", False):
                logger.warning(f"🚫 DCA Rejected {pair} (dca_enabled=OFF)")
                return self.positions[pair]
            else:
                logger.info(f"📈 DCA Adding to {pair}")
                return self._add_to_position(
                    self.positions[pair], entry_price, quantity
                )

        self._maybe_reset_daily()

        position = Position(
            id=f"{pair}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pair=pair,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profits=take_profits or [],
            current_price=entry_price,
            best_price=entry_price,
            entry_context=context or {},
        )

        self.positions[pair] = position
        self.session_trades += 1
        self._save()

        logger.success(f"📊 Open {pair} @ {entry_price:.4f}")
        return position

    def update_position(self, pair: str, current_price: float) -> Optional[Position]:
        """Update position with current price."""
        if pair not in self.positions:
            return None

        pos = self.positions[pair]
        pos.update_price(current_price)
        return pos

    def close_position(
        self, pair: str, exit_price: float, reason: str = "MANUAL"
    ) -> Tuple[float, float]:
        """
        Close a position.

        Returns:
            (pnl_pct, pnl_eur)
        """
        if pair not in self.positions:
            return 0.0, 0.0

        pos = self.positions[pair]
        pos.update_price(exit_price)
        pos.status = "closed"

        pnl_pct = pos.pnl_pct
        pnl_eur = pos.pnl_eur

        # Update stats
        self.session_pnl += pnl_eur
        self.daily_pnl += pnl_eur

        # Update Lifetime Stats
        self.portfolio_stats["total_profit"] += pnl_eur
        self.portfolio_stats["total_trades"] += 1

        if pnl_eur > 0:
            self.session_wins += 1
            self.daily_wins += 1
            self.portfolio_stats["wins"] += 1
            # Add to cagnotte (23.6% of gains)
            self.cagnotte += pnl_eur * CAGNOTTE_BTC_RATIO

            # Check achievements (dopamine reward)
            try:
                self.gamification.check_milestones(self.session_pnl)
            except Exception:
                logger.warning("🎮 Gamify Error")

            # Remember winning trade
            try:
                self.memory.remember(
                    pair=pair,
                    pnl_pct=pnl_pct,
                    pnl_eur=pnl_eur,
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    indicators=pos.entry_context,
                )
            except Exception:
                logger.warning("🧠 Memory Error")
        else:
            self.session_losses += 1
            self.daily_losses += 1
            self.portfolio_stats["losses"] += 1
            # 🛑 LOSS SHARING: Reduce Cagnotte to avoid cannibalizing cash
            # If we lose, the "net profit" pool shrinks, so cagnotte must shrink too.
            deduction = abs(pnl_eur) * CAGNOTTE_BTC_RATIO
            if self.cagnotte > 0:
                self.cagnotte = max(0.0, self.cagnotte - deduction)
                logger.debug(f"📉 Cagnotte -{deduction:.2f}€")

        self.closed_today.append(pos)
        del self.positions[pair]
        self._save()

        # SOTA v5.12: Invalidate trader_cache.json to prevent ghost positions in frontend
        cache_file = MEMORIES_DIR / "trader" / "trader_cache.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.debug("📊 Cache invalidated")
            except Exception:
                pass

        logger.info(f"📊 Close {pair} {pnl_pct * 100:+.1f}%")
        return pnl_pct, pnl_eur

    # ═══════════════════════════════════════════════════════════════════════════
    # EXIT LOGIC
    # ═══════════════════════════════════════════════════════════════════════════

    def check_exits(
        self,
        pair: str,
        current_price: float,
        min_cost: float = 5.0,
        use_golden_ratchet: bool = True,
        tp1_pct: float = None,
        tp2_pct: float = None,
    ) -> Optional[Tuple[bool, float, str]]:
        """
        Check if position should exit using Golden Ratchet or Fixed TP.
        ALL EXITS ARE 100% (Ratio = 1.0). NO PARTIALS.

        Args:
            pair: Trading pair
            current_price: Current market price
            min_cost: Minimum cost for order (Kraken default ~5€)
            use_golden_ratchet: If True, use infinite trailing stop (default).
                                If False, use fixed tp1/tp2 targets.
            tp1_pct: Fixed TP1 percentage (only used if use_golden_ratchet=False)
            tp2_pct: Fixed TP2 percentage (only used if use_golden_ratchet=False)

        Returns:
            (should_exit, ratio, reason) or None
        """
        if pair not in self.positions:
            return None

        pos = self.positions[pair]
        pos.update_price(current_price)

        # ════ SACRED ASSET GUARD (INVIOLABLE) ════
        # Absolutely prohibition on selling Sacred Assets
        for sacred in FORBIDDEN_SELL_ASSETS:
            if sacred in pair:  # e.g. "BTC" in "BTC/EUR"
                return None

        # ════ DUST GUARD (URGENT) ════
        # Protect capital from being trapped as dust.
        # If value falls within 10% of min_cost, we MUST sell immediately.
        # Example: min_cost=5€, we sell if value < 5.50€
        current_value = pos.value
        danger_zone = min_cost * (1 + DUST_EJECTION_BUFFER)  # 1.10

        if current_value > 0 and current_value < danger_zone:
            # Check if we are actually above min_cost (otherwise we are already dust)
            if current_value > min_cost:
                logger.debug(f"🛡️ Dust Eject {pair}")
                return True, 1.0, "DUST_ESCAPE"
            else:
                # Already dust... nothing we can do via API usually, but let's try
                pass

        # ════ STAGNATION EXIT (SOTA) ════
        # If position is old (> 3 days) and flat, free the capital.
        # User Mandate: "Sell without loss"
        if pos.age_minutes > STAGNANT_AGE_MINUTES:
            # We only close if we are at least Break-Even (covering fees approx)
            # PnL > STAGNANT_PNL_THRESHOLD (1.3%)
            if 0 < pos.pnl_pct < STAGNANT_PNL_THRESHOLD:
                return True, 1.0, "STAGNATION_CLEANUP"

        # ════ STOP LOSS (HARD) ════
        # ════ STOP LOSS (HARD) ════
        if pos.side == "short":
            if current_price >= pos.stop_loss:  # Short: Price rose above Stop
                return True, 1.0, "STOP_LOSS"
        else:
            if current_price <= pos.stop_loss:  # Long: Price fell below Stop
                return True, 1.0, "STOP_LOSS"

        # Current gain percentage for both modes
        current_gain = 0.0
        if pos.side == "short":
            # For Short: (Entry - Current) / Entry (using current price, not best)
            current_gain = (pos.entry_price - current_price) / pos.entry_price
        else:
            # For Long: (Current - Entry) / Entry
            current_gain = (current_price - pos.entry_price) / pos.entry_price

        # ════ MODE SELECTION: GOLDEN RATCHET vs FIXED TP ════
        if not use_golden_ratchet:
            # ════ FIXED TP MODE ════
            # Simple take profit at tp1 or tp2 thresholds
            if tp2_pct is not None and current_gain >= tp2_pct:
                return True, 1.0, "TP2_HIT"
            if tp1_pct is not None and current_gain >= tp1_pct:
                return True, 1.0, "TP1_HIT"
            return None

        # ════ GOLDEN RATCHET (ALL-OR-NOTHING) ════
        # Principle: As price climbs Golden Steps, Virtual Stop Loss follows.
        # Breach of virtual stop = 100% SELL.

        # Best gain for ratchet calculation (uses best price, not current)
        if pos.side == "short":
            best_gain = (pos.entry_price - pos.best_price) / pos.entry_price
        else:
            best_gain = (pos.best_price - pos.entry_price) / pos.entry_price

        virtual_stop = pos.stop_loss  # Default to hard stop
        ratchet_level = -1

        # SOTA v5.8: GOLDEN RATCHET INFINITY
        # Determine Ratchet Level using dynamic Phi progression
        # get_golden_step(n) = 0.01 × Φ^n (infinite levels)
        # Level 0: 1%, Level 1: 1.618%, Level 2: 2.618%, ... Level 10: 122.9%!
        level = 0
        while True:
            step = get_golden_step(level)
            if best_gain >= step:
                ratchet_level = level
                level += 1
                # Safety cap at 50 levels (~122,000% gain = unrealistic)
                if level >= 50:
                    break
            else:
                break

        if ratchet_level >= 0:
            # Level 0 (1.3%) -> No change (let it breathe, secure space)
            if ratchet_level == 0:
                pass

            # Level 1 (1.618%) -> Breakeven
            elif ratchet_level == 1:
                if pos.side == "short":
                    virtual_stop = pos.entry_price * 0.998  # Break even (fees)
                else:
                    virtual_stop = pos.entry_price * 1.002  # +0.2% for fees

            # Level N -> Lock Level N-1 (using dynamic Phi progression)
            else:
                prev_step_pct = get_golden_step(ratchet_level - 1)
                if pos.side == "short":
                    virtual_stop = pos.entry_price * (1 - prev_step_pct)
                else:
                    virtual_stop = pos.entry_price * (1 + prev_step_pct)

            # SOTA: Persist the virtual stop for UI visibility (Save only on change)
            if abs(pos.virtual_stop_loss - virtual_stop) > 0.00000001:
                old_vsl = pos.virtual_stop_loss
                pos.virtual_stop_loss = virtual_stop
                # ═══════════════════════════════════════════════════════════════
                # 📊 DEBUG: Log Golden Ratchet SL adjustment
                # ═══════════════════════════════════════════════════════════════
                step_pct = get_golden_step(ratchet_level) * 100
                logger.info(
                    f"🔒 [RATCHET] {pair} L{ratchet_level} (>{step_pct:.2f}%) | "
                    f"VSL: {old_vsl:.6f} → {virtual_stop:.6f} | Best={pos.best_price:.6f}"
                )
                self._save()

            # Check Breach
            # Check Breach (Side dependent)
            breach = False
            if pos.side == "short":
                # Short: Virtual stop is falling. If Price > Virtual Stop -> Breach
                # E.g. Entry 100. Best 80. Step 10%. Virtual Stop 90. Price 91 -> Exit.
                if ratchet_level == 1:
                    virtual_stop = pos.entry_price * 0.998  # Break even (fees)
                else:
                    prev_step_pct = get_golden_step(ratchet_level - 1)
                    virtual_stop = pos.entry_price * (1 - prev_step_pct)

                if current_price > virtual_stop:
                    breach = True
            else:
                # Long logic (existing)
                if current_price < virtual_stop:
                    breach = True

            if breach:
                reason = f"GOLDEN_RATCHET_L{ratchet_level}"
                return True, 1.0, reason

        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # CIRCUIT BREAKER
    # ═══════════════════════════════════════════════════════════════════════════

    def check_circuit_breaker(
        self, current_capital: float, initial_capital: float
    ) -> Tuple[bool, str]:
        """
        Check if trading should halt.

        Returns:
            (should_halt, reason)
        """
        if self.circuit_breaker_active:
            return True, self.circuit_breaker_reason

        # Daily drawdown check
        if initial_capital > 0:
            drawdown = (current_capital - initial_capital) / initial_capital
            if drawdown < DAILY_LOSS_LIMIT:
                self._trigger_circuit_breaker(f"Daily loss {drawdown * 100:.1f}%")
                return True, self.circuit_breaker_reason

        return False, ""

    def _trigger_circuit_breaker(self, reason: str) -> None:
        """Activate circuit breaker."""
        self.circuit_breaker_active = True
        self.circuit_breaker_reason = reason
        self._save()
        logger.critical(f"🚨 Breaker: {reason}")

    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker."""
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = ""
        self._save()
        logger.success("✅ Breaker Reset")

    def spend_cagnotte(self, amount: float) -> bool:
        """
        Spend from cagnotte (e.g. for BTC auto-buy).

        Args:
            amount: Amount to spend in EUR

        Returns:
            True if successful, False if insufficient funds
        """
        if self.cagnotte >= amount:
            self.cagnotte -= amount
            self._save()
            logger.debug(f"🐷 Spent {amount:.2f}€")
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _maybe_reset_daily(self) -> None:
        """Reset daily stats at midnight."""
        today = date.today()
        if self.last_stat_date != today:
            self.daily_pnl = 0.0
            self.daily_wins = 0
            self.daily_losses = 0
            self.last_stat_date = today
            self.closed_today = []

    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())

    def get_position(self, pair: str) -> Optional[Position]:
        """Get position by pair."""
        return self.positions.get(pair)

    def get_total_exposure(self) -> float:
        """Total value of open positions in EUR."""
        return sum(pos.value for pos in self.positions.values())

    def get_stats(self) -> Dict:
        """Get session statistics."""
        total = self.session_wins + self.session_losses
        return {
            "session_pnl": self.session_pnl,
            "session_trades": self.session_trades,
            "session_wins": self.session_wins,
            "session_losses": self.session_losses,
            "win_rate": (self.session_wins / total * 100) if total > 0 else 0,
            "daily_pnl": self.daily_pnl,
            "cagnotte": self.cagnotte,
            "open_positions": len(self.positions),
            "total_exposure": self.get_total_exposure(),
        }

    def get_today_stats(self) -> Dict:
        """Get stats for today."""
        total = self.daily_wins + self.daily_losses
        return {
            "pnl_eur": self.daily_pnl,
            "wins": self.daily_wins,
            "losses": self.daily_losses,
            "trades": total,
            "win_rate": (self.daily_wins / total * 100) if total > 0 else 0,
        }

    def add_to_position(
        self, pair: str, additional_price: float, additional_quantity: float
    ) -> Optional[Position]:
        """
        DCA Averaging: Add to an existing position.
        Requires dca_enabled=True in config.
        """
        if not getattr(self.config, "dca_enabled", False):
            logger.error(f"🚫 DCA Attempted on {pair} - dca_enabled=OFF")
            return None
        return self._add_to_position(
            self.positions.get(pair), additional_price, additional_quantity
        )

    def _add_to_position(
        self, position: Position, additional_price: float, additional_quantity: float
    ) -> Optional[Position]:
        """
        Internal DCA logic: Calculate weighted average entry price.
        """
        if not position:
            return None

        # Calculate weighted average entry price
        old_value = position.entry_price * position.quantity
        new_value = additional_price * additional_quantity
        total_quantity = position.quantity + additional_quantity
        new_avg_price = (old_value + new_value) / total_quantity

        # Update position
        position.entry_price = new_avg_price
        position.quantity = total_quantity

        # Recalculate stop loss based on new entry (maintain same % distance)
        if position.stop_loss and position.stop_loss > 0:
            sl_pct = 1 - (position.stop_loss / position.entry_price)
            position.stop_loss = new_avg_price * (1 - sl_pct)

        logger.success(
            f"📈 DCA {position.pair}: +{additional_quantity:.4f} @ {additional_price:.4f} "
            f"→ Avg: {new_avg_price:.4f} | Total: {total_quantity:.4f}"
        )
        self._save()
        return position

    async def sync_positions_from_kraken(self, exchange, api=None) -> Dict:
        """
        SOTA Portfolio Sync: Kraken + Local Persistence = Hybrid Truth.
        """

        # Use simple constant for dust if not imported
        DUST_THRESHOLD = 1.618  # PHI

        report = {
            "synced": [],
            "ghosts_removed": [],
            "orphans_added": [],
            "dust_ignored": [],
            "eur_balance": 0,
        }

        try:
            logger.debug("[POSITIONS] Syncing with Kraken...")

            # 1. Get real balances from Kraken
            balances = await exchange.fetch_all_balances()
            # Find EUR balance
            eur_bal = balances.get("EUR", {}) or balances.get("ZEUR", {})
            report["eur_balance"] = eur_bal.get("free", 0)

            # 2. Get recent trades for entry prices (fallback)
            trades = []
            if api and hasattr(api, "fetch_trade_history"):
                trades = await api.fetch_trade_history(days=7)
            elif hasattr(exchange, "get_trade_history"):
                trades = await exchange.get_trade_history(days=7)

            entry_prices_from_kraken = {}
            for t in reversed(trades):
                if t.get("side") == "buy":
                    entry_prices_from_kraken[t.get("pair")] = t.get("price")

            # 3. Process each Kraken balance
            kraken_pairs = set()

            for asset, balance in balances.items():
                # STRICT FILTERING: Skip Fiat and Sacred Assets (BTC)
                # We do NOT want to manage/sell BTC in the bot
                if (
                    asset
                    in [
                        "EUR",
                        "USD",
                        "ZEUR",
                        "ZUSD",
                        "BTC",
                        "XBT",
                        "XXBT",
                        "BTC_TOTAL",
                        "ETH_TOTAL",
                    ]
                    or asset in FORBIDDEN_SELL_ASSETS
                ):
                    continue

                amount = float(balance.get("total", 0) or 0.0)
                if amount <= 0:
                    continue

                pair = f"{asset}/EUR"
                kraken_pairs.add(pair)

                # Get current price
                current_price = float(balance.get("price", 0.0) or 0.0)

                if current_price <= 0:
                    try:
                        # Fallback: Fetch real ticker price
                        ticker = await exchange.fetch_ticker(pair)
                        last = ticker.get("last")
                        current_price = float(last) if last is not None else 0.0
                    except Exception:
                        pass  # Keep 0 if failed

                if current_price <= 0:
                    continue

                value_eur = amount * current_price

                # Filter dust
                if value_eur < DUST_THRESHOLD:
                    report["dust_ignored"].append({"pair": pair, "value": value_eur})
                    continue

                # Check memory
                existing_pos = self.positions.get(pair)

                if existing_pos:
                    # UPDATE existing
                    existing_pos.quantity = amount
                    # Use update_price to trigger PnL and high-water mark calculation
                    existing_pos.update_price(current_price)
                    report["synced"].append(pair)
                else:
                    # SOTA v5.12: Skip orphan creation if recently closed (anti-ghost)
                    recently_closed_pairs = {p.pair for p in self.closed_today}
                    if pair in recently_closed_pairs:
                        logger.debug(f"🚫 Skipping orphan {pair} (recently closed)")
                        report["dust_ignored"].append(
                            {
                                "pair": pair,
                                "value": value_eur,
                                "reason": "recently_closed",
                            }
                        )
                        continue

                    # ORPHAN: Create new
                    entry_price = entry_prices_from_kraken.get(pair, current_price)
                    # FIX: Calculate SL BEFORE open_position to avoid race condition
                    default_sl = entry_price * (1 - 0.05)  # 5% default safety

                    pos = self.open_position(
                        pair=pair,
                        entry_price=entry_price,
                        quantity=amount,
                        stop_loss=default_sl,  # Correct SL passed immediately
                    )
                    # Ensure PnL is calculated immediately
                    pos.update_price(current_price)

                    report["orphans_added"].append({"pair": pair, "value": value_eur})
                    logger.warning(f"⚠️ Orphan {pair} {value_eur:.2f}€")
                    # FIX: Add to kraken_pairs to prevent ghost detection from deleting it
                    kraken_pairs.add(pair)

            # 5. Detect ghosts (in memory but not on Kraken)
            for pair in list(self.positions.keys()):
                # Fuzzy Check
                is_found = False
                if pair in kraken_pairs:
                    is_found = True
                else:
                    # Try fuzzy
                    norm_pair = pair.replace("XBT", "BTC").replace("XDG", "DOGE")
                    if "/" in norm_pair:
                        b, q = norm_pair.split("/")
                        if len(b) == 4 and b[0] in ["X", "Z"]:
                            b = b[1:]
                        norm_pair = f"{b}/{q}"

                    for k_pair in kraken_pairs:
                        norm_k = k_pair.replace("XBT", "BTC").replace("XDG", "DOGE")
                        if "/" in norm_k:
                            kb, kq = norm_k.split("/")
                            if len(kb) == 4 and kb[0] in ["X", "Z"]:
                                kb = kb[1:]
                            norm_k = f"{kb}/{kq}"

                        if norm_k == norm_pair:
                            is_found = True
                            break

                if not is_found:
                    if "/" in pair:
                        asset = pair.split("/")[0]
                        # Double check asset fuzzy
                        asset_found = False
                        if asset in balances:
                            asset_found = True
                        else:
                            # Fuzzy asset check
                            norm_asset = asset
                            if len(asset) == 4 and asset[0] in ["X", "Z"]:
                                norm_asset = asset[1:]

                            for bal_asset in balances:
                                norm_bal = bal_asset
                                if len(bal_asset) == 4 and bal_asset[0] in ["X", "Z"]:
                                    norm_bal = bal_asset[1:]
                                if norm_bal == norm_asset:
                                    asset_found = True
                                    break

                        if not asset_found:
                            # Truly gone
                            del self.positions[pair]
                            report["ghosts_removed"].append(pair)
                            logger.debug(f"[POSITIONS] Ghost removed: {pair}")

            self._save()

            logger.info(
                f"📊 Sync: {len(report['synced'])}s/{len(report['orphans_added'])}o/{len(report['ghosts_removed'])}g"
            )
            return report

        except Exception as e:
            logger.error(f"📊 [SYNC] Error: {e}")
            return report


def create_position_manager() -> PositionManager:
    """Factory function."""
    return PositionManager()
