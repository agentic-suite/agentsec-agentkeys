# FT-OPS-RETENTION — PASS

- pack: `ops` · scenario: `None` · class: `P/F`
- driver: `retention` · duration: 0ms
- detail: retention is an append-only marker

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| marker | eq | `retention-pruned` | `retention-pruned` | yes |
| actor | eq | `alice` | `alice` | yes |
| nothing-deleted | eq | `3` | `3` | yes |
| chain-intact | true | `True` | `True` | yes |
