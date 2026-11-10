# FT-AP-CONTEXTDUMP — PASS

- pack: `attack` · scenario: `SC-40` · class: `P/F`
- driver: `dump-scan` · duration: 0ms
- detail: dump holds references only; the seeded control is caught

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| no-token-in-dump | true | `True` | `True` | yes |
| no-secret-shapes | eq | `()` | `()` | yes |
| references-present | contains | `ref_1` | `{"event":{"agent_id":"a1","binding_json":"{\"audience\":\"https://api.example.com\",\"tool\":\"call\"}","event_id":"evt_b7069d333ea14dd488a4ef540d24f07f","event_name":"reference-resolved","event_version":"1.0","issuance_id":null,"monotonic_ms":0,"occurred_at":1000,"principal":"op","reason":null,"reference_id":"ref_1","session_id":"s1","severity":"info","ttl_seconds":null},"hash":"7c91a34afa0e1b77347bb0d40f66ef7f9c1b41b03378ac4fc60f39906d5a64db","prev_hash":"0000000000000000000000000000000000000000000000000000000000000000","seq":1}
{"event":{"agent_id":"a1","binding_json":"{\"audience\":\"https://api.example.com\",\"tool\":\"call\"}","event_id":"evt_34e82b4500234e5289485f77bfa33e27","event_name":"issuance.created","event_version":"1.0","issuance_id":"iss_274d0961cac044748e7fc77fd1e73c47","monotonic_ms":0,"occurred_at":1000,"principal":"op","reason":null,"reference_id":"ref_1","session_id":"s1","severity":"info","ttl_seconds":300},"hash":"3c2a282b40de6aa0ab7029f3fa61b5142ffbae5a2ebb790114600125b46dc8bc","prev_hash":"7c91a34afa0e1b77347bb0d40f66ef7f9c1b41b03378ac4fc60f39906d5a64db","seq":2}[{'akref': '1.0', 'reference_id': 'ref_1', 'backend': 'keychain', 'path': 'agentkeys/dev/token', 'class': 'dev', 'label': 'dev token'}]{'issuance': '1.0', 'issuance_id': 'iss_274d0961cac044748e7fc77fd1e73c47', 'reference_id': 'ref_1', 'session_id': 's1', 'agent_id': 'a1', 'binding': {'audience': 'https://api.example.com', 'tool': 'call'}, 'class': 'dev', 'ttl': 300, 'issued_at': 1000, 'expires_at': 1300}transcript: ref_1` | yes |
| control-fires | gte | `1` | `1` | yes |
