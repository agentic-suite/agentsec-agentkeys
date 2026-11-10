# FT-HC-GENERIC — PASS

- pack: `harness` · scenario: `SC-37` · class: `P/F`
- driver: `sdk` · duration: 0ms
- detail: public SDK contract: resolve → use, no get_secret

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| resolved | present | `True` | `c7eff442474d67610437fadbec5d5982` | yes |
| consumed | eq | `consumed` | `consumed` | yes |
| no-secret-read-out | true | `True` | `True` | yes |
