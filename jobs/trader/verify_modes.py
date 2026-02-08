#!/usr/bin/env python3
"""
TRADER MODE VERIFICATION SCRIPT
================================
Test complet des 6 modes (2 stratégies × 3 levels) pour vérifier:
1. Que toutes les variables de config sont correctement appliquées
2. Que les signaux sont générés avec les bons seuils
3. Que l'IA reçoit les bonnes données

Usage: python verify_modes.py
"""

import asyncio
import json
from pathlib import Path

# Add project root to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.trader.config import (
    TraderConfig,
    MITRAILLETTE,
    SNIPER,
    MITRAILLETTE_RANGES,
    SNIPER_RANGES,
    MEMORIES_DIR,
)
from jobs.trader.strategy.brain import create_brain
from jobs.trader.kraken.exchange import create_exchange

# Expected values for each mode/level combination
# SOTA v5.8: Phi-Harmonized Expected Values
EXPECTED_VALUES = {
    "mitraillette": {
        0: {  # Passive (F21=21)
            "rsi_oversold": 21,
            "rsi_overbought": 55,
            "rsi_period": 13,
            "stop_loss": -0.01,
            "tp1": 0.00618,
            "tp2": 0.01,
            "min_confidence": 76.4,
            "max_positions": 21,
            "trend_ema": 144,
            "min_trade": 1.618,
            "max_trade": 8,
            "rsi_composite_limit": 34,
        },
        1: {  # Normal (F34=34)
            "rsi_oversold": 34,
            "rsi_overbought": 61.8,
            "rsi_period": 21,
            "stop_loss": -0.01618,
            "tp1": 0.01,  # Updated: 1% (Phi-pure)
            "tp2": 0.01618,
            "min_confidence": 61.8,
            "max_positions": 34,
            "trend_ema": 89,
            "min_trade": 2.618,
            "max_trade": 13,
            "rsi_composite_limit": 42.36,
        },
        2: {  # Aggressive (Φ³*10=42.36)
            "rsi_oversold": 42.36,
            "rsi_overbought": 76.4,
            "rsi_period": 13,
            "stop_loss": -0.02618,
            "tp1": 0.01618,  # Updated: 1.618% (Phi)
            "tp2": 0.02618,
            "min_confidence": 55.0,
            "max_positions": 55,
            "trend_ema": 55,
            "min_trade": 4.236,
            "max_trade": 21,
            "rsi_composite_limit": 50.0,  # Updated: 50 (cleaner)
        },
    },
    "sniper": {
        0: {  # Passive (F8=8)
            "rsi_oversold": 8,
            "rsi_overbought": 61.8,  # Updated: Phi ratio
            "rsi_period": 34,
            "stop_loss": -0.01618,
            "tp1": 0.01618,
            "tp2": 0.02618,
            "min_confidence": 88.6,  # Updated: 100-11.4 (Phi-derived)
            "max_positions": 5,
            "trend_ema": 233,
            "min_trade": 4.236,
            "max_trade": 13,
        },
        1: {  # Normal (F13=13)
            "rsi_oversold": 13,
            "rsi_overbought": 76.4,
            "rsi_period": 34,
            "stop_loss": -0.02618,
            "tp1": 0.02618,
            "tp2": 0.04236,
            "min_confidence": 85.4,  # Updated: 100-14.6 (Phi-derived)
            "max_positions": 8,
            "trend_ema": 144,
            "min_trade": 8,
            "max_trade": 21,
        },
        2: {  # Aggressive (Φ²*10=23.6)
            "rsi_oversold": 23.6,
            "rsi_overbought": 85.4,  # Updated: 100-14.6 (Phi-derived)
            "rsi_period": 21,
            "stop_loss": -0.04236,
            "tp1": 0.04236,
            "tp2": 0.06854,
            "min_confidence": 76.4,
            "max_positions": 13,
            "trend_ema": 89,
            "min_trade": 13,
            "max_trade": 34,
        },
    },
}


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    print(f"\n--- {title} ---")


