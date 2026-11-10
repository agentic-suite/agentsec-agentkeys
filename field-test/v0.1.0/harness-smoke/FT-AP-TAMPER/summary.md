# FT-AP-TAMPER — PASS

- pack: `attack` · scenario: `SC-41` · class: `P/F`
- driver: `tamper` · duration: 0ms
- detail: config, ledger, and spoof tamper all fail closed

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| config-tamper | contains | `config-tampered` | `config-tampered: 6afe68c3c686 != dd5686bccb08` | yes |
| ledger-tamper | true | `True` | `True` | yes |
| spoof-refused | contains | `ref_invented` | `unknown reference_id: ref_invented` | yes |
