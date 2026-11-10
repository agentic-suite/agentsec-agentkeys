# FT-ST-NOPASSTHRU — PASS

- pack: `stdio` · scenario: `SC-13` · class: `P/F`
- driver: `stdio-strip` · duration: 0ms
- detail: no client token reaches the child or the upstream

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| literal-client-credential-stripped | eq | `('GITHUB_TOKEN',)` | `('GITHUB_TOKEN',)` | yes |
| placeholder-kept | contains | `AGENTKEYS_SCOPED_TOKEN` | `{'AGENTKEYS_SCOPED_TOKEN': 'akref:file/x/y'}` | yes |
| header-client-token-absent | true | `True` | `True` | yes |
| child-token-is-broker-minted | true | `True` | `True` | yes |
