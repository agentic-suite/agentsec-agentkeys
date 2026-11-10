# FT-RK-KILLTIME — PASS

- pack: `killtime` · scenario: `SC-24` · class: `P/F`
- driver: `bench` · duration: 0ms
- detail: p50=0.02ms p95=0.04ms max=0.04ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| iterations | eq | `5` | `5` | yes |
| p95-lte-1s | lte | `1000.0` | `0.041042` | yes |
| max-lte-1s | lte | `1000.0` | `0.041042` | yes |
| every-replay-refused | eq | `5` | `5` | yes |
