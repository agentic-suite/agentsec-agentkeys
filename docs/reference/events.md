# Events reference — the agentwatch lifecycle set

> **Status: implemented (M7/M9/M12).** Chain and export details: [ledger reference](ledger.md).

| Event | Severity | Fields of note |
|---|---|---|
| `reference-resolved` | info | `reference_id`, binding |
| `issuance.created` | info | `issuance_id`, binding, `ttl_seconds` |
| `use` | info | `issuance_id`, `principal` |
| `exchange-rejected` | warn | `issuance_id`, `reason` (audience/tool/replay) |
| `step-up-requested` | info | `reference_id`, class |
| `step-up-granted` | info | `issuance_id`, `reason` = decision source |
| `step-up-denied` | warn | `reference_id`, `reason` (deny/timeout/policy-error) |
| `evasion-detected` | high | `principal`, class/path or `reference-enumeration` |
| `tamper-detected` | high | `reason` (config digest mismatch) |
| `revoked` | high | `session_id`, `agent_id`, `principal`, `reason` |
| `expired` | info | `issuance_id`, `ttl_seconds` (fires once) |
| `retention-pruned` | info | `principal`, `reason` = cutoff (no rows deleted) |
| `sink-gap` | warn | `reason` = `sink-offline: <error class>` |

Common fields on every event: `event_id`, `event_version` (`1.0`), `event_name`, `occurred_at`,
`monotonic_ms`, `session_id`, `agent_id`, `reference_id`, `issuance_id`, `binding_json`, `ttl_seconds`,
`principal`, `reason`, `severity`, plus the chain's `seq`, `prev_hash`, `hash`.
