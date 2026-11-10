# FT-CL-FIRST — WARN

- pack: `core` · scenario: `SC-01` · class: `P/F|W`
- driver: `quickstart` · duration: 586ms
- detail: scripted quickstart green in 0.58s
- limitations: no fresh field box for the timed <15-min median; the scripted path ran (plan §8)

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| scan | eq | `0` | `0` | yes |
| migrate | eq | `0` | `0` | yes |
| ref | eq | `0` | `0` | yes |
| brokered-call | eq | `0` | `0` | yes |
| revoke | eq | `0` | `0` | yes |
| replay-refused | eq | `4` | `4` | yes |
| export | eq | `0` | `0` | yes |
| verify-log | eq | `0` | `0` | yes |
| no-secret-printed | true | `True` | `True` | yes |
| elapsed-under-15min | lte | `900.0` | `0.583` | yes |
