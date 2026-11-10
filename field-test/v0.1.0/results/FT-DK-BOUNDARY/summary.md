# FT-DK-BOUNDARY — PASS

- pack: `docker` · scenario: `None` · class: `P/F`
- driver: `compose-exec` · duration: 264ms
- detail: the child container has no path to the broker store or credentials

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| child-isolated | eq | `0` | `0` | yes |
| marks-isolated | contains | `isolated` | `isolated
` | yes |
