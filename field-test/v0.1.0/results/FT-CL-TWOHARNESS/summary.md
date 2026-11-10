# FT-CL-TWOHARNESS — PASS

- pack: `core` · scenario: `SC-07` · class: `P/F`
- driver: `two-sessions` · duration: 0ms
- detail: two harnesses, one broker, one kill

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| s1-authenticated | present | `True` | `b1388abbb6cc18637a35c3426cac5b35` | yes |
| s2-authenticated | present | `True` | `0b1c14355e0747a2a9ca2be964e0066e` | yes |
| distinct-tokens | true | `True` | `True` | yes |
| one-revoke-kills-both | eq | `2` | `2` | yes |
