# FT-FC-CRASH — PASS

- pack: `failclosed` · scenario: `SC-23` · class: `P/F`
- driver: `subprocess-crash` · duration: 30ms
- detail: kill -9 mid-issue recovers with no partial or orphan state

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| crashed | eq | `70` | `70` | yes |
| no-partial-ledger | eq | `0` | `0` | yes |
| no-orphan-issuance | eq | `0` | `0` | yes |
