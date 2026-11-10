# FT-CL-TWOHARNESS — PASS

- pack: `core` · scenario: `SC-07` · class: `P/F`
- driver: `two-sessions` · duration: 0ms
- detail: two harnesses, one broker, one kill

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| s1-authenticated | present | `True` | `ee10a0105a43cf6619f7aa727dada351` | yes |
| s2-authenticated | present | `True` | `ef839e5f84a9232e1b07b5f7eaa56d61` | yes |
| distinct-tokens | true | `True` | `True` | yes |
| one-revoke-kills-both | eq | `2` | `2` | yes |
