"""
socket.socketpair() fallback that works under seccomp (no AF_UNIX).

Implements just enough of the socket API for asyncio’s self-pipe trick.
Never active in production.
"""

from __future__ import annotations
import os
import socket
from types import SimpleNamespace
from typing import Tuple


# ------------------------------------------------------------------ #
# helpers                                                            #
# ------------------------------------------------------------------ #
def _pipe_socketpair() -> Tuple[socket.socket, socket.socket]:
    """Return a cross-wired pair of pipe-backed pseudo sockets."""

    def _make_pipe_end(read_fd: int, write_fd: int) -> socket.socket:  # type: ignore[return-value]
        class _PipeSocket(SimpleNamespace):
            def fileno(self) -> int:  # noqa: D401
                return read_fd

            def setblocking(self, _flag: bool) -> None:  # noqa: D401
                os.set_blocking(read_fd, False)
                os.set_blocking(write_fd, False)

            def recv(self, bufsize: int) -> bytes:  # noqa: D401
                return os.read(read_fd, bufsize)

            def send(self, data: bytes) -> int:  # noqa: D401
                return os.write(write_fd, data)

            def close(self) -> None:  # noqa: D401
                for fd in (read_fd, write_fd):
                    try:
                        os.close(fd)
                    except OSError:
                        pass

        return _PipeSocket()

    r1, w1 = os.pipe()
    r2, w2 = os.pipe()
    return _make_pipe_end(r1, w2), _make_pipe_end(r2, w1)


def _safe_socketpair(*args, **kwargs):  # noqa: D401
    """Try real socketpair, fall back on PermissionError."""
    _orig = socket._orig_socketpair  # type: ignore[attr-defined]
    try:
        return _orig(*args, **kwargs)
    except PermissionError:
        return _pipe_socketpair()


# ------------------------------------------------------------------ #
# public installer                                                   #
# ------------------------------------------------------------------ #
def install_socketpair_patch() -> None:
    """Idempotently monkey-patch socket.socketpair with safe fallback."""
    if getattr(socket, "_socketpair_patched", False):
        return
    socket._orig_socketpair = getattr(socket, "socketpair")  # type: ignore[attr-defined]
    socket.socketpair = _safe_socketpair  # type: ignore[assignment]
    socket._socketpair_patched = True  # type: ignore[attr-defined]
