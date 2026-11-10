# FT-DK-IMAGE — PASS

- pack: `docker` · scenario: `None` · class: `P/F`
- driver: `compose-inspect` · duration: 3308ms
- detail: image built; user=10001:10001

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| build-exit | eq | `0` | `0` | yes |
| non-root-user | true | `True` | `True` | yes |
| no-secret-in-dockerfile | eq | `()` | `()` | yes |
