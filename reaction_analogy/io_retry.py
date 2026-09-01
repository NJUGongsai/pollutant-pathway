#!/usr/bin/env python3
"""Retry helpers for the flaky external /Volumes/CC APFS drive.

The external drive drops briefly (loose connection / power) under I/O and
recovers within a few seconds with journaled data intact. These wrappers
retry ENOENT(2)/EIO(5)/ENXIO(6) with bounded backoff. Every retry path is
bounded by the outer ``retries`` loop (no unbounded inner spin), so a
genuinely-broken state still terminates and raises the last error.

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import os
import time

# errno 2 = ENOENT (transient when the mount drops mid-call on a file that
#          exists), 5 = EIO, 6 = ENXIO ("Device not configured").
_RETRYABLE = {2, 5, 6}


def robust_open(path: str, mode: str = "r", buffering: int = -1,
                retries: int = 200, delay: float = 3.0):
    """open() with retry on ENOENT/EIO/ENXIO. Returns a file object.

    The external drive has multi-minute outages, so the default budget is
    200 x 3s = 10 min before giving up.
    """
    last = None
    for _ in range(retries):
        try:
            return open(path, mode, buffering=buffering)
        except OSError as e:
            last = e
            if getattr(e, "errno", None) in _RETRYABLE:
                time.sleep(delay)
                continue
            raise
    raise last  # type: ignore[misc]


def robust_readlines(path: str, retries: int = 200, delay: float = 3.0) -> list[str]:
    """Read all lines, retrying the WHOLE read on a mid-read drop.

    The drive recovers in minutes; re-reading from the start on a drop costs
    only the read time (~seconds for 1 GB once a good window opens).
    """
    last = None
    for _ in range(retries):
        try:
            with open(path, "r", buffering=1024 * 1024) as f:
                return f.readlines()
        except OSError as e:
            last = e
            if getattr(e, "errno", None) in _RETRYABLE:
                time.sleep(delay)
                continue
            raise
    raise last  # type: ignore[misc]


def robust_writelines(path: str, lines, retries: int = 200, delay: float = 3.0) -> None:
    """Write all lines, retrying the WHOLE write on a mid-write drop."""
    last = None
    for _ in range(retries):
        try:
            with open(path, "w", buffering=1024 * 1024) as f:
                f.writelines(lines)
            return
        except OSError as e:
            last = e
            if getattr(e, "errno", None) in _RETRYABLE:
                time.sleep(delay)
                continue
            raise
    raise last  # type: ignore[misc]


def robust_json_dump(path: str, obj, retries: int = 200, delay: float = 3.0) -> None:
    """json.dump with retry on ENOENT/EIO/ENXIO."""
    import json
    last = None
    for _ in range(retries):
        try:
            with open(path, "w") as f:
                json.dump(obj, f, indent=2, ensure_ascii=False)
            return
        except OSError as e:
            last = e
            if getattr(e, "errno", None) in _RETRYABLE:
                time.sleep(delay)
                continue
            raise
    raise last  # type: ignore[misc]
