# FT-RK-KILLTIME — PASS

- pack: `killtime` · scenario: `SC-24` · class: `P/F`
- driver: `bench` · duration: 6ms
- detail: p50=0.01ms p95=0.01ms max=0.03ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| iterations | eq | `100` | `100` | yes |
| p95-lte-1s | lte | `1000.0` | `0.014708` | yes |
| max-lte-1s | lte | `1000.0` | `0.02975` | yes |
| every-replay-refused | eq | `100` | `100` | yes |
