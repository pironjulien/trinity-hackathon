from jobs.youtuber.syncer import YouTubeSyncer
from loguru import logger


def force_sync():
    logger.info("🇺🇸 Syncing EN...")
    YouTubeSyncer(channel="en").run_sync()

    logger.info("🇫🇷 Syncing FR...")
    YouTubeSyncer(channel="fr").run_sync()


if __name__ == "__main__":
    force_sync()
