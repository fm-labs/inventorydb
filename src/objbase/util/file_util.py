"""Cross-platform file locking and atomic JSON writes, using only the standard library."""

import contextlib
import json
import os
import shutil
import sys
import time
import uuid
from collections.abc import Iterator
from typing import IO, Any

if sys.platform == "win32":
    import msvcrt

    def _lock(f: IO[bytes], shared: bool) -> None:
        # msvcrt has no shared locks, so readers lock exclusively too. LK_LOCK
        # gives up after ~10s, so retry until the lock is acquired.
        f.seek(0)
        while True:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                return
            except OSError:
                time.sleep(0.05)

    def _unlock(f: IO[bytes]) -> None:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(f: IO[bytes], shared: bool) -> None:
        # flock locks belong to the open file, so they also exclude other threads
        # in the same process, not just other processes.
        fcntl.flock(f.fileno(), fcntl.LOCK_SH if shared else fcntl.LOCK_EX)

    def _unlock(f: IO[bytes]) -> None:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def locked(lock_path: str, shared: bool = False) -> Iterator[None]:
    """Hold an advisory lock on ``lock_path`` (created if missing) for the duration of the block.

    Blocks until the lock is available. ``shared=True`` allows concurrent readers
    (on Windows all locks are exclusive). The lock is released if the process dies.
    Lock files are left in place; deleting them while others may use them is unsafe.
    """
    with open(lock_path, "a+b") as f:
        _lock(f, shared)
        try:
            yield
        finally:
            _unlock(f)


def _replace(src: str, dst: str) -> None:
    if sys.platform != "win32":
        os.replace(src, dst)
        return
    # Windows refuses to replace a file another process has open (e.g. an unlocked
    # reader), so retry briefly before giving up.
    for _ in range(40):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.05)
    os.replace(src, dst)


def atomic_write_json(path: str, data: Any) -> None:
    """Write ``data`` as JSON to ``path`` so readers see either the old or the new file, never a partial one.

    See ``atomic_write_text``.
    """
    atomic_write_text(path, json.dumps(data, indent=4))


def atomic_write_text(path: str, text: str) -> None:
    """Write ``text`` to ``path`` so readers see either the old or the new file, never a partial one.

    Writes to a temporary file in the same directory and renames it over ``path``.
    Keeps the permissions of an existing ``path``; a new file gets the default
    permissions for the current umask.
    """
    directory, name = os.path.split(path)
    tmp_path = os.path.join(directory, f".{name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(tmp_path, "x") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            shutil.copymode(path, tmp_path)
        _replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp_path)
        raise
