# FT-HC-CLAUDE — PASS

- pack: `harness` · scenario: `SC-35` · class: `P/F|W`
- driver: `recipe` · duration: 0ms
- detail: Claude Code recipe wiring + smoke authenticated

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| wiring-valid | true | `True` | `True` | yes |
| smoke-authenticated | true | `True` | `True` | yes |
| transcript-only-reference | eq | `('ref_1',)` | `('ref_1',)` | yes |
| no-token-in-transcript | true | `True` | `True` | yes |
