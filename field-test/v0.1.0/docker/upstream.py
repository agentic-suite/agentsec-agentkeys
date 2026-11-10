"""Fake HTTP resource + fake RFC 8693 STS for the field topology (no real API, no secrets logged).

Every request is recorded as metadata only: scheme presence, sha256 of the full header value, and
the exchange body keys. No token value is ever written to disk.
"""

from __future__ import annotations

import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG_PATH = os.environ.get("UPSTREAM_LOG", "/shared/upstream.jsonl")


def _record(payload: dict[str, object]) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "agentkeys-fixture/1.0"

    def _send(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self.path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not-found"})

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        if self.path == "/resource":
            auth = self.headers.get("Authorization", "")
            scheme, _, value = auth.partition(" ")
            _record(
                {
                    "path": "/resource",
                    "auth_present": bool(auth),
                    "scheme": scheme,
                    "auth_sha256": hashlib.sha256(auth.encode()).hexdigest(),
                    "token_sha256": hashlib.sha256(value.encode()).hexdigest() if value else "",
                }
            )
            if not auth:
                self._send(401, {"error": "missing-authorization"})
            else:
                self._send(200, {"authenticated": True, "audience": "fixture"})
            return
        if self.path == "/token":
            fields = body.split("&")
            pairs = [field.partition("=") for field in fields]
            data = {key: value for key, _sep, value in pairs}
            _record(
                {
                    "path": "/token",
                    "keys": sorted(data),
                    "audience": data.get("audience", ""),
                    "scope": data.get("scope", ""),
                    "subject_sha256": hashlib.sha256(data.get("subject_token", "").encode()).hexdigest(),
                }
            )
            self._send(
                200,
                {
                    "access_token": "exchanged-fixture-token",
                    "act": "agentkeys:broker",
                    "audience": data.get("audience", ""),
                },
            )
            return
        self._send(404, {"error": "not-found"})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - http.server API
        return


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
