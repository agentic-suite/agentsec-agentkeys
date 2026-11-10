# FT-EV-CLOUD — PASS

- pack: `evasion` · scenario: `SC-15` · class: `P/F`
- driver: `detector` · duration: 0ms
- detail: cloud-credential read caught as a high-severity event

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| class | eq | `cloud-credential` | `cloud-credential` | yes |
| severity | eq | `high` | `high` | yes |
| event | eq | `evasion-detected` | `evasion-detected` | yes |
| path-recorded | contains | `/home/u/.aws/credentials` | `cloud-credential: /home/u/.aws/credentials; monitor-only: cloud-credential read outside the broker` | yes |
