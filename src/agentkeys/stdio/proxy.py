"""Transparent stdio JSON-RPC proxy: byte-for-byte frames, stderr-only logging (M5, WBS 5.2)."""

from __future__ import annotations

import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from typing import IO

__all__ = ["DEFAULT_MAX_FRAME_BYTES", "FrameTooLarge", "StdioProxy", "forward_frame"]

DEFAULT_MAX_FRAME_BYTES = 1_048_576


class FrameTooLarge(Exception):
    """A frame exceeded the proxy's size cap; it is refused and logged, never forwarded."""


def forward_frame(frame: bytes, *, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES) -> bytes:
    """Return the frame unchanged, or refuse it when it exceeds the cap."""
    if len(frame) > max_frame_bytes:
        raise FrameTooLarge(f"frame of {len(frame)} bytes exceeds the {max_frame_bytes}-byte cap")
    return frame


class StdioProxy:
    """Launches a child under the broker and pumps its stdio, logging only to stderr."""

    def __init__(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
        log: Callable[[str], None] | None = None,
    ) -> None:
        if not argv:
            raise ValueError("the proxy needs a child command")
        self.argv = list(argv)
        self.env = dict(env) if env is not None else None
        self.max_frame_bytes = max_frame_bytes
        self._log = log if log is not None else (lambda line: print(line, file=sys.stderr))

    def log(self, message: str) -> None:
        """Logging goes to stderr only; stdout is reserved for the JSON-RPC stream."""
        self._log(message)

    def spawn(self) -> subprocess.Popen[bytes]:
        return subprocess.Popen(  # noqa: S603 - fixed argv from trusted config, no shell
            self.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )

    def pump(
        self,
        process: subprocess.Popen[bytes],
        *,
        source: IO[bytes],
        sink: IO[bytes],
        errors: IO[bytes],
    ) -> int:
        """Pump `source` into the child and the child's stdout into `sink`; return the exit code."""
        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise RuntimeError("the child was spawned without pipes")

        def child_to_sink() -> None:
            for line in process.stdout or ():
                try:
                    sink.write(forward_frame(line, max_frame_bytes=self.max_frame_bytes))
                except FrameTooLarge as exc:
                    self.log(f"agentkeys run: refused an oversized response frame: {exc}")
                sink.flush()

        def drain_stderr() -> None:
            for line in process.stderr or ():
                errors.write(line)
            errors.flush()

        pump = threading.Thread(target=child_to_sink, daemon=True)
        pump.start()
        threading.Thread(target=drain_stderr, daemon=True).start()
        for line in source:
            try:
                process.stdin.write(forward_frame(line, max_frame_bytes=self.max_frame_bytes))
                process.stdin.flush()
            except FrameTooLarge as exc:
                self.log(f"agentkeys run: refused an oversized request frame: {exc}")
        process.stdin.close()
        return process.wait()

    def run(self, *, stdin: IO[bytes] | None = None, stdout: IO[bytes] | None = None) -> int:
        """The `agentkeys run` entry point."""
        import os

        source = stdin if stdin is not None else sys.stdin.buffer
        sink = stdout if stdout is not None else sys.stdout.buffer
        env = self.env
        if env is None:
            env = dict(os.environ)
        process = self.spawn()
        try:
            return self.pump(process, source=source, sink=sink, errors=sys.stderr.buffer)
        finally:
            if process.poll() is None:  # pragma: no cover - only when the pump raised
                process.kill()
