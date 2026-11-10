# FT-AP-CONTEXTDUMP — PASS

- pack: `attack` · scenario: `SC-40` · class: `P/F`
- driver: `dump-scan` · duration: 0ms
- detail: dump holds references only; the seeded control is caught

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| no-token-in-dump | true | `True` | `True` | yes |
| no-secret-shapes | eq | `()` | `()` | yes |
| references-present | contains | `ref_1` | `{"event":{"agent_id":"a1","binding_json":"{\"audience\":\"https://api.example.com\",\"tool\":\"call\"}","event_id":"evt_5407ceee539b40c994d4e47df43188cc","event_name":"reference-resolved","event_version":"1.0","issuance_id":null,"monotonic_ms":0,"occurred_at":1000,"principal":"op","reason":null,"reference_id":"ref_1","session_id":"s1","severity":"info","ttl_seconds":null},"hash":"ddb44e62a38e5f57f32bd2937293e2092ca9b44dc769b1f43c6f30370687f07c","prev_hash":"0000000000000000000000000000000000000000000000000000000000000000","seq":1}
{"event":{"agent_id":"a1","binding_json":"{\"audience\":\"https://api.example.com\",\"tool\":\"call\"}","event_id":"evt_19316646f8d046a29f9395c7060650b8","event_name":"issuance.created","event_version":"1.0","issuance_id":"iss_5a756848e9904bdc81f223c30219dd4a","monotonic_ms":0,"occurred_at":1000,"principal":"op","reason":null,"reference_id":"ref_1","session_id":"s1","severity":"info","ttl_seconds":300},"hash":"e48102387fe20ed0bb9a877131229c83008c7f527e58269d6d5c5dafee2559d4","prev_hash":"ddb44e62a38e5f57f32bd2937293e2092ca9b44dc769b1f43c6f30370687f07c","seq":2}[{'akref': '1.0', 'reference_id': 'ref_1', 'backend': 'keychain', 'path': 'agentkeys/dev/token', 'class': 'dev', 'label': 'dev token'}]{'issuance': '1.0', 'issuance_id': 'iss_5a756848e9904bdc81f223c30219dd4a', 'reference_id': 'ref_1', 'session_id': 's1', 'agent_id': 'a1', 'binding': {'audience': 'https://api.example.com', 'tool': 'call'}, 'class': 'dev', 'ttl': 300, 'issued_at': 1000, 'expires_at': 1300}transcript: ref_1` | yes |
| control-fires | gte | `1` | `1` | yes |
