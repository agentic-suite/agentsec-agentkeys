# FT-OPS-RESTORE — PASS

- pack: `ops` · scenario: `SC-30` · class: `P/F`
- driver: `restore` · duration: 5ms
- detail: restore preserves the chain and refuses tamper

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| rows-restored | eq | `3` | `3` | yes |
| chain-preserved | true | `True` | `True` | yes |
| tampered-refused | contains | `broken at seq 2` | `backup chain is broken at seq 2` | yes |
