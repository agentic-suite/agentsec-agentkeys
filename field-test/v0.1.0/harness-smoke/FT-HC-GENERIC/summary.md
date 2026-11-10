# FT-HC-GENERIC — PASS

- pack: `harness` · scenario: `SC-37` · class: `P/F`
- driver: `sdk` · duration: 0ms
- detail: public SDK contract: resolve → use, no get_secret

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| resolved | present | `True` | `9ff7b093d730b38be2a7b2bbae7b8d1a` | yes |
| consumed | eq | `consumed` | `consumed` | yes |
| no-secret-read-out | true | `True` | `True` | yes |
