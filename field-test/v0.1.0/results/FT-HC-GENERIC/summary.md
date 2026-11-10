# FT-HC-GENERIC — PASS

- pack: `harness` · scenario: `SC-37` · class: `P/F`
- driver: `sdk` · duration: 0ms
- detail: public SDK contract: resolve → use, no get_secret

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| resolved | present | `True` | `edd960eb1b5ad03f006afcb9dd8dd5b1` | yes |
| consumed | eq | `consumed` | `consumed` | yes |
| no-secret-read-out | true | `True` | `True` | yes |
