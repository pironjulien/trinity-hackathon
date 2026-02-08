"""
CORPUS/SOMA/SENSES.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SENSES (INPUTS) 👁️
PURPOSE: Perceptions Externes (Le Web).
      Permet à Trinity de "lire" internet (RSS, News, Scraping léger).
DEPENDANCES: requests, beautifulsoup4 (optionnel)
══════════════════════════════════════════════════════════════════════════════
"""

import aiohttp
from typing import List, Dict
from loguru import logger


class Senses:
    """
    Yeux et Oreilles numériques de Trinity.
    """

    def __init__(self):
        pass

    async def read_url(self, url: str) -> str:
        """Lit le contenu brut (HTML/Text) d'une URL."""
        try:
            # Use transient session to prevent unclosed connection warnings
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        text = await response.text()
                        logger.info(f"👁️ [SENSES] Read {len(text)} bytes from {url}")
                        return text
                    else:
                        logger.warning(
                            f"👁️ [SENSES] Failed to read {url}: {response.status}"
                        )
                        return ""
        except Exception as e:
            logger.error(f"👁️ [SENSES] Blindness Error: {e}")
            return ""

    def _smart_truncate(self, text: str | None, limit: int) -> str:
        """
        Coupe intelligente du texte :
        1. Nettoie les balises HTML basiques.
        2. Tronque à 'limit'.
        3. Cherche la fin d'une phrase (. ! ?) ou un espace pour couper proprement.
        """
        if not text:
            return ""

        # 1. Basic Cleaning
        text = (
            text.replace("<br>", "\n")
            .replace("<br/>", "\n")
            .replace("<p>", "")
            .replace("</p>", "\n")
        )

        # Si c'est court, on renvoie tout
        if len(text) <= limit:
            return text

        # 2. Hard Truncate
        truncated = text[:limit]

        # 3. Smart Cut
        # Cherche le dernier gros séparateur (fin de phrase)
        last_punct = max(
            truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?")
        )

        if last_punct != -1 and last_punct > limit * 0.5:
            # On coupe au séparateur trouvé (incluant le caractère)
            return truncated[: last_punct + 1]

        # Fallback: coupe au dernier espace
        last_space = truncated.rfind(" ")
        if last_space != -1:
            return truncated[:last_space] + "..."

        return truncated + "..."

    async def scan_rss(self, feed_url: str) -> List[Dict]:
        """Lit un flux RSS (Structure simple XML) et retourne des items structurés."""
        content = await self.read_url(feed_url)
        if not content:
            return []

        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(content)

            # Auto-detect RSS vs Atom (simple heuristic)
            items = []

            # Standard RSS 2.0 <item> under <channel>
            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                desc = item.find("description")

                raw_desc = desc.text if desc is not None else ""

                items.append(
                    {
                        "title": title.text if title is not None else "No Title",
                        "link": link.text if link is not None else feed_url,
                        "summary": self._smart_truncate(raw_desc, 500),
                    }
                )

            # Atom <entry> (fallback if RSS didn't work and we have entries)
            if not items and root.tag.endswith("feed"):
                for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                    title = entry.find("{http://www.w3.org/2005/Atom}title")
                    link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
                    summary = entry.find("{http://www.w3.org/2005/Atom}summary")

                    link_href = (
                        link_elem.get("href") if link_elem is not None else feed_url
                    )
                    raw_summary = summary.text if summary is not None else ""

                    items.append(
                        {
                            "title": title.text if title is not None else "No Title",
                            "link": link_href,
                            "summary": self._smart_truncate(raw_summary, 500),
                        }
                    )

            if items:
                logger.info(f"👁️ [SENSES] Parsed {len(items)} items from RSS.")
                return items
            else:
                logger.warning("👁️ [SENSES] No items found in XML.")
                return [{"raw": content[:200] + "...", "error": "No items found"}]

        except Exception as e:
            logger.warning(f"👁️ [SENSES] XML Parse Failed ({e}), returning raw snippet.")
            return [{"raw": content[:500] + "...", "error": str(e)}]


# Singleton
senses = Senses()
