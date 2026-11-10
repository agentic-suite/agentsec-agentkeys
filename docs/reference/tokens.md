# Token model — short-lived, audience-bound, tool-scoped, session-bound

> **Status: implemented (M2–M4).**

| Property | Exposed as | Enforced by |
|---|---|---|
| Short-lived | `ttl`, `issued_at`, `expires_at` | class floor/ceiling at mint; absolute expiry at use |
| Audience-bound | `binding.audience` | resolution binding allow-list + injector audience check |
| Tool-scoped | `binding.tool` | injector refuses a different tool or a wider scope |
| Session-bound | `session_id` | binding hash includes the session; revoke epoch kills it |
| Single-use | hashed `secret_hash` at rest | CAS consume; a second use is not a grant |

The token value is never a field of the issuance document and is never stored; it exists only transiently at
egress. See the [issuance contract](contracts.md) and [events](events.md).
