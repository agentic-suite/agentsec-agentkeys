# FT-BR-STALE — PASS

- pack: `binding` · scenario: `SC-11` · class: `P/F`
- driver: `lifecycle` · duration: 0ms
- detail: stale and forwarded presentations refused

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| stale-expired | eq | `expired` | `expired` | yes |
| forwarded-rejected | eq | `rejected` | `rejected` | yes |
