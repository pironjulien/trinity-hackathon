"""
JOBS/TRADER/DATA/PULSE.PY
==============================================================================
MODULE: MARKET PULSE (Sentiment Oracle) 💓
PURPOSE: Multi-source sentiment fusion (FNG, BTC trend, volume, AI).
==============================================================================
"""

import time
import aiohttp
from typing import Dict, Tuple
from corpus.soma.nerves import logger  # SOTA: DEBUG level

from corpus.soma.cells import save_json, load_json
from corpus.dna.genome import MEMORIES_DIR
from jobs.trader.config import TraderConfig


PULSE_FILE = MEMORIES_DIR / "trader" / "pulse.json"
FNG_API_URL = "https://api.alternative.me/fng/"
CACHE_DURATION = 3600 * 24  # 24 hours


class MarketPulse:
    """
    Sentiment Oracle - Multi-source fusion.

    Sources:
    - Fear & Greed Index (API)
    - BTC 24h trend
    - Volume ratio
    - AI analysis (optional)
    """

    def __init__(self):
        self._state: Dict = self._load()
        self._btc_24h: float = 0.0
        self._volume_ratio: float = 1.0

    def _load(self) -> Dict:
        """Load cached pulse state."""
        return load_json(
            PULSE_FILE, default={"score": 50, "reason": "Neutral", "timestamp": 0}
        )

    def _save(self) -> None:
        """Persist pulse state."""
        save_json(PULSE_FILE, self._state)

    @property
    def score(self) -> int:
        """Current sentiment score (0-100)."""
        return self._state.get("score", 50)

    @property
    def reason(self) -> str:
        """Reason for current score."""
        return self._state.get("reason", "Neutral")

    @property
    def btc_24h(self) -> float:
        """Get BTC 24h change percentage."""
        return self._btc_24h

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA FETCHING
    # ═══════════════════════════════════════════════════════════════════════════

    async def _fetch_fng(self) -> Dict:
        """Fetch Fear & Greed Index from API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(FNG_API_URL, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "data" in data and len(data["data"]) > 0:
                            item = data["data"][0]
                            return {
                                "value": int(item["value"]),
                                "label": item["value_classification"],
                            }
        except Exception as e:
            logger.warning(f"💓 [PULSE] FNG API failed: {e}")

        return {"value": 50, "label": "Neutral"}

    # ═══════════════════════════════════════════════════════════════════════════
    # PULSE UPDATE
    # ═══════════════════════════════════════════════════════════════════════════

    async def update(self, force: bool = False) -> Dict:
        """
        Update market pulse.

        Args:
            force: Force update even if cache is valid

        Returns:
            Updated state dict
        """
        # Check cache
        if not force and time.time() - self._state["timestamp"] < CACHE_DURATION:
            return self._state

        logger.info("💓 [PULSE] Updating...")

        # 1. Fetch FNG
        fng = await self._fetch_fng()

        # 2. Check if AI is enabled
        config = TraderConfig.load()

        if not config.ai_enabled:
            # Simple FNG-only mode
            self._state = {
                "score": fng["value"],
                "reason": f"FNG: {fng['label']}",
                "news": None,
                "recommendation": "neutral",
                "timestamp": time.time(),
            }
            self._save()
            logger.success(f"💓 [PULSE] FNG: {fng['value']}/100 ({fng['label']})")
            return self._state

        # 3. AI-enhanced pulse
        try:
            from corpus.brain.gattaca import gattaca
            import json

            prompt = f"""
TASK: Crypto Market Pulse Analysis

CURRENT DATA:
- Fear & Greed Index: {fng["value"]}/100 ({fng["label"]})

ANALYZE:
1. NEWS CATALYSTS: Major crypto news today
2. SOCIAL SENTIMENT: Overall crypto mood
3. MARKET ASSESSMENT: bullish/bearish/neutral

