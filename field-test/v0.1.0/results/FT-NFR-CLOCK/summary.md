# FT-NFR-CLOCK — PASS

- pack: `nfr` · scenario: `SC-05` · class: `P/F`
- driver: `clock` · duration: 0ms
- detail: clock jumps cannot extend or resurrect

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| first-now | eq | `1000` | `1000` | yes |
| backwards-fails-closed | contains | `moved backwards` | `wall clock moved backwards by 100s (tolerance 0s)` | yes |
| forwards-expires | true | `True` | `True` | yes |
| expiry-once | eq | `(1, 0)` | `(1, 0)` | yes |
