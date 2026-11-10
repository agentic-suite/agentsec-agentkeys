# FT-EV-ENFORCE — PASS

- pack: `evasion` · scenario: `SC-17` · class: `P/F|W`
- driver: `enforce-hook` · duration: 0ms
- detail: enforce mode: OS filesystem deny composed and the read is provably blocked; without an enforcer the gap is named

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| gap-named-without-enforcer | true | `True` | `True` | yes |
| never-claims-block | true | `True` | `True` | yes |
| blocked-when-composed | true | `True` | `True` | yes |
| composed-block-is-real | true | `True` | `True` | yes |