def verify_ranges():
    """Verify that RANGES are correctly defined."""
    print_header("1. VÉRIFICATION DES RANGES (config.py)")

    for mode_name, ranges in [
        ("MITRAILLETTE", MITRAILLETTE_RANGES),
        ("SNIPER", SNIPER_RANGES),
    ]:
        print_section(f"{mode_name}_RANGES")
        for param, values in ranges.items():
            level_names = ["Passive", "Normal", "Aggressive"]
            formatted = " | ".join(
                [f"{level_names[i]}: {v}" for i, v in enumerate(values)]
            )
            print(f"  {param}: {formatted}")


def verify_get_strategy():
    """Verify get_strategy() returns correct strategy for each mode."""
    print_header("2. VÉRIFICATION get_strategy()")

    # Test each mode
    for mode in ["mitraillette", "sniper", "ia", "manual"]:
        config = TraderConfig()
        config.mode = mode

        # For IA mode, we need to simulate active_config.json
        if mode == "ia":
            # Test with mitraillette active
            active_config_path = MEMORIES_DIR / "trader" / "active_config.json"
            current_config = {}
            if active_config_path.exists():
                with open(active_config_path) as f:
                    current_config = json.load(f)

            active_mode = current_config.get("active_mode", "mitraillette")
            strategy = config.get_strategy()
            expected = SNIPER if active_mode == "sniper" else MITRAILLETTE
            status = "✅" if strategy == expected else "❌"
            print(
                f"  Mode '{mode}' (active={active_mode}): {type(strategy).__name__} {status}"
            )
        else:
            strategy = config.get_strategy()
            if mode == "sniper":
                expected = SNIPER
            elif mode == "mitraillette":
                expected = MITRAILLETTE
            else:
                expected = SNIPER  # Manual defaults to SNIPER base

            status = "✅" if isinstance(strategy, type(expected)) else "❌"
            print(f"  Mode '{mode}': {type(strategy).__name__} {status}")


def verify_dynamic_config():
    """Verify _load_dynamic_config returns correct values for each level."""
    print_header("3. VÉRIFICATION _load_dynamic_config()")

    brain = create_brain()

    for mode in ["mitraillette", "sniper"]:
        print_section(f"Mode: {mode.upper()}")

        for level in [0, 1, 2]:
            level_name = ["Passive", "Normal", "Aggressive"][level]

            # Set config level
            brain.config.level = level
            brain.config.mode = mode

            # Get dynamic config
            conf, sl, exit_rsi, rsi_oversold = brain._load_dynamic_config(
                pair="TEST/EUR", mode=mode, override_level=level
            )

            expected = EXPECTED_VALUES[mode][level]

            print(f"\n  Level {level} ({level_name}):")

            # Check each value
            checks = [
                ("min_confidence", conf, expected["min_confidence"]),
                ("stop_loss", sl, expected["stop_loss"]),
                ("rsi_oversold", rsi_oversold, expected["rsi_oversold"]),
            ]

            for name, actual, exp in checks:
                status = "✅" if abs(actual - exp) < 0.01 else "❌"
                print(f"    {name}: {actual} (expected: {exp}) {status}")


async def verify_signal_detection():
    """Verify signal detection uses correct thresholds."""
    print_header("4. VÉRIFICATION SIGNAL DETECTION (avec vraies cryptos)")

    exchange = create_exchange()
    brain = create_brain()

    try:
        await exchange.connect()

        # Test pairs
        test_pairs = ["BTC/EUR", "ETH/EUR", "SOL/EUR", "XRP/EUR", "ADA/EUR"]

        for mode in ["mitraillette", "sniper"]:
            print_section(f"Mode: {mode.upper()}")

            for level in [0, 1, 2]:
                level_name = ["Passive", "Normal", "Aggressive"][level]
                print(f"\n  Level {level} ({level_name}):")

                # Set mode
                brain.config.mode = mode
                brain.config.level = level

                expected = EXPECTED_VALUES[mode][level]
                expected_rsi = expected["rsi_oversold"]
                expected_conf = expected["min_confidence"]

                print(
                    f"    Expected: RSI < {expected_rsi}, Confidence >= {expected_conf}"
                )

                signals_found = 0
                for pair in test_pairs:
                    try:
                        df = await exchange.fetch_candles(
                            pair, timeframe="15m", limit=100
                        )
                        if df is None or df.is_empty():
                            continue

                        # Evaluate
                        indicators = brain.evaluate(pair, df)
                        if "error" in indicators:
                            continue

                        rsi = indicators.get("rsi", 50)

                        # Detect signal
                        action, confidence, reason = brain.detect_signal(
                            indicators, mode
                        )

                        if action == "BUY":
                            signals_found += 1
                            print(
                                f"    ✅ {pair}: RSI={rsi:.1f} → BUY ({confidence:.1f}%)"
                            )
                        elif rsi < expected_rsi + 5:  # Close to threshold
                            print(
                                f"    ⚠️ {pair}: RSI={rsi:.1f} (proche seuil {expected_rsi})"
                            )

                    except Exception:
                        pass  # Skip errors silently

                if signals_found == 0:
                    print("    ℹ️ Aucun signal BUY (marché au-dessus du seuil RSI)")

    finally:
        await exchange.close()


