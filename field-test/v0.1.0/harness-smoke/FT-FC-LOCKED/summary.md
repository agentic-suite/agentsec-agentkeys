# FT-FC-LOCKED — PASS

- pack: `failclosed` · scenario: `SC-18` · class: `P/F`
- driver: `backend` · duration: 0ms
- detail: locked backend denies with a reason

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| denied | eq | `backend-locked` | `backend-locked` | yes |
| no-value | absent | `SecretValue` | `Denial(reason='backend-locked', detail='backend locked: locked/token')` | yes |
