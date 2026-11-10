# FT-CL-EXCHANGE — PASS

- pack: `core` · scenario: `SC-04` · class: `P/F`
- driver: `exchange-inject` · duration: 0ms
- detail: exchange request is narrow and passthrough-free

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| audience | eq | `https://api.example.com` | `https://api.example.com` | yes |
| scope | eq | `call` | `call` | yes |
| subject-is-broker-token | true | `True` | `True` | yes |
| actor-present | present | `True` | `agentkeys:broker` | yes |
| client-token-absent | true | `True` | `True` | yes |
| exchanged-token-returned | eq | `exchanged-token` | `exchanged-token` | yes |
