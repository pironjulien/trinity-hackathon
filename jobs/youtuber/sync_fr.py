from jobs.youtuber.syncer import YouTubeSyncer
from loguru import logger


def sync_fr():
    logger.info("🇫🇷 Syncing FR Channel (Trinity IA)...")
    YouTubeSyncer(channel="fr").run_sync()


if __name__ == "__main__":
    sync_fr()
