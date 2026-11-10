# FT-FC-SINK — PASS

- pack: `failclosed` · scenario: `SC-22` · class: `P/F`
- driver: `sink` · duration: 0ms
- detail: sink offline leaves the local ledger authoritative with a gap marker

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| local-event-kept | contains | `issuance.created` | `['issuance.created', 'sink-gap']` | yes |
| one-gap-marker | eq | `1` | `1` | yes |
| chain-intact | true | `True` | `True` | yes |
