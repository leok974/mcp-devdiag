"""Efficient log file tailing utilities."""

from __future__ import annotations
from pathlib import Path
from typing import List


def tail_lines(path: Path, n: int = 300) -> List[str]:
    """
    Efficiently read last N lines from a file.

    Args:
        path: Path to log file
        n: Number of lines to return from end

    Returns:
        List of last N lines
    """
    if not path.exists():
        return []

    # Efficient tail for moderate files
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        block = 4096
        data = b""

        while size > 0 and data.count(b"\n") <= n:
            read_size = min(block, size)
            size -= read_size
            f.seek(size)
            data = f.read(read_size) + data

        text = data.decode(errors="replace")

    lines = text.splitlines()
    return lines[-n:]
