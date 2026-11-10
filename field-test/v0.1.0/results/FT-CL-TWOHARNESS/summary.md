# FT-CL-TWOHARNESS — PASS

- pack: `core` · scenario: `SC-07` · class: `P/F`
- driver: `two-sessions` · duration: 0ms
- detail: two harnesses, one broker, one kill

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| s1-authenticated | present | `True` | `30663e485af0c859582480eba3f14710` | yes |
| s2-authenticated | present | `True` | `eab985b28848f32a2ec1063c3d550134` | yes |
| distinct-tokens | true | `True` | `True` | yes |
| one-revoke-kills-both | eq | `2` | `2` | yes |
