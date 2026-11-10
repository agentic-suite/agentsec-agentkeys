# FT-RK-ATTR — PASS

- pack: `killtime` · scenario: `SC-28` · class: `P/F`
- driver: `revoke` · duration: 0ms
- detail: revoked event carries the operator and target

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| principal | eq | `alice` | `alice` | yes |
| session | eq | `s1` | `s1` | yes |
| timestamp | eq | `1234` | `1234` | yes |
| severity | eq | `high` | `high` | yes |
