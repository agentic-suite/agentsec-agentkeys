# FT-EV-KEYCHAIN — PASS

- pack: `evasion` · scenario: `SC-16` · class: `P/F`
- driver: `detector` · duration: 0ms
- detail: keychain read caught as a high-severity event

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| class | eq | `keychain` | `keychain` | yes |
| severity | eq | `high` | `high` | yes |
| event | eq | `evasion-detected` | `evasion-detected` | yes |
| path-recorded | contains | `/Users/u/Library/Keychains/login.keychain-db` | `keychain: /Users/u/Library/Keychains/login.keychain-db; monitor-only: keychain read outside the broker` | yes |