OUTPUT JSON ONLY:
{{
    "score": 0-100,
    "reason": "Brief explanation",
    "news_headline": "Most important news or null",
    "recommendation": "risk_on/risk_off/neutral"
}}
"""
            # SOTA 2026: Route 1 (CLI) - Reliable Reasoning
            # Explicit F233 (233s) timeout for Route 1 (Pro is slower)
            import asyncio

            response = await asyncio.wait_for(
                gattaca.think(prompt, route_id=1),
                timeout=233,
            )

            # SOTA v4.7: Robust JSON Parsing & Error Handling
            if not response or "ERROR" in response[:20] or "Quota" in response:
                raise ValueError(f"AI Error: {response[:100]}")

            clean = response.replace("```json", "").replace("```", "").strip()

            try:
                data = json.loads(clean)
            except json.JSONDecodeError:
                # Fallback: Attempt to repair/find JSON
                import re

                match = re.search(r"\{.*\}", clean, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                else:
                    raise ValueError(f"Invalid JSON format: {clean[:100]}")

            self._state = {
                "score": data.get("score", fng["value"]),
                "reason": data.get("reason", fng["label"]),
                "news": data.get("news_headline"),
                "recommendation": data.get("recommendation", "neutral"),
                "timestamp": time.time(),
            }
            self._save()

            emoji = (
                "🟢"
                if self._state["score"] >= 60
                else ("🔴" if self._state["score"] <= 40 else "⚪")
            )
            logger.success(
                f"💓 [PULSE] {emoji} {self._state['score']}/100 | {self._state['reason']}"
            )

        except Exception as e:
            logger.warning(f"💓 [PULSE] AI failed, using FNG: {e}")
            self._state = {
                "score": fng["value"],
                "reason": fng["label"],
                "timestamp": time.time(),
            }
            self._save()

        return self._state

    async def get_oracle_score(
        self, btc_24h: float = 0.0, volume_ratio: float = 1.0
    ) -> Tuple[float, str]:
        """
        Calculate PHI-weighted sentiment score.

        Sources (PHI-weighted):
        - FNG Index: 0.382
        - BTC 24h trend: 0.236
        - Volume trend: 0.236
        - Base sentiment: 0.146

        Returns:
            (oracle_score, regime)
        """
        self._btc_24h = btc_24h
        self._volume_ratio = volume_ratio

        fng_score = self._state.get("score", 50)

        # BTC trend score (0-100)
        btc_score = 50 + (btc_24h * 10)
        btc_score = max(0, min(100, btc_score))

        # Volume score
        volume_score = 50 + ((volume_ratio - 1) * 25)
        volume_score = max(0, min(100, volume_score))

        base_score = self._state.get("score", 50)

        # PHI-weighted fusion
        oracle_score = (
            fng_score * 0.382
            + btc_score * 0.236
            + volume_score * 0.236
            + base_score * 0.146
        )

        # Determine regime
        if oracle_score >= 70:
            regime = "GREED"
        elif oracle_score <= 30:
            regime = "FEAR"
        else:
            regime = "NEUTRAL"

        logger.debug(f"🔮 [ORACLE] {oracle_score:.1f} ({regime})")
        return oracle_score, regime

    async def trigger_dopamine(self, event: str, value: float) -> None:
        """
        Dopamine shot - triggered by trading wins.
        Sends signal to Avatar via Socket Manager.
        """
        logger.success(f"💉 [DOPAMINE] {event}: {value}")

        try:
            from social.web.socket_manager import socket_manager  # type: ignore[import-not-found]

            await socket_manager.emit(
                "DOPAMINE",
                {
                    "type": "VICTORY",
                    "event": event,
                    "value": value,
                    "intensity": min(1.0, value / 100),
                },
            )
        except Exception:
            pass

        # Temporary score boost
        self._state["score"] = min(100, self._state["score"] + 10)
        self._state["reason"] = f"Dopamine: {event}"


def create_pulse() -> MarketPulse:
    """Factory function to create MarketPulse."""
    return MarketPulse()
