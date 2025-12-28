"""
Automatic Memory Archival Worker (Chunk 5.6)
Runs periodically to archive old memories to disk.

Features:
- Runs daily at configured time
- Archives memories older than 30 days
- Keeps most recent 1000 memories in Redis
- Logs archival statistics
"""

import asyncio
import logging
from datetime import datetime, time as datetime_time

from memory.cold_storage import ColdStorageManager
from config import config


logger = logging.getLogger(__name__)


class MemoryArchiver:
    """Background worker for automatic memory archival"""

    def __init__(self):
        self.storage_manager = ColdStorageManager()
        self.running = False
        self.task = None

    async def start(self):
        """Start the archival worker"""
        if self.running:
            logger.warning("[Archiver] Worker already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_worker())
        logger.info("[Archiver] Memory archival worker started")

    async def stop(self):
        """Stop the archival worker"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("[Archiver] Memory archival worker stopped")

    async def _run_worker(self):
        """Main worker loop"""
        while self.running:
            try:
                # Wait until next scheduled time
                await self._wait_until_next_run()

                if not self.running:
                    break

                # Run archival
                logger.info("[Archiver] Starting scheduled memory archival...")
                result = self.storage_manager.archive_old_memories(
                    days_threshold=config.ARCHIVE_DAYS_THRESHOLD,
                    keep_recent=config.ARCHIVE_KEEP_RECENT
                )

                logger.info(
                    f"[Archiver] Archival complete: "
                    f"{result['archived']} archived, "
                    f"{result['kept_in_redis']} kept in Redis, "
                    f"{result['files_created']} files created"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Archiver] Error during archival: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(3600)  # 1 hour

    async def _wait_until_next_run(self):
        """Wait until next scheduled archival time"""
        now = datetime.now()
        target_time = datetime_time(
            hour=config.ARCHIVE_HOUR,
            minute=config.ARCHIVE_MINUTE
        )

        # Calculate next run time
        next_run = datetime.combine(now.date(), target_time)

        # If target time has passed today, schedule for tomorrow
        if next_run <= now:
            from datetime import timedelta
            next_run += timedelta(days=1)

        # Calculate wait time
        wait_seconds = (next_run - now).total_seconds()

        logger.info(
            f"[Archiver] Next archival scheduled for {next_run.isoformat()} "
            f"(in {wait_seconds / 3600:.1f} hours)"
        )

        await asyncio.sleep(wait_seconds)

    async def run_manual_archival(self) -> dict:
        """
        Manually trigger archival (for admin endpoint).

        Returns:
            Archival result dictionary
        """
        logger.info("[Archiver] Manual archival triggered")
        result = self.storage_manager.archive_old_memories(
            days_threshold=config.ARCHIVE_DAYS_THRESHOLD,
            keep_recent=config.ARCHIVE_KEEP_RECENT
        )
        logger.info(
            f"[Archiver] Manual archival complete: "
            f"{result['archived']} archived, {result['kept_in_redis']} kept"
        )
        return result


# Global instance
archiver = MemoryArchiver()
