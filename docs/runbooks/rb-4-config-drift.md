# Config drift / integrity failure

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

`doctor` reports `config-tampered` or a digest mismatch.

## Steps

1. Diff the config against the reviewed copy.
2. Re-pin the digest only after review (`config.toml.sha256`).

## Verification

`agentkeys doctor` `config-integrity` is green; no literal secret in the config.
