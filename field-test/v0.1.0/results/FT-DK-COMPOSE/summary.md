# FT-DK-COMPOSE — PASS

- pack: `docker` · scenario: `None` · class: `P/F`
- driver: `compose-up` · duration: 3587ms
- detail: topology boots and reports healthy services

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| up-exit | eq | `0` | `0` | yes |
| broker-running | true | `True` | `True` | yes |
