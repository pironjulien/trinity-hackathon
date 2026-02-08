"""
JOBS/TRADER/STRATEGY/SIGNALS.PY
==============================================================================
MODULE: TRADING SIGNALS
PURPOSE: Signal dataclass and factory functions.
==============================================================================
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from datetime import datetime


SignalAction = Literal["BUY", "SELL", "HOLD"]


@dataclass
class Signal:
    """
    Trading Signal with complete decision context.

    Attributes:
        action: BUY, SELL, or HOLD
        pair: Trading pair (e.g., "BTC/EUR")
        price: Current price at signal generation
        reason: Human-readable reason for the signal
        confidence: Confidence score (0-100)
        stop_loss: Calculated stop loss price
        take_profit: Primary take profit price
        mode: Strategy mode (mitraillette, sniper, ia)
        golden_steps: List of take profit levels (PHI-based)
        indicators: Raw indicator values at signal time
        timestamp: When signal was generated
    """

    action: SignalAction
    pair: str
    price: float
    reason: str
    confidence: float
    stop_loss: float = 0.0
    take_profit: float = 0.0
    mode: str = "mitraillette"
    golden_steps: List[float] = field(default_factory=list)
    indicators: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def hold(
        cls, pair: str, reason: str, price: float = 0.0, indicators: Dict = None
    ) -> "Signal":
        """Factory method for HOLD signals."""
        return cls(
            action="HOLD",
            pair=pair,
            price=price,
            reason=reason,
            confidence=0.0,
            indicators=indicators,
        )

    @classmethod
    def buy(
        cls,
        pair: str,
        price: float,
        reason: str,
        confidence: float,
        stop_loss: float,
        take_profit: float,
        mode: str = "mitraillette",
        golden_steps: List[float] = None,
        indicators: Dict = None,
    ) -> "Signal":
        """Factory method for BUY signals."""
        return cls(
            action="BUY",
            pair=pair,
            price=price,
            reason=reason,
            confidence=confidence,
            stop_loss=stop_loss,
            take_profit=take_profit,
            mode=mode,
            golden_steps=golden_steps or [],
            indicators=indicators,
        )

    @classmethod
    def sell(
        cls,
        pair: str,
        price: float,
        reason: str,
        confidence: float = 100.0,
        indicators: Dict = None,
    ) -> "Signal":
        """Factory method for SELL signals."""
        return cls(
            action="SELL",
            pair=pair,
            price=price,
            reason=reason,
            confidence=confidence,
            indicators=indicators,
        )

    @property
    def is_actionable(self) -> bool:
        """Check if signal requires action (BUY or SELL)."""
        return self.action in ("BUY", "SELL")

    @property
    def is_buy(self) -> bool:
        """Check if this is a BUY signal."""
        return self.action == "BUY"

    @property
    def is_sell(self) -> bool:
        """Check if this is a SELL signal."""
        return self.action == "SELL"

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        inds = self.indicators
        if hasattr(inds, "to_dict"):
             # For HOLD/Log signals, we typically want a Snapshot (not full calc)
             # But for BUY, we inject full dict anyway.
             # This call handles the fallback if we passed BrainContext.
             inds = inds.to_dict(full=False)

        return {
            "action": self.action,
            "pair": self.pair,
            "price": self.price,
            "reason": self.reason,
            "confidence": self.confidence,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "mode": self.mode,
            "golden_steps": self.golden_steps,
            "indicators": inds,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationResult:
    """Result of signal validation."""

    approved: bool
    reason: str
    context: Dict = field(default_factory=dict)

    @classmethod
    def ok(cls, context: Dict = None) -> "ValidationResult":
        """Approved validation."""
        return cls(approved=True, reason="OK", context=context or {})

    @classmethod
    def reject(cls, reason: str, context: Dict = None) -> "ValidationResult":
        """Rejected validation."""
        return cls(approved=False, reason=reason, context=context or {})
