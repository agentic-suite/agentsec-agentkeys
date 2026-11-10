# FT-HC-CURSOR — WARN

- pack: `harness` · scenario: `SC-36` · class: `P/F|W`
- driver: `recipe` · duration: 0ms
- detail: Cursor: wiring + smoke green; no headless CLI on this box
- limitations: Cursor is a GUI IDE (VS Code fork) with no headless/evidence-capturing CLI surface on this box; the wiring + smoke are verified and the live run is declared (plan §8)

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| wiring-valid | true | `True` | `True` | yes |
| wiring-command-is-broker | contains | `agentkeys` | `{'mcpServers': {'agentkeys': {'command': 'agentkeys', 'args': ['run', '--server', 'akref:file/agentkeys/dev/token', '--', '<server-command>'], 'env': {}}}}` | yes |
| smoke-authenticated | true | `True` | `True` | yes |
| transcript-only-reference | eq | `('ref_1',)` | `('ref_1',)` | yes |
