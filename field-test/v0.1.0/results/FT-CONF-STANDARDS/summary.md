# FT-CONF-STANDARDS — PASS

- pack: `conformance` · scenario: `None` · class: `P/F`
- driver: `conformance` · duration: 0ms
- detail: conformance green; DPoP explicitly not supported

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| no-failures | eq | `[]` | `[]` | yes |
| dpop-not-supported | eq | `['rfc9449']` | `['rfc9449']` | yes |
| has-passing-suites | gte | `9` | `9` | yes |
