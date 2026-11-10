# FT-FC-ABSENT — PASS

- pack: `failclosed` · scenario: `SC-19` · class: `P/F`
- driver: `backend` · duration: 0ms
- detail: absent backend refuses (no fallback path)

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| absent-refused | eq | `absent` | `absent` | yes |
| no-fallback | absent | `fallback` | `denied` | yes |
