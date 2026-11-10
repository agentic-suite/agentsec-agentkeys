# FT-ST-NOSECRET — PASS

- pack: `stdio` · scenario: `SC-12` · class: `P/F`
- driver: `stdio-run` · duration: 18ms
- detail: stdio child authenticates with no secret in its config/env/transcript

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| child-exit | eq | `0` | `0` | yes |
| reference-in-child-env | absent | `file/agentkeys` | `{'AGENTKEYS_SCOPED_TOKEN': 'ed848efa984e612b7feeb2bf69c780cd'}` | yes |
| backend-value-absent | absent | `SENTINEL-BACKEND-VALUE` | `{'AGENTKEYS_SCOPED_TOKEN': 'ed848efa984e612b7feeb2bf69c780cd'}` | yes |
| no-secret-in-transcript | eq | `()` | `()` | yes |
| receipts-issued | gte | `1` | `1` | yes |
