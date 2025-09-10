"""
Custom log handlers for Harbor.

Provides specialized handlers for rotation, compression, and buffering.
"""

import gzip
import logging
import logging.handlers
from pathlib import Path


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Rotating file handler that compresses rotated log files.
    Important for home labs with limited storage.
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        maxBytes: int = 0,  # noqa: N803 - matching parent class signature
        backupCount: int = 0,  # noqa: N803 - matching parent class signature
        encoding: str | None = None,
        delay: bool = False,
        compression_level: int = 9,
    ):
        """
        Initialize compressed rotating file handler.

        Args:
            filename: Log file path
            mode: File open mode
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Delay file opening until first log
            compression_level: Gzip compression level (1-9)
        """
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.compression_level = compression_level
        self.namer = self._compressed_namer
        self.rotator = self._compressed_rotator

    def _compressed_namer(self, name: str) -> str:
        """
        Generate name for compressed backup file.

        Args:
            name: Original backup filename

        Returns:
            str: Filename with .gz extension
        """
        return name + ".gz"

    def _compressed_rotator(self, source: str, dest: str) -> None:
        """
        Compress and rotate log file.

        Args:
            source: Source file to compress
            dest: Destination compressed file
        """
        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb", compresslevel=self.compression_level) as f_out:
                f_out.writelines(f_in)
        Path(source).unlink()

    def doRollover(self) -> None:  # noqa: N802 - matching parent class method name
        """Override to handle compressed files during rollover."""
        super().doRollover()

        # Clean up old compressed files beyond backupCount
        if self.backupCount > 0:
            for i in range(self.backupCount, 0, -1):
                sfn = self.rotation_filename(f"{self.baseFilename}.{i}.gz")
                if Path(sfn).exists():
                    Path(sfn).unlink()


class TimedCompressedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Time-based rotating file handler with compression.
    Useful for daily log rotation with compression.
    """

    def __init__(
        self,
        filename: str,
        when: str = "midnight",
        interval: int = 1,
        backupCount: int = 0,  # noqa: N803 - matching parent class signature
        encoding: str | None = None,
        delay: bool = False,
        utc: bool = False,
        compression_level: int = 9,
    ):
        """
        Initialize timed compressed rotating file handler.

        Args:
            filename: Log file path
            when: Type of interval ('midnight', 'H', 'D', 'W', etc.)
            interval: Rotation interval
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Delay file opening
            utc: Use UTC time
            compression_level: Gzip compression level
        """
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc)
        self.compression_level = compression_level
        self.namer = self._compressed_namer
        self.rotator = self._compressed_rotator

    def _compressed_namer(self, name: str) -> str:
        """Add .gz extension to rotated files."""
        return name + ".gz"

    def _compressed_rotator(self, source: str, dest: str) -> None:
        """Compress the rotated file."""
        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb", compresslevel=self.compression_level) as f_out:
                f_out.writelines(f_in)
        Path(source).unlink()


class BufferedHandler(logging.handlers.MemoryHandler):
    """
    Buffered handler for performance optimization.
    Batches log writes to reduce I/O overhead.
    """

    def __init__(
        self,
        capacity: int = 1000,
        flushLevel: int = logging.ERROR,  # noqa: N803 - matching parent class signature
        target: logging.Handler | None = None,
        flushOnClose: bool = True,  # noqa: N803 - matching parent class signature
    ):
        """
        Initialize buffered handler.

        Args:
            capacity: Buffer capacity (number of records)
            flushLevel: Flush immediately for this level and above
            target: Target handler to flush to
            flushOnClose: Flush buffer when handler is closed
        """
        super().__init__(capacity, flushLevel, target, flushOnClose)
