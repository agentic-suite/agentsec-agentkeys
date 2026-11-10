# FT-CL-FIRST — WARN

- pack: `core` · scenario: `SC-01` · class: `P/F|W`
- driver: `quickstart` · duration: 5496ms
- detail: scripted quickstart green; median 0.54s over 5 runs; fresh-venv install→first-call 2.7s
- limitations: the timed path ran 5x on this machine plus a fresh-venv install median; not a naive-human fresh-machine median (plan §8)

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| all-exit-codes | true | `True` | `True` | yes |
| replay-refused | true | `True` | `True` | yes |
| five-runs | eq | `5` | `5` | yes |
| no-secret-printed | true | `True` | `True` | yes |
| median-under-15min | lte | `900.0` | `0.543` | yes |
| max-under-15min | lte | `900.0` | `0.55` | yes |
| fresh-install-ok | true | `True` | `True` | yes |
| fresh-first-call-under-15min | lte | `900.0` | `0.468` | yes |
