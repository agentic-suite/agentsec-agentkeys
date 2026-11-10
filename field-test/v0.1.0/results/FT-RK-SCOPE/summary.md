# FT-RK-SCOPE — PASS

- pack: `killtime` · scenario: `SC-25` · class: `P/F`
- driver: `revoke` · duration: 0ms
- detail: scoped revoke kills only the target

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| target-dead | eq | `1` | `1` | yes |
| non-target-alive | eq | `0` | `0` | yes |
