# FT-EV-ENFORCE — WARN

- pack: `evasion` · scenario: `SC-17` · class: `P/F|W`
- driver: `enforce-hook` · duration: 0ms
- detail: enforce mode names the gap where no enforcer composes
- limitations: no OS-level enforcer composed; the gap is named (plan §8)

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| gap-named-without-enforcer | true | `True` | `True` | yes |
| never-claims-block | true | `True` | `True` | yes |
| blocked-when-composed | true | `True` | `True` | yes |
