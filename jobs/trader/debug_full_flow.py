#!/usr/bin/env python3
"""
🔬 TRADER DEEP DEBUG - Simulation complète du cycle de vie d'un trade.

Simule:
1. Arrivée crypto avec bons signaux
2. Appel IA pour validation BUY
3. Ouverture position avec SL/TP du mode actuel
4. Prix monte → vérifie Golden Ratchet (SL monte)
5. Prix descend → vérifie déclenchement SL → SELL

Usage: python3 debug_full_flow.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple
from dataclasses import dataclass

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Logging setup
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="DEBUG", format="<level>{message}</level>")


@dataclass
class DebugStep:
    """Une étape du debug."""

    name: str
    passed: bool
    details: str
    data: Dict = None

    def __str__(self):
        emoji = "✅" if self.passed else "❌"
        return f"{emoji} {self.name}: {self.details}"


class TraderDeepDebug:
    """Debug profond du cycle de vie complet d'un trade."""

    def __init__(self):
        self.steps: list[DebugStep] = []
        self.mock_pair = "DEBUG/EUR"
        self.mock_price = 1.0

    def log_step(self, name: str, passed: bool, details: str, data: Dict = None):
        step = DebugStep(name, passed, details, data or {})
        self.steps.append(step)
        print(f"\n{'=' * 60}")
        print(step)
        if data:
            for k, v in data.items():
                print(f"   📊 {k}: {v}")
        print("=" * 60)

    async def step_1_load_config(self) -> Dict:
        """Step 1: Charger la config active (mode + level)."""
        print("\n" + "🔷" * 30)
        print("STEP 1: LOAD CONFIG (Mode + Level)")
        print("🔷" * 30)

        try:
            from jobs.trader.config import TraderConfig

            config = TraderConfig.load()

            mode = config.mode
            level = getattr(config, "level", "PASSIVE")

            # Get strategy for current mode/level
            strategy = config.get_strategy()

            sl_pct = (
                strategy.stop_loss * 100 if hasattr(strategy, "stop_loss") else -1.0
            )
            tp_pct = strategy.tp1 * 100 if hasattr(strategy, "tp1") else 1.0

            data = {
                "Mode": mode,
                "Level": level,
                "Stop Loss": f"{sl_pct:.2f}%",
                "Take Profit (TP1)": f"{tp_pct:.2f}%",
                "AI Buy Validation": getattr(config, "ai_buy_validation", True),
                "Max Positions": strategy.max_positions
                if hasattr(strategy, "max_positions")
                else "N/A",
            }

            self.log_step(
                "Config Loaded",
                True,
                f"Mode={mode}, Level={level}, SL={sl_pct:.2f}%, TP={tp_pct:.2f}%",
                data,
            )

            return {
                "config": config,
                "strategy": strategy,
                "sl_pct": sl_pct / 100,
                "tp_pct": tp_pct / 100,
            }

        except Exception as e:
            self.log_step("Config Load", False, str(e))
            return {}

    async def step_2_simulate_signal(self, config_data: Dict) -> Dict:
        """Step 2: Simuler un signal BUY avec bons indicateurs."""
        print("\n" + "🔷" * 30)
        print("STEP 2: SIMULATE BUY SIGNAL")
        print("🔷" * 30)

        try:
            from jobs.trader.strategy.signals import Signal

            strategy = config_data.get("strategy")
            sl_pct = config_data.get("sl_pct", -0.01)
            tp_pct = config_data.get("tp_pct", 0.01)

            # Fake good indicators
            indicators = {
                "pair": self.mock_pair,
                "rsi": 28.5,  # Oversold = good
                "rsi_rising": True,
                "macd_strong": True,
                "is_uptrend": True,
                "in_fib_zone": True,
                "atr_pct": 0.02,
                "bb_position": 0.15,  # Near bottom
                "bearish_divergence": False,
                "bullish_divergence": True,
            }

            # Calculate SL/TP from config
            stop_loss_price = self.mock_price * (1 + sl_pct)
            take_profit_price = self.mock_price * (1 + tp_pct)

            signal = Signal.buy(
                pair=self.mock_pair,
                price=self.mock_price,
                reason="DEBUG: RSI oversold + MACD strong + Uptrend",
                confidence=85.0,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price,
                mode=config_data.get("config").mode,
                indicators=indicators,
            )

            data = {
                "Pair": self.mock_pair,
                "Action": signal.action,
                "Entry Price": f"{self.mock_price:.4f}€",
                "Stop Loss": f"{signal.stop_loss:.4f}€ ({sl_pct * 100:.2f}%)",
                "Take Profit": f"{signal.take_profit:.4f}€ ({tp_pct * 100:.2f}%)",
                "Confidence": f"{signal.confidence:.1f}%",
                "RSI": indicators["rsi"],
                "MACD Strong": indicators["macd_strong"],
            }

            self.log_step(
                "Signal Generated",
                signal.action == "BUY",
                f"BUY {self.mock_pair} @ {self.mock_price}€, Confidence={signal.confidence:.1f}%",
                data,
            )

            return {"signal": signal, **config_data}

        except Exception as e:
            self.log_step("Signal Generation", False, str(e))
            return config_data

    async def step_3_ai_validation(self, signal_data: Dict) -> Dict:
        """Step 3: Vérifier l'appel IA pour validation."""
        print("\n" + "🔷" * 30)
        print("STEP 3: AI VALIDATION CALL")
        print("🔷" * 30)

        try:
            config = signal_data.get("config")

            # Check if AI validation is enabled
            ai_enabled = getattr(config, "ai_buy_validation", True)

            if not ai_enabled:
                self.log_step(
                    "AI Validation",
                    True,
                    "AI Validation DISABLED - trade proceeds without AI",
                    {"ai_buy_validation": False},
                )
                return {
                    **signal_data,
                    "ai_approved": True,
                    "ai_reason": "Validation désactivée",
                }

            # Simulate AI call (don't actually call to avoid cost)
            # In real flow, TradingBrain._consult_ai() is called

            from jobs.trader.strategy.brain import TradingBrain

            brain = TradingBrain(config)

            # Check the method exists and what it expects
            import inspect

            sig = inspect.signature(brain._consult_ai)

            data = {
                "AI Enabled": True,
                "Method": "_consult_ai()",
                "Parameters": str(list(sig.parameters.keys())),
                "Timeout": "144s",
                "Fallback (>80% conf)": "Fail-Open",
            }

            # We won't actually call AI to avoid costs, just verify the path exists
            self.log_step(
                "AI Validation Path",
                True,
                "AI validation enabled, _consult_ai() will be called",
                data,
            )

            # Simulate approval
            return {
                **signal_data,
                "ai_approved": True,
                "ai_reason": "SIMULATED: AI would validate",
            }

        except Exception as e:
            self.log_step("AI Validation", False, str(e))
            return signal_data

    async def step_4_open_position(self, validated_data: Dict) -> Dict:
        """Step 4: Ouvrir une position avec le SL du mode."""
        print("\n" + "🔷" * 30)
        print("STEP 4: OPEN POSITION")
        print("🔷" * 30)

        try:
            from jobs.trader.execution.positions import PositionManager

            signal = validated_data.get("signal")
            pm = PositionManager()

            # Clean any existing debug position
            if self.mock_pair in pm.positions:
                del pm.positions[self.mock_pair]

            # Open position with signal's SL/TP
            pos = pm.open_position(
                pair=self.mock_pair,
                entry_price=signal.price,
                quantity=100,
                stop_loss=signal.stop_loss,
                take_profits=[signal.take_profit],
            )

            data = {
                "Position ID": pos.id,
                "Entry Price": f"{pos.entry_price:.4f}€",
                "Stop Loss": f"{pos.stop_loss:.4f}€",
                "Take Profits": [f"{tp:.4f}€" for tp in pos.take_profits],
                "Quantity": pos.quantity,
                "Side": pos.side,
            }

            self.log_step(
                "Position Opened",
                pos.stop_loss == signal.stop_loss,
                f"Opened {self.mock_pair} with SL={pos.stop_loss:.4f}",
                data,
            )

            return {**validated_data, "position_manager": pm, "position": pos}

        except Exception as e:
            self.log_step("Position Open", False, str(e))
            return validated_data

    async def step_5_price_rises(self, position_data: Dict) -> Dict:
        """Step 5: Prix monte → vérifier Golden Ratchet (SL monte)."""
        print("\n" + "🔷" * 30)
        print("STEP 5: PRICE RISES → GOLDEN RATCHET")
        print("🔷" * 30)

        try:
            pm = position_data.get("position_manager")
            pos = position_data.get("position")
            signal = position_data.get("signal")

            original_sl = pos.stop_loss

            # Simulate price rising to +1.5% (above entry but below TP)
            new_price = self.mock_price * 1.015
            pos.update_price(new_price)

            # Check if Golden Ratchet updated virtual_stop_loss
            virtual_sl = pos.virtual_stop_loss

            # Check exits at this price
            result = pm.check_exits(self.mock_pair, new_price)
            if result is None:
                exit_signal, ratio, reason = False, 0, "No exit needed"
            else:
                exit_signal, ratio, reason = result

            data = {
                "New Price": f"{new_price:.4f}€ (+1.5%)",
                "Original SL": f"{original_sl:.4f}€",
                "Current SL (hard)": f"{pos.stop_loss:.4f}€",
                "Virtual SL (Golden Ratchet)": f"{virtual_sl:.4f}€"
                if virtual_sl
                else "Not set",
                "Best Price": f"{pos.best_price:.4f}€",
                "Exit Signal": exit_signal,
                "Exit Reason": reason,
            }

            # Golden Ratchet should raise virtual_sl when price rises
            sl_moved = virtual_sl > original_sl if virtual_sl else False

            self.log_step(
                "Price Rise (+1.5%)",
                not exit_signal,  # Should NOT exit yet
                f"Price={new_price:.4f}, SL moved: {sl_moved}",
                data,
            )

            return {**position_data, "price_after_rise": new_price}

        except Exception as e:
            self.log_step("Price Rise", False, str(e))
            return position_data

    async def step_6_price_drops_sl_triggers(self, position_data: Dict) -> Dict:
        """Step 6: Prix descend sous SL → vérifier déclenchement SELL."""
        print("\n" + "🔷" * 30)
        print("STEP 6: PRICE DROPS → SL TRIGGERS SELL")
        print("🔷" * 30)

        try:
            pm = position_data.get("position_manager")
            pos = position_data.get("position")

            sl_price = pos.stop_loss

            # Simulate price dropping BELOW SL
            crash_price = sl_price * 0.99  # 1% below SL

            # Check exits at this price
            exit_signal, ratio, reason = pm.check_exits(self.mock_pair, crash_price)

            data = {
                "Crash Price": f"{crash_price:.4f}€",
                "Stop Loss": f"{sl_price:.4f}€",
                "Price vs SL": f"{'BELOW' if crash_price < sl_price else 'ABOVE'} SL",
                "Exit Signal": exit_signal,
                "Exit Reason": reason,
                "Exit Ratio": ratio,
            }

            self.log_step(
                "SL Triggered",
                exit_signal == True and "STOP" in str(reason).upper(),
                f"Price {crash_price:.4f} < SL {sl_price:.4f} → EXIT={exit_signal}, Reason={reason}",
                data,
            )

            return position_data

        except Exception as e:
            self.log_step("SL Trigger", False, str(e))
            return position_data

    async def step_7_cleanup(self, position_data: Dict):
        """Step 7: Nettoyer la position de test."""
        print("\n" + "🔷" * 30)
        print("STEP 7: CLEANUP")
        print("🔷" * 30)

        try:
            pm = position_data.get("position_manager")

            if pm and self.mock_pair in pm.positions:
                del pm.positions[self.mock_pair]
                pm._save()
                self.log_step(
                    "Cleanup", True, f"Removed test position {self.mock_pair}"
                )
            else:
                self.log_step("Cleanup", True, "No cleanup needed")

        except Exception as e:
            self.log_step("Cleanup", False, str(e))

    async def run(self):
        """Exécuter le debug complet."""
        print("\n" + "=" * 60)
        print("🔬 TRADER DEEP DEBUG - FULL TRADE LIFECYCLE")
        print("=" * 60)
        print(f"Start Time: {datetime.now()}")
        print("=" * 60)

        # Step 1: Load config
        config_data = await self.step_1_load_config()
        if not config_data:
            return False

        # Step 2: Generate signal
        signal_data = await self.step_2_simulate_signal(config_data)
        if not signal_data.get("signal"):
            return False

        # Step 3: AI validation check
        validated_data = await self.step_3_ai_validation(signal_data)

        # Step 4: Open position
        position_data = await self.step_4_open_position(validated_data)
        if not position_data.get("position"):
            return False

        # Step 5: Price rises
        position_data = await self.step_5_price_rises(position_data)

        # Step 6: Price drops, SL triggers
        await self.step_6_price_drops_sl_triggers(position_data)

        # Step 7: Cleanup
        await self.step_7_cleanup(position_data)

        # Summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)

        passed = sum(1 for s in self.steps if s.passed)
        failed = sum(1 for s in self.steps if not s.passed)

        for step in self.steps:
            print(step)

        print(f"\n✅ Passed: {passed}/{len(self.steps)}")
        print(f"❌ Failed: {failed}/{len(self.steps)}")

        return failed == 0


if __name__ == "__main__":
    debug = TraderDeepDebug()
    success = asyncio.run(debug.run())
    sys.exit(0 if success else 1)
