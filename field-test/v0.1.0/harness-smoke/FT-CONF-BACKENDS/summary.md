# FT-CONF-BACKENDS — PASS

- pack: `conformance` · scenario: `None` · class: `P/F`
- driver: `conformance` · duration: 0ms
- detail: drivers admitted only through conformance

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| backends-pass | eq | `pass` | `pass` | yes |
| broken-refused | contains | `not conformant` | `backend broken is not conformant: missing capabilities, close, health, list, open, resolve` | yes |
