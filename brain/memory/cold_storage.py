"""
Cold Storage Archive Manager (Chunk 5.6)
Manages long-term memory archival to disk for memories older than 30 days.

Features:
- Archive old memories to JSON files (YYYY-MM format)
- Keep only recent 1000 memories in Redis
- Search archived memories (slower, file-based)
- Preserve all memory fields
- Organized by month directories
"""

import json
import os
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import redis

from config import config

logger = logging.getLogger(__name__)


class ColdStorageManager:
    """Manages memory archival to disk"""

    def __init__(self, archive_dir: str = "data/archive"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        # Don't decode responses - handle decoding manually to avoid binary data issues
        self.redis_client = redis.from_url(config.REDIS_URL, decode_responses=False)

    def get_archive_path(self, timestamp: int) -> Path:
        """
        Get archive file path for a given timestamp.

        Args:
            timestamp: Unix timestamp

        Returns:
            Path to archive file (YYYY-MM/memories-YYYYMMDD.json)
        """
        dt = datetime.fromtimestamp(timestamp)
        month_dir = self.archive_dir / dt.strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)
        filename = f"memories-{dt.strftime('%Y%m%d')}.json"
        return month_dir / filename

    def archive_old_memories(self, days_threshold: int = 30, keep_recent: int = 1000) -> Dict[str, Any]:
        """
        Archive memories older than threshold to disk.

        Args:
            days_threshold: Archive memories older than this many days
            keep_recent: Keep this many most recent memories in Redis

        Returns:
            Dictionary with archive statistics
        """
        cutoff_timestamp = int((datetime.now() - timedelta(days=days_threshold)).timestamp())

        # Get all memory keys (exclude index keys)
        # Use scan_iter() instead of keys() for non-blocking iteration
        memory_keys = []
        for key in self.redis_client.scan_iter(match=f"{config.REDIS_MEMORY_PREFIX}*", count=100):
            # Decode and filter
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            if not key_str.endswith("_index") and ":" in key_str:
                memory_keys.append(key)

        if not memory_keys:
            return {
                "archived": 0,
                "kept_in_redis": 0,
                "files_created": 0,
                "error": None
            }

        # Load all memories with timestamps
        # NOTE: There's a race condition window between keys() and hgetall()
        # where keys could be deleted or new ones added. We handle this by:
        # 1. Skipping keys that no longer exist (empty hgetall)
        # 2. Re-validating key count before archival decisions
        memories_with_time = []
        for key in memory_keys:
            memory_data_raw = self.redis_client.hgetall(key)
            if not memory_data_raw:
                # Key was deleted between keys() and hgetall(), skip it
                continue

            # Decode bytes to strings, preserve binary fields (like embeddings) as base64
            memory_data = {}
            for k, v in memory_data_raw.items():
                key_str = k.decode('utf-8') if isinstance(k, bytes) else k
                try:
                    val_str = v.decode('utf-8') if isinstance(v, bytes) else v
                    memory_data[key_str] = val_str
                except UnicodeDecodeError:
                    # Binary field (like embedding) - encode as base64 for JSON storage
                    if isinstance(v, bytes):
                        memory_data[key_str] = {
                            "_binary": True,
                            "data": base64.b64encode(v).decode('utf-8')
                        }
                    else:
                        # Skip non-bytes binary data
                        pass

            if "timestamp" in memory_data:
                # Handle both int and float timestamps
                timestamp = int(float(memory_data["timestamp"]))
                memories_with_time.append({
                    "key": key.decode('utf-8') if isinstance(key, bytes) else key,
                    "timestamp": timestamp,
                    "data": memory_data
                })

        # Sort by timestamp (oldest first)
        memories_with_time.sort(key=lambda x: x["timestamp"])

        # Re-check count after loading (race condition mitigation)
        # Some keys might have been deleted/added since initial scan
        total_memories = len(memories_with_time)

        if total_memories == 0:
            return {
                "archived": 0,
                "kept_in_redis": 0,
                "files_created": 0,
                "error": None
            }

        # Determine which to archive
        # Keep most recent 'keep_recent' memories regardless of age
        # Archive anything older than cutoff_timestamp that's not in recent set
        recent_cutoff_index = max(0, total_memories - keep_recent)

        to_archive = []
        to_keep = []

        for i, mem in enumerate(memories_with_time):
            # Keep if in recent set OR newer than cutoff
            if i >= recent_cutoff_index or mem["timestamp"] >= cutoff_timestamp:
                to_keep.append(mem)
            else:
                to_archive.append(mem)

        # Archive old memories
        archived_count = 0
        files_created = set()

        for mem in to_archive:
            try:
                archive_path = self.get_archive_path(mem["timestamp"])

                # Load existing archive file or create new list
                if archive_path.exists():
                    with open(archive_path, 'r') as f:
                        archived_memories = json.load(f)
                else:
                    archived_memories = []

                # Add memory to archive
                archived_memories.append(mem["data"])

                # Write to temporary file first (atomic operation)
                temp_path = archive_path.with_suffix('.tmp')
                with open(temp_path, 'w') as f:
                    json.dump(archived_memories, f, indent=2)

                # Verify temp file was written successfully
                if not temp_path.exists() or temp_path.stat().st_size == 0:
                    raise IOError(f"Failed to write archive file: {archive_path}")

                # Atomic rename (overwrites existing file safely)
                temp_path.replace(archive_path)

                # Only NOW safe to delete from Redis (after successful write+verify)
                # Check if key still exists before deleting (race condition mitigation)
                if self.redis_client.exists(mem["key"]):
                    self.redis_client.delete(mem["key"])
                else:
                    # Key was already deleted by another process, log warning
                    logger.warning("Key %s already deleted before archival", mem['key'])

                archived_count += 1
                files_created.add(str(archive_path))

            except Exception as e:
                # Log error but continue with other memories
                logger.error("Error archiving memory %s: %s", mem['key'], e)

        return {
            "archived": archived_count,
            "kept_in_redis": len(to_keep),
            "files_created": len(files_created),
            "archive_files": sorted(list(files_created)),
            "error": None
        }

    def search_archive(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search archived memories (slow, scans JSON files).

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of matching memories from archive
        """
        query_lower = query.lower()
        results = []

        # Scan all archive files
        for month_dir in sorted(self.archive_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue

            for archive_file in sorted(month_dir.glob("memories-*.json"), reverse=True):
                try:
                    # Check file size to prevent memory exhaustion
                    file_size = archive_file.stat().st_size
                    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

                    if file_size > MAX_FILE_SIZE:
                        logger.warning("Skipping large archive file %s (%.1fMB)",
                                     archive_file.name, file_size / 1024 / 1024)
                        continue

                    with open(archive_file, 'r') as f:
                        memories = json.load(f)

                    # Search within this archive
                    for memory in memories:
                        message = memory.get("message", "").lower()
                        if query_lower in message:
                            results.append(memory)

                            if len(results) >= max_results:
                                return results

                except Exception as e:
                    logger.error("Error reading archive %s: %s", archive_file, e)

        return results

    def get_archive_stats(self) -> Dict[str, Any]:
        """
        Get statistics about archived memories.

        Returns:
            Dictionary with archive statistics
        """
        total_files = 0
        total_memories = 0
        oldest_date = None
        newest_date = None

        for month_dir in self.archive_dir.iterdir():
            if not month_dir.is_dir():
                continue

            for archive_file in month_dir.glob("memories-*.json"):
                try:
                    with open(archive_file, 'r') as f:
                        memories = json.load(f)

                    total_files += 1
                    total_memories += len(memories)

                    # Track date range
                    if memories:
                        for mem in memories:
                            timestamp = int(mem.get("timestamp", 0))
                            if timestamp > 0:
                                if oldest_date is None or timestamp < oldest_date:
                                    oldest_date = timestamp
                                if newest_date is None or timestamp > newest_date:
                                    newest_date = timestamp

                except Exception as e:
                    logger.error("Error reading archive %s: %s", archive_file, e)

        return {
            "total_archive_files": total_files,
            "total_archived_memories": total_memories,
            "oldest_archive_date": datetime.fromtimestamp(oldest_date).isoformat() if oldest_date else None,
            "newest_archive_date": datetime.fromtimestamp(newest_date).isoformat() if newest_date else None,
            "archive_directory": str(self.archive_dir)
        }

    def restore_from_archive(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Restore memories from archive back to Redis (admin function).

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with restoration statistics
        """
        start_timestamp = int(datetime.fromisoformat(start_date).timestamp())
        end_timestamp = int(datetime.fromisoformat(end_date).timestamp())

        restored_count = 0

        for month_dir in self.archive_dir.iterdir():
            if not month_dir.is_dir():
                continue

            for archive_file in month_dir.glob("memories-*.json"):
                try:
                    with open(archive_file, 'r') as f:
                        memories = json.load(f)

                    for memory in memories:
                        timestamp = int(memory.get("timestamp", 0))

                        if start_timestamp <= timestamp <= end_timestamp:
                            # Restore to Redis
                            memory_id = memory.get("id", f"restored_{timestamp}")
                            key = f"{config.REDIS_MEMORY_PREFIX}{memory_id}"

                            # Decode binary fields (embeddings) from base64
                            restored_memory = {}
                            for field_key, field_value in memory.items():
                                if isinstance(field_value, dict) and field_value.get("_binary"):
                                    # Decode base64 back to bytes
                                    restored_memory[field_key] = base64.b64decode(field_value["data"])
                                else:
                                    restored_memory[field_key] = field_value

                            # Store in Redis
                            self.redis_client.hset(key, mapping=restored_memory)
                            restored_count += 1

                except Exception as e:
                    logger.error("Error restoring from %s: %s", archive_file, e)

        return {
            "restored": restored_count,
            "date_range": f"{start_date} to {end_date}"
        }
