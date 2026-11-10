# FT-AG-OFFLINE — PASS

- pack: `offline` · scenario: `SC-39` · class: `P/F`
- driver: `sockets-off` · duration: 14ms
- detail: core + revoke work with sockets disabled; unknown backend refuses

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| resolved-offline | present | `True` | `710bbd4761e66a02c03f13953dc92d9e` | yes |
| used-offline | eq | `consumed` | `consumed` | yes |
| revoked-offline | eq | `1` | `1` | yes |
| cloud-backend-refused | contains | `vault` | `unknown store driver: vault (known: memory, sqlite)` | yes |
