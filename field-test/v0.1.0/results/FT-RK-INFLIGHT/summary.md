# FT-RK-INFLIGHT — PASS

- pack: `killtime` · scenario: `SC-26` · class: `P/F`
- driver: `use-after-revoke` · duration: 0ms
- detail: the next hop after revoke fails closed

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| next-hop-refused | eq | `rejected` | `rejected` | yes |
| revoke-epoch-set | eq | `1` | `1` | yes |
| revoke-recorded | eq | `1` | `1` | yes |
