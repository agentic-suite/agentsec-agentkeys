# FT-EV-DOTENV — PASS

- pack: `evasion` · scenario: `SC-14` · class: `P/F`
- driver: `detector` · duration: 0ms
- detail: dotenv read caught as a high-severity event

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| class | eq | `dotenv` | `dotenv` | yes |
| severity | eq | `high` | `high` | yes |
| event | eq | `evasion-detected` | `evasion-detected` | yes |
| path-recorded | contains | `.env` | `dotenv: .env; monitor-only: dotenv read outside the broker` | yes |
