# FT-CL-ENV — PASS

- pack: `core` · scenario: `SC-02` · class: `P/F`
- driver: `env-inject` · duration: 6ms
- detail: placeholder substituted at egress; child authenticated

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| child-sees-token | eq | `present` | `present` | yes |
| token-not-in-output | true | `True` | `True` | yes |
| reference-not-in-child-env | absent | `akref:` | `{'AGENTKEYS_SCOPED_TOKEN': '3f6e5d6c7631532515a447a0ffc8d63d', 'SAFE': 'x'}` | yes |
| backend-value-absent | absent | `SENTINEL-BACKEND-VALUE` | `{'AGENTKEYS_SCOPED_TOKEN': '3f6e5d6c7631532515a447a0ffc8d63d', 'SAFE': 'x'}` | yes |
| no-secret-shapes | eq | `()` | `()` | yes |
