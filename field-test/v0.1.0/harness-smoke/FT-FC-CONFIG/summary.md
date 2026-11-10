# FT-FC-CONFIG — PASS

- pack: `failclosed` · scenario: `SC-20` · class: `P/F`
- driver: `config` · duration: 0ms
- detail: ambiguous/partial config is refused loudly

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| refused | present | `True` | `missing required key: sink` | yes |
| names-the-field | contains | `missing required key` | `missing required key: sink` | yes |
