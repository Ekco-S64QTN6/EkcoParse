"""High-performance, non-blocking EverQuest log tailer engine."""

import os
import time
from pathlib import Path
from typing import Generator, List, Optional


class LogTailer:
    """Efficiently tails an EverQuest log file with rotation and truncation handling."""

    def __init__(
        self,
        filepath: Path,
        start_at_end: bool = True,
        poll_interval_sec: float = 0.05,
    ):
        self.filepath = Path(filepath)
        self.start_at_end = start_at_end
        self.poll_interval_sec = poll_interval_sec
        self._file = None
        self._last_ino: Optional[int] = None
        self._last_size: int = 0
        self._is_active = False

    def open(self) -> bool:
        """Open or reopen the target log file."""
        self.close()
        if not self.filepath.exists():
            return False

        try:
            stat = self.filepath.stat()
            self._file = open(self.filepath, "r", encoding="utf-8", errors="replace")
            self._last_ino = stat.st_ino
            self._last_size = stat.st_size

            if self.start_at_end:
                self._file.seek(0, os.SEEK_END)
            else:
                self._file.seek(0, os.SEEK_SET)

            self._is_active = True
            return True
        except Exception:
            self._file = None
            self._is_active = False
            return False

    def close(self) -> None:
        """Close active file handle."""
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None
        self._is_active = False

    def set_filepath(self, new_path: Path) -> None:
        """Switch target file (e.g. character switch or zone change)."""
        if Path(new_path) != self.filepath:
            self.filepath = Path(new_path)
            self.open()

    def read_available_lines(self) -> List[str]:
        """Read all currently available complete lines without blocking."""
        if not self._file or not self.filepath.exists():
            if not self.open():
                return []

        # Check for rotation or truncation
        try:
            stat = self.filepath.stat()
            if stat.st_ino != self._last_ino or stat.st_size < self._last_size:
                # File was recreated, rotated, or truncated: reopen
                self.open()
                if not self._file:
                    return []
            self._last_size = stat.st_size
        except Exception:
            return []

        lines = []
        while True:
            line = self._file.readline()
            if not line:
                break
            # Strip trailing newline while preserving message spacing
            if line.endswith("\r\n"):
                line = line[:-2]
            elif line.endswith("\n"):
                line = line[:-1]
            lines.append(line)

        return lines

    def stream(self) -> Generator[str, None, None]:
        """Continuous generator yielding new lines as they appear."""
        if not self.open():
            # Wait for file to be created
            while not self.open():
                time.sleep(self.poll_interval_sec)

        while True:
            lines = self.read_available_lines()
            if lines:
                for line in lines:
                    yield line
            else:
                time.sleep(self.poll_interval_sec)
