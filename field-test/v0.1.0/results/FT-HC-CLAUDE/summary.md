# FT-HC-CLAUDE — WARN

- pack: `harness` · scenario: `SC-35` · class: `P/F|W`
- driver: `recipe` · duration: 542ms
- detail: Claude Code 2.1.187 (Claude Code): wiring + smoke green; live headless run not authenticated
- limitations: claude CLI installed but not logged in on this box (Not logged in · Please run /login); wiring + smoke verified, the live run is declared (plan §8)

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| wiring-valid | true | `True` | `True` | yes |
| wiring-command-is-broker | contains | `agentkeys` | `{'mcpServers': {'agentkeys': {'command': 'agentkeys', 'args': ['run', '--server', 'akref:file/agentkeys/dev/token', '--', '<server-command>'], 'env': {}}}}` | yes |
| smoke-authenticated | true | `True` | `True` | yes |
| transcript-only-reference | eq | `('ref_1',)` | `('ref_1',)` | yes |
| claude-installed | contains | `Claude Code` | `2.1.187 (Claude Code)` | yes |
| live-no-secret | eq | `()` | `()` | yes |
