# FT-SU-APPROVED — PASS

- pack: `stepup` · scenario: `SC-33` · class: `P/F`
- driver: `step-up-gate` · duration: 0ms
- detail: approval recorded, TTL tightened, grant tied to the issuance

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| provenance | eq | `agentpolicy` | `agentpolicy` | yes |
| tighter-ttl | eq | `120` | `120` | yes |
| provenance-persisted | contains | `agentpolicy` | `{"decided_by": "agentpolicy", "decision": "allow", "source": "human-once"}` | yes |
| granted-after-mint | eq | `iss_3fc2519d60a8487a8f3058adb8c57b01` | `iss_3fc2519d60a8487a8f3058adb8c57b01` | yes |
