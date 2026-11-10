# FT-OPS-MIGRATE — PASS

- pack: `ops` · scenario: `None` · class: `P/F`
- driver: `migration` · duration: 4ms
- detail: forward migrate; newer schema refuses loudly

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| forward-migrate | eq | `1` | `1` | yes |
| downgrade-refused | contains | `newer than supported` | `store schema version 999 is newer than supported 1; downgrade is refused` | yes |
