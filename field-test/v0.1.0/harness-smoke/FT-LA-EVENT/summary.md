# FT-LA-EVENT — PASS

- pack: `audit` · scenario: `SC-32` · class: `P/F`
- driver: `events` · duration: 0ms
- detail: one versioned event per transition

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| issuance-event | contains | `issuance.created` | `{'reference-resolved', 'use', 'revoked', 'issuance.created'}` | yes |
| use-event | contains | `use` | `{'reference-resolved', 'use', 'revoked', 'issuance.created'}` | yes |
| revoked-event | contains | `revoked` | `{'reference-resolved', 'use', 'revoked', 'issuance.created'}` | yes |
| event-version | eq | `{'1.0'}` | `{'1.0'}` | yes |
