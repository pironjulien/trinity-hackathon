#!/usr/bin/env python3
"""
Trinity Immune System Scanner (Manual Trigger)
Wraps corpus.soma.immune.scan()
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))


async def main():
    from corpus.soma.immune import immune

    success = await immune.scan()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
