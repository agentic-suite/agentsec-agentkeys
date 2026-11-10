# FT-CL-TTL — PASS

- pack: `core` · scenario: `SC-05` · class: `P/F`
- driver: `expiry` · duration: 0ms
- detail: expiry fires once; no resurrection

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| first-sweep-expires | eq | `1` | `1` | yes |
| second-sweep-is-empty | eq | `0` | `0` | yes |
| one-expired-event | eq | `1` | `1` | yes |
| post-ttl-use-dead | eq | `expired` | `expired` | yes |
