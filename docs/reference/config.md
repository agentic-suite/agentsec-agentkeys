# Config reference — references only, validated at every start

> **Status: implemented (M0–M10).** A missing, malformed, ambiguous, or secret-bearing config refuses to
> load with the failing key named. Values are never echoed back.

`agentkeys` reads `$AGENTKEYS_HOME/config.toml` (default `~/.agentkeys/config.toml`) unless `--config`
names another file. Unknown keys are refused.

| Key | Type | Required | Meaning |
|---|---|---|---|
| `enforce_mode` | `"monitor"` \| `"enforce"` | yes | evasion handling: monitor records, enforce blocks where an enforcer composes |
| `sink` | string | yes | agentwatch sink endpoint; empty means local ledger only |
| `store.path` | path | yes | SQLite store location (mode `0600`) |
| `clock.skew_tolerance` | integer ≥ 0 | yes | seconds of backwards clock drift tolerated before failing closed |
| `ttl.<class>.floor` | integer > 0 | yes (per class) | minimum honored TTL; below floor is rejected |
| `ttl.<class>.ceiling` | integer ≥ floor | yes (per class) | maximum honored TTL; never silently extended |
| `backends[].id` | string | yes | registered backend id (`keychain`, `file`) |
| `backends[].precedence` | integer ≥ 1 | yes | unique precedence order |
| `bindings[].reference` | reference (`akref:…`) | yes | the reference this binding authorizes |
| `bindings[].audience` | string | yes | the one audience (RFC 8707 resource) |
| `bindings[].tool` | string | yes | the one tool/operation |
| `step_up.gated_classes` | array of classes | no (default `["prod"]`) | classes that require an approval; never empty |
| `step_up.timeout_seconds` | integer ≥ 1 | no (default `30`) | approval window; timeout = deny |
| `step_up.policy` | string | no (default empty) | informational label for the decision source |

TTL classes are `public`, `dev`, `staging`, and `prod`.

## Example

```toml
enforce_mode = "enforce"
sink = ""

[store]
path = "~/.agentkeys/agentkeys.db"

[clock]
skew_tolerance = 30

[ttl.dev]
floor = 30
ceiling = 900

[ttl.prod]
floor = 30
ceiling = 300

[step_up]
gated_classes = ["prod"]
timeout_seconds = 30
policy = "agentpolicy"

[[backends]]
id = "keychain"
precedence = 1

[[backends]]
id = "file"
precedence = 2

[[bindings]]
reference = "akref:keychain/agentkeys/dev/example-api-token"
audience = "api.github.com"
tool = "gh"
```

## Fail-closed rules

- A literal secret anywhere in the config is refused (references only). A secret is a **location**, never
  a value.
- Duplicate backend ids/precedences and duplicate `(reference, audience, tool)` triples are refused.
- A TTL outside its class window is refused at mint time; the broker never clamps into an unsafe direction.
- An empty `step_up.gated_classes` is refused.
