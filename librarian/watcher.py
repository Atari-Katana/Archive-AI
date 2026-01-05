"""
File Watcher Service
Watches Library-Drop directory for new files and triggers processing.
Archive-AI v7.5 - Phase 5.1
"""

import os
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from processor import DocumentProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LibraryFileHandler(FileSystemEventHandler):
    """Handles file system events for library ingestion"""

    def __init__(self, processor: DocumentProcessor, callback: Optional[Callable] = None):
        """
        Initialize file handler.

        Args:
            processor: DocumentProcessor instance
            callback: Optional callback function to call with processed chunks
        """
        super().__init__()
        self.processor = processor
        self.callback = callback
        self.supported_extensions = {'.pdf', '.txt', '.md'}

        logger.info(f"LibraryFileHandler initialized. Supported: {self.supported_extensions}")

    def on_created(self, event):
        """
        Handle file creation event.

        Args:
            event: FileSystemEvent
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        extension = file_path.suffix.lower()

        # Only process supported file types
        if extension not in self.supported_extensions:
            logger.debug(f"Ignoring unsupported file type: {file_path.name}")
            return

        logger.info(f"New file detected: {file_path.name}")

        # Wait a moment to ensure file is fully written
        time.sleep(1)

        try:
            # Process the document
            chunks = self.processor.process_document(str(file_path))

            logger.info(f"Successfully processed {file_path.name}: {len(chunks)} chunks")

            # Call callback if provided (for storage in next chunk)
            if self.callback:
                self.callback(chunks, file_path)

        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")


class LibraryWatcher:
    """Watches a directory for new library files"""

    def __init__(
        self,
        watch_dir: str,
        chunk_size: int = 250,
        chunk_overlap: int = 50,
        callback: Optional[Callable] = None
    ):
        """
        Initialize library watcher.

        Args:
            watch_dir: Directory to watch for new files
            chunk_size: Token size for chunks
            chunk_overlap: Overlap tokens between chunks
            callback: Optional callback for processed chunks
        """
        self.watch_dir = Path(watch_dir)
        self.processor = DocumentProcessor(chunk_size, chunk_overlap)
        self.callback = callback
        self.observer = None

        # Create watch directory if it doesn't exist
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LibraryWatcher initialized for: {self.watch_dir}")

    def start(self):
        """Start watching the directory"""
        # Create event handler
        event_handler = LibraryFileHandler(self.processor, self.callback)

        # Create observer
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_dir), recursive=False)
        self.observer.start()

        logger.info(f"🔍 Watching for files in: {self.watch_dir}")
        logger.info(f"Supported types: PDF, TXT, MD")

    def stop(self):
        """Stop watching the directory"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watcher stopped")

    def process_existing_files(self):
        """Process any existing files in the watch directory"""
        supported_patterns = ['*.pdf', '*.txt', '*.md']

        for pattern in supported_patterns:
            for file_path in self.watch_dir.glob(pattern):
                logger.info(f"Processing existing file: {file_path.name}")

                try:
                    chunks = self.processor.process_document(str(file_path))

                    logger.info(f"Processed {file_path.name}: {len(chunks)} chunks")

                    if self.callback:
                        self.callback(chunks, file_path)

                except Exception as e:
                    logger.error(f"Error processing {file_path.name}: {str(e)}")

    def run_forever(self):
        """Run the watcher indefinitely"""
        try:
            # Process any existing files first
            logger.info("Processing existing files...")
            self.process_existing_files()

            # Start watching for new files
            self.start()

            # Keep running
            logger.info("Watcher running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.stop()


# Standalone service mode
def main():
    """
    Run the library watcher as a standalone service.

    Enhanced in Chunk 5.2 to store chunks in RedisVL.
    """
    import argparse
    from storage import LibraryStorage

    parser = argparse.ArgumentParser(description='Archive-AI Library Watcher')
    parser.add_argument(
        '--watch-dir',
        default=os.path.expanduser('~/ArchiveAI/Library-Drop'),
        help='Directory to watch for files'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=250,
        help='Token size for chunks (default: 250)'
    )
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=50,
        help='Overlap tokens (default: 50)'
    )
    parser.add_argument(
        '--redis-url',
        default=os.getenv('REDIS_URL', 'redis://redis:6379'),
        help='Redis connection URL (default: from REDIS_URL env or redis://redis:6379)'
    )

    args = parser.parse_args()

    # Initialize storage (Phase 5.2)
    logger.info("Initializing library storage...")
    storage = LibraryStorage(redis_url=args.redis_url)

    # Create callback that stores chunks
    def store_chunks_callback(chunks, file_path):
        """Store processed chunks in RedisVL"""
        try:
            storage.store_chunks(chunks, file_path)

            logger.info(f"📚 Stored {file_path.name}:")
            for chunk in chunks:
                logger.info(
                    f"  Chunk {chunk['chunk_index']}/{chunk['total_chunks']}: "
                    f"{chunk['tokens']} tokens"
                )
        except Exception as e:
            logger.error(f"Failed to store chunks from {file_path.name}: {str(e)}")

    # Create and run watcher
    watcher = LibraryWatcher(
        watch_dir=args.watch_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        callback=store_chunks_callback
    )

    watcher.run_forever()


if __name__ == "__main__":
    main()
