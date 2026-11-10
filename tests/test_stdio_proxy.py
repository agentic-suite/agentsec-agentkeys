"""5.2 - the stdio proxy: byte-for-byte frames, stderr-only logging, a frame size cap."""

from __future__ import annotations

import io
import sys

import pytest

from agentkeys.stdio.proxy import (
    DEFAULT_MAX_FRAME_BYTES,
    FrameTooLarge,
    StdioProxy,
    forward_frame,
)


def test_a_frame_passes_through_byte_for_byte() -> None:
    frame = b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'
    assert forward_frame(frame) == frame


def test_an_oversized_frame_is_refused() -> None:
    with pytest.raises(FrameTooLarge, match="cap"):
        forward_frame(b"x" * 64, max_frame_bytes=16)
    assert forward_frame(b"x" * 16, max_frame_bytes=16)


def test_logging_never_touches_the_jsonrpc_stream() -> None:
    lines: list[str] = []
    proxy = StdioProxy([sys.executable, "-c", "pass"], log=lines.append)
    proxy.log("refused an oversized frame")
    assert lines == ["refused an oversized frame"]
    assert not hasattr(proxy, "out")


def test_the_default_cap_is_a_megabyte() -> None:
    assert DEFAULT_MAX_FRAME_BYTES == 1_048_576


def test_a_child_is_proxied_and_its_exit_code_returned() -> None:
    child = [
        sys.executable,
        "-c",
        "import sys\nfor line in sys.stdin.buffer:\n    sys.stdout.buffer.write(line)\nsys.exit(3)\n",
    ]
    proxy = StdioProxy(child, log=lambda line: None)
    stdin = io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
    stdout = io.BytesIO()
    code = proxy.run(stdin=stdin, stdout=stdout)
    assert code == 3
    assert b'"method":"ping"' in stdout.getvalue()


def test_an_oversized_request_frame_is_logged_and_not_forwarded() -> None:
    child = [sys.executable, "-c", "import sys; sys.exit(0)"]
    logged: list[str] = []
    proxy = StdioProxy(child, max_frame_bytes=8, log=logged.append)
    proxy.run(stdin=io.BytesIO(b"x" * 64), stdout=io.BytesIO())
    assert any("oversized" in line for line in logged)


def test_a_proxy_needs_a_command() -> None:
    with pytest.raises(ValueError, match="command"):
        StdioProxy([])
