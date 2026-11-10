# FT-CL-ENV — PASS

- pack: `core` · scenario: `SC-02` · class: `P/F`
- driver: `env-inject` · duration: 18ms
- detail: placeholder substituted at egress; child authenticated

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| child-sees-token | eq | `present` | `present` | yes |
| token-not-in-output | true | `True` | `True` | yes |
| reference-not-in-child-env | absent | `akref:` | `{'AGENTKEYS_SCOPED_TOKEN': 'e6b6b7a90244fdd57fa69cc156a36b21', 'SAFE': 'x'}` | yes |
| backend-value-absent | absent | `SENTINEL-BACKEND-VALUE` | `{'AGENTKEYS_SCOPED_TOKEN': 'e6b6b7a90244fdd57fa69cc156a36b21', 'SAFE': 'x'}` | yes |
| no-secret-shapes | eq | `()` | `()` | yes |
