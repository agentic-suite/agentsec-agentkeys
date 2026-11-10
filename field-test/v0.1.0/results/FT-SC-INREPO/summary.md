# FT-SC-INREPO — PASS

- pack: `conformance` · scenario: `None` · class: `P/F`
- driver: `supply-chain` · duration: 1ms
- detail: stdlib-only, security.txt, CI gate, SBOM, fuzz targets

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| checks-pass | eq | `[]` | `[]` | yes |
| sbom-format | eq | `CycloneDX` | `CycloneDX` | yes |
| security-txt | true | `True` | `True` | yes |
