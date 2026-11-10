"""Fixture stdio MCP server: proves it received a scoped token without printing it.

Reads JSON-RPC-ish lines; replies with `token_present` only. Never echoes the token, the
reference, or the backend value. Exits 0 on EOF.
"""

from __future__ import annotations

import json
import os
import sys

TOKEN_ENV = "AGENTKEYS_SCOPED_TOKEN"


def main() -> int:
    token = os.environ.get(TOKEN_ENV, "")
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        try:
            request = json.loads(text)
        except json.JSONDecodeError:
            request = {}
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "token_present": bool(token),
                "token_length": len(token),
                "reference_present": token.startswith("akref:"),
            },
        }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