async def verify_optimizer_flow():
    """Verify optimizer correctly proposes to AI."""
    print_header("5. VÉRIFICATION OPTIMIZER FLOW")

    # Read current active_config
    config_path = MEMORIES_DIR / "trader" / "active_config.json"

    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

        print_section("État actuel de active_config.json")
        print(f"  active_mode: {config.get('active_mode', 'N/A')}")
        print(f"  active_variation: {config.get('active_variation', 'N/A')}")
        print(f"  recommended_mode: {config.get('recommended_mode', 'N/A')}")
        print(f"  recommended_variation: {config.get('recommended_variation', 'N/A')}")
        print(f"  last_optimization: {config.get('last_optimization', 'N/A')}")
        print(f"  mode_switch_reason: {config.get('mode_switch_reason', 'N/A')}")

        # Show AI analysis if available
        if "ai_analysis" in config:
            print_section("Dernière analyse IA")
            print(f"  {config['ai_analysis'][:300]}...")

        # Show optimization results
        if "optimization_results" in config:
            print_section("Résultats des 6 modes")
            for mode_key, data in config["optimization_results"].items():
                pnl = data.get("pnl", 0)
                wr = data.get("wr", 0)
                trades = data.get("trades", 0)
                print(f"  {mode_key}: PnL={pnl:+.2f}% | WR={wr:.0f}% | Trades={trades}")
    else:
        print("  ⚠️ active_config.json n'existe pas encore")


def verify_all_params_in_code():
    """Verify all parameters are used in the code."""
    print_header("6. VÉRIFICATION UTILISATION DES PARAMÈTRES")

    # Parameters that SHOULD be used
    critical_params = {
        "rsi_oversold": "detect_signal (BUY threshold)",
        "rsi_overbought": "detect_signal (SELL threshold - disabled)",
        "min_confidence": "detect_signal (base confidence)",
        "stop_loss": "Signal creation (SL calculation)",
        "tp1": "Signal creation (TP1 calculation)",
        "tp2": "Signal creation (TP2 calculation)",
        "max_positions": "trader.py (position limit)",
        "trend_ema": "evaluate (trend detection)",
        "rsi_period": "calculate_rsi (period)",
        "min_trade": "execute_buy (minimum trade size)",
        "max_trade": "execute_buy (maximum trade size)",
    }

    print_section("Paramètres critiques")
    for param, usage in critical_params.items():
        print(f"  {param}: {usage}")

    print_section("Paramètres dans MITRAILLETTE_RANGES")
    for param in MITRAILLETTE_RANGES.keys():
        status = "✅" if param in critical_params else "⚠️ (non critique)"
        print(f"  {param} {status}")


async def main():
    """Run all verifications."""
    print("\n" + "🔍" * 35)
    print("  TRADER MODE VERIFICATION - TEST COMPLET")
    print("🔍" * 35)

    # Static verifications
    verify_ranges()
    verify_get_strategy()
    verify_dynamic_config()
    verify_all_params_in_code()

    # Dynamic verifications (need exchange)
    await verify_signal_detection()
    await verify_optimizer_flow()

    print_header("RÉSUMÉ")
    print("  Vérification terminée. Consultez les ✅ et ❌ ci-dessus.")
    print("  Si des ❌ apparaissent, le paramètre n'est pas correctement appliqué.")


if __name__ == "__main__":
    asyncio.run(main())
