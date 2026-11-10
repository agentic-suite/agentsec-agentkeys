# FT-FC-STORE — PASS

- pack: `failclosed` · scenario: `SC-21` · class: `P/F`
- driver: `core` · duration: 0ms
- detail: unavailable store denies resolution

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| closed-store-denies | eq | `store-error` | `store-error` | yes |
| ledger-denied | eq | `denied` | `denied` | yes |
