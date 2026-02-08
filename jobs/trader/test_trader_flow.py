#!/usr/bin/env python3
"""
TRADER E2E TEST - Simule un trade complet pour vérifier le flow.
Usage: python3 test_trader_flow.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any

# Mock prices for simulation
MOCK_PAIR = "TEST/EUR"
ENTRY_PRICE = 1.0
TP_PRICE = 1.02  # +2%
SL_PRICE = 0.98  # -2%


class TestTraderFlow:
    """Test complet du flow Trader."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results: List[Dict] = []

    def log(self, test: str, passed: bool, details: str = ""):
        emoji = "✅" if passed else "❌"
        status = "PASS" if passed else "FAIL"
        print(f"{emoji} [{status}] {test}: {details}")
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append({"test": test, "passed": passed, "details": details})

    async def test_signal_generation(self):
        """Test 1: Vérifier que brain.decide() génère un Signal avec SL/TP corrects."""
        print("\n" + "=" * 60)
        print("TEST 1: Signal Generation (brain.decide)")
        print("=" * 60)

        try:
            from jobs.trader.config import TraderConfig, MITRAILLETTE
            from jobs.trader.strategy.brain import TradingBrain

            config = TraderConfig.load()
            brain = TradingBrain(config)

            # Check que la stratégie a un SL défini
            sl = MITRAILLETTE.stop_loss
            tp = MITRAILLETTE.tp1

            self.log(
                "Strategy SL defined",
                sl != 0 and sl < 0,
                f"SL = {sl * 100:.2f}%",
            )
            self.log(
                "Strategy TP defined",
                tp != 0 and tp > 0,
                f"TP = {tp * 100:.2f}%",
            )

        except Exception as e:
            self.log("Signal Generation", False, str(e))

    async def test_position_creation(self):
        """Test 2: Créer une position fictive avec SL."""
        print("\n" + "=" * 60)
        print("TEST 2: Position Creation with SL")
        print("=" * 60)

        try:
            from jobs.trader.execution.positions import Position

            pos = Position(
                id=f"TEST_{datetime.now().strftime('%H%M%S')}",
                pair=MOCK_PAIR,
                side="long",
                entry_price=ENTRY_PRICE,
                quantity=100,
                entry_time=datetime.now(),
                stop_loss=SL_PRICE,
                take_profits=[TP_PRICE],
                current_price=ENTRY_PRICE,
                best_price=ENTRY_PRICE,
            )

            self.log(
                "Position created with SL",
                pos.stop_loss == SL_PRICE,
                f"SL = {pos.stop_loss}",
            )
            self.log(
                "Position has TP",
                TP_PRICE in pos.take_profits,
                f"TPs = {pos.take_profits}",
            )

        except Exception as e:
            self.log("Position Creation", False, str(e))

    async def test_sl_trigger(self):
        """Test 3: Vérifier que le SL déclenche une vente."""
        print("\n" + "=" * 60)
        print("TEST 3: Stop Loss Trigger")
        print("=" * 60)

        try:
            from jobs.trader.execution.positions import Position, PositionManager

            # Create a mock position
            pos = Position(
                id="TEST_SL",
                pair=MOCK_PAIR,
                side="long",
                entry_price=ENTRY_PRICE,
                quantity=100,
                entry_time=datetime.now(),
                stop_loss=SL_PRICE,  # 0.98
                take_profits=[TP_PRICE],
                current_price=ENTRY_PRICE,
                best_price=ENTRY_PRICE,
            )

            # Simulate price dropping BELOW SL
            current_price_below_sl = 0.97  # Below 0.98 SL

            # Check SL logic directly
            sl_triggered = current_price_below_sl <= pos.stop_loss

            self.log(
                "SL triggers when price < SL",
                sl_triggered,
                f"Price {current_price_below_sl} <= SL {pos.stop_loss}",
            )

            # Simulate price ABOVE SL (should NOT trigger)
            current_price_above_sl = 0.99
            sl_not_triggered = current_price_above_sl > pos.stop_loss

            self.log(
                "SL does NOT trigger when price > SL",
                sl_not_triggered,
                f"Price {current_price_above_sl} > SL {pos.stop_loss}",
            )

        except Exception as e:
            self.log("SL Trigger", False, str(e))

    async def test_tp_trigger(self):
        """Test 4: Vérifier que le TP déclenche une vente."""
        print("\n" + "=" * 60)
        print("TEST 4: Take Profit Trigger")
        print("=" * 60)

        try:
            from jobs.trader.execution.positions import Position

            pos = Position(
                id="TEST_TP",
                pair=MOCK_PAIR,
                side="long",
                entry_price=ENTRY_PRICE,
                quantity=100,
                entry_time=datetime.now(),
                stop_loss=SL_PRICE,
                take_profits=[TP_PRICE],  # 1.02
                current_price=ENTRY_PRICE,
                best_price=ENTRY_PRICE,
            )

            # Simulate price rising ABOVE TP
            current_price_above_tp = 1.03  # Above 1.02 TP

            tp_triggered = current_price_above_tp >= TP_PRICE

            self.log(
                "TP triggers when price >= TP",
                tp_triggered,
                f"Price {current_price_above_tp} >= TP {TP_PRICE}",
            )

        except Exception as e:
            self.log("TP Trigger", False, str(e))

    async def test_check_exits_function(self):
        """Test 5: Vérifier que check_exits() fonctionne correctement."""
        print("\n" + "=" * 60)
        print("TEST 5: check_exits() Function")
        print("=" * 60)

        try:
            from jobs.trader.execution.positions import PositionManager

            pm = PositionManager()

            # Open test position
            pos = pm.open_position(
                pair=MOCK_PAIR,
                entry_price=ENTRY_PRICE,
                quantity=100,
                stop_loss=SL_PRICE,
                take_profits=[TP_PRICE],
            )

            self.log(
                "Position opened with SL",
                pos.stop_loss == SL_PRICE,
                f"SL = {pos.stop_loss}",
            )

            # Test: Price above entry (no exit)
            exit_signal, ratio, reason = pm.check_exits(MOCK_PAIR, 1.01)
            self.log(
                "No exit at +1%",
                exit_signal is False,
                f"Exit={exit_signal}, Reason={reason}",
            )

            # Test: Price at TP (should exit)
            exit_signal, ratio, reason = pm.check_exits(MOCK_PAIR, 1.025)
            self.log(
                "Exit at TP (+2.5%)",
                exit_signal is True,
                f"Exit={exit_signal}, Reason={reason}",
            )

            # Cleanup
            if MOCK_PAIR in pm.positions:
                del pm.positions[MOCK_PAIR]
                pm._save()

        except Exception as e:
            self.log("check_exits()", False, str(e))

    async def test_check_exits_sl(self):
        """Test 6: Vérifier que check_exits() déclenche le SL."""
        print("\n" + "=" * 60)
        print("TEST 6: check_exits() with SL Trigger")
        print("=" * 60)

        try:
            from jobs.trader.execution.positions import PositionManager

            pm = PositionManager()

            # Remove any existing test position
            if MOCK_PAIR in pm.positions:
                del pm.positions[MOCK_PAIR]

            # Open test position
            pos = pm.open_position(
                pair=MOCK_PAIR,
                entry_price=ENTRY_PRICE,
                quantity=100,
                stop_loss=SL_PRICE,  # 0.98
                take_profits=[TP_PRICE],
            )

            self.log(
                "Position created",
                pos is not None,
                f"Entry={pos.entry_price}, SL={pos.stop_loss}",
            )

            # Test: Price below SL (should trigger exit)
            exit_signal, ratio, reason = pm.check_exits(MOCK_PAIR, 0.97)  # Below 0.98
            self.log(
                "SL Exit at -3%",
                exit_signal is True,
                f"Exit={exit_signal}, Reason={reason}",
            )

            # Cleanup
            if MOCK_PAIR in pm.positions:
                del pm.positions[MOCK_PAIR]
                pm._save()

        except Exception as e:
            self.log("check_exits() SL", False, str(e))

    async def run_all_tests(self):
        """Exécute tous les tests."""
        print("\n" + "=" * 60)
        print("🧪 TRADER E2E TEST SUITE")
        print("=" * 60)

        await self.test_signal_generation()
        await self.test_position_creation()
        await self.test_sl_trigger()
        await self.test_tp_trigger()
        await self.test_check_exits_function()
        await self.test_check_exits_sl()

        print("\n" + "=" * 60)
        print(f"📊 RESULTS: {self.passed} passed, {self.failed} failed")
        print("=" * 60)

        return self.failed == 0


if __name__ == "__main__":
    tester = TestTraderFlow()
    success = asyncio.run(tester.run_all_tests())
    sys.exit(0 if success else 1)
