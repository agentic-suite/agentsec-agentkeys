# FT-NFR-RSS — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `container-stats` · duration: 1ms
- detail: peak RSS 38.2 MB

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| rss-under-50mb | lte | `50.0` | `38.2` | yes |
| rss-positive | gte | `0.0` | `38.2` | yes |
