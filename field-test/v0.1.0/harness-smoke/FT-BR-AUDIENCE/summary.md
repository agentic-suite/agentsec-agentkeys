# FT-BR-AUDIENCE — PASS

- pack: `binding` · scenario: `SC-08` · class: `P/F`
- driver: `injector` · duration: 0ms
- detail: wrong audience refused and recorded

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| refused | true | `True` | `True` | yes |
| evidence-event | eq | `exchange-rejected` | `exchange-rejected` | yes |
| reason | eq | `audience-mismatch` | `audience-mismatch` | yes |
