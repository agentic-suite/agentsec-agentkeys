# FT-OPS-BACKUP — PASS

- pack: `ops` · scenario: `None` · class: `P/F`
- driver: `backup` · duration: 3ms
- detail: WAL-safe backup with verified chain head

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| rows | eq | `3` | `3` | yes |
| chain-head | present | `True` | `02fde7a0ab6b57f2fcb7d20707c2c98878fcf8699169ca49a1a949f9653365a0` | yes |
| manifest-0600 | eq | `384` | `384` | yes |
| secret-free-manifest | contains | `"contains_secrets": false` | `{"chain_head": "02fde7a0ab6b57f2fcb7d20707c2c98878fcf8699169ca49a1a949f9653365a0", "contains_secrets": false, "contents": "references, bindings, issuance hashes, ledger, receipts", "created_at": 1234, "path": "/var/folders/1y/8cvcsmv53m7c2gzqb6gp09p40000gn/T/ak-FT-OPS-BACKUP-082sbii1/backup.db", "rows": 3, "schema_version": 1}` | yes |
