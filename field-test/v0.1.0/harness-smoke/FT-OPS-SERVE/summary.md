# FT-OPS-SERVE — PASS

- pack: `ops` · scenario: `None` · class: `P/F`
- driver: `serve` · duration: 2ms
- detail: serve lock lifecycle is honest

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| live-lock | eq | `live` | `live` | yes |
| second-serve-refused | contains | `already running` | `broker already running: lock held by pid 13996` | yes |
| sigterm-cleans-up | eq | `absent` | `absent` | yes |
| stale-detected | eq | `stale` | `stale` | yes |
