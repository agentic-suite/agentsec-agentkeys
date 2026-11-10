# FT-SU-DENIED — PASS

- pack: `stepup` · scenario: `SC-34` · class: `P/F`
- driver: `step-up-gate` · duration: 0ms
- detail: deny mints nothing

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| denied | true | `True` | `True` | yes |
| no-credential | eq | `0` | `0` | yes |
