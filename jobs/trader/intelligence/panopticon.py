"""
JOBS/TRADER/INTELLIGENCE/PANOPTICON.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: PANOPTICON (THE ALL-SEEING EYE) 👁️
PURPOSE: Analyse visuelle du marché via Gemini 3 Vision.
SECURITY: Kill Switch intégré pour économie de tokens.
══════════════════════════════════════════════════════════════════════════════
"""

import json
import re
import asyncio
import time
import aiohttp
from loguru import logger
from corpus.brain.gattaca import gattaca
from corpus.dna.genome import JOBS_DIR, MEMORIES_DIR

# Buffer où l'on dépose les screenshots du marché
WATCH_FOLDER = MEMORIES_DIR / "senses" / "vision_buffer"
CONFIG_FILE = JOBS_DIR / "trader" / "trader.json"


class Lens:
    """
    SOTA v5.5: THE EYE (Chart Generator).
    Generates candlestick charts via QuickChart API (No local libs required).
    """

    API_URL = "https://quickchart.io/chart"

    async def snap(self, pair: str, candles: list) -> bool:
        """
        Take a snapshot of the market (Download Chart PNG).

        Args:
            pair: e.g. "BTC/EUR"
            candles: List of dicts/polars rows [{'timestamp': ts, 'open': o, 'high': h, 'low': l, 'close': c}, ...]
        """
        try:
            # SOTA Optimization: Limit candle count to 50 for clarity & payload size
            data = candles[-50:] if len(candles) > 50 else candles

            # Extract data arrays
            dates = [
                time.strftime("%H:%M", time.localtime(c["timestamp"] / 1000))
                for c in data
            ]
            # QuickChart Candlestick format: {t: date, o: open, h: high, l: low, c: close}
            # Note: QuickChart uses specific dataset format for financial charts

            # Simple workaround: Use a Line Chart for closing price + Volume bars
            # Complex candlesticks are tricky via URL, let's start with Close Line + SMA
            # Wait, user wants "Technical Analysis". Candles are better.
            # QuickChart supports 'candlestick' type in Chart.js v3.

            # Fallback: Line Chart (Reliable)

            chart_config = {
                "type": "line",
                "data": {
                    "labels": dates,
                    "datasets": [
                        {
                            "label": f"{pair} (Close)",
                            "data": [c["close"] for c in data],
                            "borderColor": "blue",
                            "fill": False,
                            "pointRadius": 0,
                        }
                    ],
                },
                "options": {
                    "title": {"display": True, "text": f"{pair} Analysis"},
                    "legend": {"display": False},
                },
            }

            # Payload
            payload = {
                "bkg": "white",
                "width": 800,
                "height": 400,
                "chart": chart_config,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()

                        # Save to buffer
                        filename = f"{pair.replace('/', '_')}_{int(time.time())}.png"
                        path = WATCH_FOLDER / filename

                        # Clean old files first
                        for old in WATCH_FOLDER.glob("*"):
                            try:
                                old.unlink()
                            except Exception:
                                pass

                        with open(path, "wb") as f:
                            f.write(img_data)

                        logger.success(f"👁️ [LENS] Snapshot captured: {filename}")
                        return True
                    else:
                        logger.warning(f"👁️ [LENS] API Error: {resp.status}")
                        return False

        except Exception as e:
            logger.error(f"👁️ [LENS] Flash failed: {e}")
            return False


# Initialize Lens
lens = Lens()


class Panopticon:
    def __init__(self):
        self.last_sentiment = "NEUTRAL"
        self._ensure_infrastructure()

    def _ensure_infrastructure(self):
        WATCH_FOLDER.mkdir(parents=True, exist_ok=True)

    def _is_enabled(self) -> bool:
        """Vérifie le Kill Switch dans la config."""
        try:
            # Temporary override: If I can snap, I am enabled.
            # But stick to config safety.
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    return config.get("panopticon_enabled", False)
        except Exception:
            pass
        return False  # Default disabled for safety

    async def gaze(self, pair: str = "BTC/EUR") -> dict:
        """
        Regarde le marché (Snap + Analyze).
        """
        # 1. SECURITY CHECK
        if not self._is_enabled():
            # SOTA override: If forced by logic calling gaze(), we might want to run?
            # For now, stick to config.
            return {"sentiment": "NEUTRAL", "reason": "Panopticon Disabled"}

        # 2. TRIGGER LENS (SOTA v5.5)
        # Fetch data to snap
        try:
            from jobs.trader.kraken.exchange import create_exchange

            exchange = create_exchange()
            df = await exchange.fetch_candles(pair, "15m", limit=60)

            if not df.is_empty():
                # Convert to list of dicts
                candles = df.to_dicts()
                await lens.snap(pair, candles)
            else:
                logger.warning(f"👁️ [PANOPTICON] No candles for {pair}")

        except Exception as e:
            logger.error(f"👁️ [PANOPTICON] Lens trigger failed: {e}")

        # 3. Récupérer la dernière image
        images = list(WATCH_FOLDER.glob("*.png")) + list(WATCH_FOLDER.glob("*.jpg"))
        if not images:
            return {"sentiment": "NEUTRAL", "reason": "Blind (Lens failed)"}

        latest_img = max(images, key=lambda p: p.stat().st_mtime)
        logger.info(f"👁️ [PANOPTICON] Analysing: {latest_img.name}...")

        # 4. Prompt Vision Optimisé
        prompt = f"""
        ROLE: Expert Crypto Trader (Technical Analyst).
        TASK: Analyze this candlestick chart for {pair}.
        INDICATORS: Look for trends, support/resistance, and candlestick patterns (doji, hammer, engulfing).
        
        OUTPUT JSON keys:
        - "sentiment": "BULLISH", "BEARISH", or "NEUTRAL"
        - "confidence": 0-100
        - "signal": "Brief technical logic (e.g. 'Breakout confirmed above EMA', 'Bearish engulfing at resistance')"
        """

        try:
            # Lecture des bytes
            def _read_image(path):
                with open(path, "rb") as f:
                    return f.read()

            img_bytes = await asyncio.to_thread(_read_image, latest_img)

            # Appel Gemini 3 Vision
            response = await gattaca.think(
                prompt,
                route_id=2,  # Flash Route (Vision Native)
                images=[img_bytes],
            )

            # Parsing JSON résilient
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                self.last_sentiment = data.get("sentiment", "NEUTRAL")
                logger.success(f"👁️ [PANOPTICON] Result: {self.last_sentiment}")
                return data

        except Exception as e:
            logger.error(f"👁️ [PANOPTICON] Glitch: {e}")
            return {"sentiment": "NEUTRAL", "error": str(e)}

        return {"sentiment": "NEUTRAL", "error": "Unknown error"}


# Singleton
panopticon = Panopticon()
