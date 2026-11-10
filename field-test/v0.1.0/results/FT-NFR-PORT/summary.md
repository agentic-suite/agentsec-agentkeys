# FT-NFR-PORT — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `platform` · duration: 56ms
- detail: platform darwin; Windows not claimed

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| supported-platform | true | `True` | `True` | yes |
| cli-version-exit | eq | `0` | `0` | yes |
| windows-not-claimed | absent | `Windows is supported` | `v0.1.0 supports macOS and Linux` | yes |
