# FT-BR-SESSION — PASS

- pack: `binding` · scenario: `SC-10` · class: `P/F`
- driver: `revoke` · duration: 0ms
- detail: session-bound token dies with the session

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| revoked-token-rejected | eq | `rejected` | `rejected` | yes |
| token-was-session-bound | eq | `s1` | `s1` | yes |
