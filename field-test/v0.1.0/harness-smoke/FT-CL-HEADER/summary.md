# FT-CL-HEADER — PASS

- pack: `core` · scenario: `SC-03` · class: `P/F`
- driver: `header-inject` · duration: 0ms
- detail: header injection sets only the broker-minted token

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| authorization-set | true | `True` | `True` | yes |
| broker-token-in-header | true | `True` | `True` | yes |
| client-token-absent | true | `True` | `True` | yes |
| overwrote-client | true | `True` | `True` | yes |
