# FT-CL-ENV — PASS

- pack: `core` · scenario: `SC-02` · class: `P/F`
- driver: `env-inject` · duration: 21ms
- detail: placeholder substituted at egress; child authenticated

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| child-sees-token | eq | `present` | `present` | yes |
| token-not-in-output | true | `True` | `True` | yes |
| reference-not-in-child-env | absent | `akref:` | `{'AGENTKEYS_SCOPED_TOKEN': 'c4138fdfb3870bf8c3137038c0cf1693', 'SAFE': 'x'}` | yes |
| backend-value-absent | absent | `SENTINEL-BACKEND-VALUE` | `{'AGENTKEYS_SCOPED_TOKEN': 'c4138fdfb3870bf8c3137038c0cf1693', 'SAFE': 'x'}` | yes |
| no-secret-shapes | eq | `()` | `()` | yes |
