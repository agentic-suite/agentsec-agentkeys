# FT-AG-OFFLINE — PASS

- pack: `offline` · scenario: `SC-39` · class: `P/F`
- driver: `sockets-off` · duration: 12ms
- detail: core + revoke work with sockets disabled; unknown backend refuses

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| resolved-offline | present | `True` | `7c4dcae1df52eb78cb60244f650fd060` | yes |
| used-offline | eq | `consumed` | `consumed` | yes |
| revoked-offline | eq | `1` | `1` | yes |
| cloud-backend-refused | contains | `vault` | `unknown store driver: vault (known: memory, sqlite)` | yes |
