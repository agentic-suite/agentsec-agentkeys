# FT-NFR-RSS — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `container-stats` · duration: 0ms
- detail: peak RSS 35.1 MB

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| rss-under-50mb | lte | `50.0` | `35.1` | yes |
| rss-positive | gte | `0.0` | `35.1` | yes |
