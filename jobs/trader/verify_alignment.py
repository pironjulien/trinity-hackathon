#!/usr/bin/env python3
"""
🔍 FRONTEND-BACKEND ALIGNMENT VERIFICATION

Vérifie que:
1. positions.json a les bons SL
2. trader_cache.json a les mêmes SL
3. API /api/trader/status retourne les bons SL
4. Le frontend n'a pas besoin de fallback
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class VerificationResult:
    step: str
    passed: bool
    details: str
    data: Dict = None


class AlignmentVerifier:
    def __init__(self):
        self.results: List[VerificationResult] = []
        self.base = Path("/home/julienpiron_fr/trinity/memories/trader")

    def log(self, step: str, passed: bool, details: str, data: Dict = None):
        result = VerificationResult(step, passed, details, data)
        self.results.append(result)
        emoji = "✅" if passed else "❌"
        print(f"\n{emoji} {step}")
        print(f"   {details}")
        if data:
            for k, v in data.items():
                print(f"   📊 {k}: {v}")

    def verify_positions_json(self) -> Dict[str, float]:
        """1. Vérifier positions.json"""
        print("\n" + "=" * 60)
        print("1️⃣ POSITIONS.JSON (Source of Truth)")
        print("=" * 60)

        file = self.base / "positions.json"
        data = json.loads(file.read_text())

        sl_values = {}
        has_zero = False

        for pos in data.get("positions", []):
            pair = pos.get("pair")
            sl = pos.get("stop_loss", 0)
            entry = pos.get("entry_price", 0)
            sl_pct = ((sl / entry) - 1) * 100 if entry > 0 else 0
            sl_values[pair] = sl

            if sl == 0:
                has_zero = True
            print(f"   {pair}: SL={sl:.6f} ({sl_pct:+.2f}%)")

        self.log(
            "positions.json",
            not has_zero,
            f"{len(sl_values)} positions, all have SL > 0: {not has_zero}",
            {"Positions with SL=0": sum(1 for v in sl_values.values() if v == 0)},
        )

        return sl_values

    def verify_cache_json(self, source_sl: Dict[str, float]) -> bool:
        """2. Vérifier trader_cache.json matches positions.json"""
        print("\n" + "=" * 60)
        print("2️⃣ TRADER_CACHE.JSON (API Source)")
        print("=" * 60)

        file = self.base / "trader_cache.json"
        data = json.loads(file.read_text())

        mismatches = []
        positions = data.get("positions", {})

        for pair, pos in positions.items():
            cache_sl = pos.get("stop_loss", 0)
            source = source_sl.get(pair, 0)

            match = abs(cache_sl - source) < 0.000001
            status = "✓" if match else "✗"
            print(f"   {pair}: cache={cache_sl:.6f} vs source={source:.6f} [{status}]")

            if not match:
                mismatches.append(pair)

        self.log(
            "Cache Sync",
            len(mismatches) == 0,
            f"Cache matches positions.json: {len(mismatches) == 0}",
            {"Mismatches": mismatches if mismatches else "None"},
        )

        return len(mismatches) == 0

    def verify_frontend_fallback(self) -> bool:
        """3. Vérifier que le frontend n'utilise pas de fallback"""
        print("\n" + "=" * 60)
        print("3️⃣ FRONTEND FALLBACK CHECK")
        print("=" * 60)

        file = self.base / "trader_cache.json"
        data = json.loads(file.read_text())

        zero_sl_positions = []
        for pair, pos in data.get("positions", {}).items():
            if pos.get("stop_loss", 0) == 0:
                zero_sl_positions.append(pair)

        if zero_sl_positions:
            print(f"   ⚠️ Frontend will use FALLBACK for: {zero_sl_positions}")
            print("   → These positions show CALCULATED SL, not real SL!")
        else:
            print("   ✓ All positions have real SL - no fallback needed")

        self.log(
            "Frontend Fallback",
            len(zero_sl_positions) == 0,
            f"No fallback needed: {len(zero_sl_positions) == 0}",
            {"Positions needing fallback": zero_sl_positions},
        )

        return len(zero_sl_positions) == 0

    def verify_config_strategy(self):
        """4. Vérifier la config active"""
        print("\n" + "=" * 60)
        print("4️⃣ ACTIVE CONFIG STRATEGY")
        print("=" * 60)

        try:
            import sys

            sys.path.insert(0, str(Path("/home/julienpiron_fr/trinity")))
            from jobs.trader.config import TraderConfig

            config = TraderConfig.load()
            strategy = config.get_strategy()

            sl = strategy.stop_loss * 100 if hasattr(strategy, "stop_loss") else 0
            tp = strategy.tp1 * 100 if hasattr(strategy, "tp1") else 0

            data = {
                "Mode": config.mode,
                "Level": getattr(config, "level", 0),
                "Stop Loss": f"{sl:.2f}%",
                "Take Profit": f"{tp:.2f}%",
            }

            self.log(
                "Config Strategy",
                sl != 0 and tp != 0,
                f"Mode={config.mode}, SL={sl:.2f}%, TP={tp:.2f}%",
                data,
            )

        except Exception as e:
            self.log("Config Strategy", False, str(e))

    def run(self) -> bool:
        print("\n" + "=" * 60)
        print("🔍 FRONTEND-BACKEND ALIGNMENT VERIFICATION")
        print("=" * 60)

        # 1. Positions.json
        source_sl = self.verify_positions_json()

        # 2. Cache matches source
        self.verify_cache_json(source_sl)

        # 3. Frontend fallback
        self.verify_frontend_fallback()

        # 4. Config
        self.verify_config_strategy()

        # Summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        for r in self.results:
            emoji = "✅" if r.passed else "❌"
            print(f"{emoji} {r.step}: {r.details}")

        print(f"\n✅ Passed: {passed}/{len(self.results)}")
        print(f"❌ Failed: {failed}/{len(self.results)}")

        return failed == 0


if __name__ == "__main__":
    verifier = AlignmentVerifier()
    success = verifier.run()
    exit(0 if success else 1)
