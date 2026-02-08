from jobs.youtuber.syncer import YouTubeSyncer
from loguru import logger


def sync_en():
    logger.info("🇺🇸 Syncing EN Channel (Trinity Thinks)...")
    YouTubeSyncer(channel="en").run_sync()


if __name__ == "__main__":
    sync_en()
