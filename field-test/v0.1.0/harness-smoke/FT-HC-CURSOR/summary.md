# FT-HC-CURSOR — WARN

- pack: `harness` · scenario: `SC-36` · class: `P/F|W`
- driver: `recipe` · duration: 0ms
- detail: Cursor not installed; wiring + smoke green
- limitations: no Cursor on the box; the smoke is mandatory and the live run is declared (plan §8)

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| wiring-valid | true | `True` | `True` | yes |
| smoke-authenticated | true | `True` | `True` | yes |
| transcript-only-reference | eq | `('ref_1',)` | `('ref_1',)` | yes |
| no-token-in-transcript | true | `True` | `True` | yes |
