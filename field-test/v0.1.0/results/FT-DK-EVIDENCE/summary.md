# FT-DK-EVIDENCE — PASS

- pack: `docker` · scenario: `SC-43` · class: `P/F`
- driver: `compose-run` · duration: 489ms
- detail: evidence scan over broker volumes is clean

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| evidence-clean | eq | `0` | `0` | yes |
| scan-ran | contains | `scanned` | `{"scanned": "/data", "findings": 0}
` | yes |
