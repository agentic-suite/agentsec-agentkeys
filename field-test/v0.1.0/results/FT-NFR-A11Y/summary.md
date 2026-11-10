# FT-NFR-A11Y — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `cli-output` · duration: 56ms
- detail: machine-readable, linear, colour-free output

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| json-envelope | eq | `ok` | `ok` | yes |
| stable-exit | eq | `0` | `0` | yes |
| no-ansi | absent | `[` | `{"ok": true, "exit_class": "ok", "data": {"version": "0.1.0"}, "receipts": []}
` | yes |
| no-color-env | eq | `1` | `1` | yes |
