# FT-OPS-BACKUP — PASS

- pack: `ops` · scenario: `None` · class: `P/F`
- driver: `backup` · duration: 3ms
- detail: WAL-safe backup with verified chain head

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| rows | eq | `3` | `3` | yes |
| chain-head | present | `True` | `8e0a1e6cb7be3c8f5f6d9cecdbf7ab5c240b4b1113aaa4aa564bf10ddbfe9095` | yes |
| manifest-0600 | eq | `384` | `384` | yes |
| secret-free-manifest | contains | `"contains_secrets": false` | `{"chain_head": "8e0a1e6cb7be3c8f5f6d9cecdbf7ab5c240b4b1113aaa4aa564bf10ddbfe9095", "contains_secrets": false, "contents": "references, bindings, issuance hashes, ledger, receipts", "created_at": 1234, "path": "/var/folders/1y/8cvcsmv53m7c2gzqb6gp09p40000gn/T/ak-FT-OPS-BACKUP-qwjqaf9a/backup.db", "rows": 3, "schema_version": 1}` | yes |
