# FT-OPS-DOCTOR — PASS

- pack: `ops` · scenario: `None` · class: `P/F`
- driver: `doctor` · duration: 4ms
- detail: doctor checks chain/lock/config and exits by precedence

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| healthy-exit | eq | `0` | `0` | yes |
| tamper-exit | eq | `3` | `3` | yes |
| under-2s | lte | `2.0` | `0.001` | yes |
