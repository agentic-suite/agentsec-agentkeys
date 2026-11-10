# FT-RK-UNKNOWN — PASS

- pack: `killtime` · scenario: `SC-27` · class: `P/F`
- driver: `revoke` · duration: 0ms
- detail: unknown target errors loudly

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| refused | present | `True` | `unknown session: ghost` | yes |
| names-target | contains | `ghost` | `unknown session: ghost` | yes |
