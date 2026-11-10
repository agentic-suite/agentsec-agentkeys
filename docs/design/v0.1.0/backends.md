# Backends design — contract, drivers, fail-closed engine, redactor (M3)

**Status:** design of record for M3 · **Issue:** #42 (`3.D0`) · **Written before implementation.**
**Sources:** [PRD 02 §6](../../prd/02-architecture.md), [PRD 15 §7](../../prd/15-data-model.md),
[PRD 13 §4](../../prd/13-non-functional-requirements.md), [store design](store.md).

**BLUF:** One `Backend` contract, two drivers (OS keychain, credential file), one **fail-closed engine**
whose fault matrix is 100% deny-or-pending, and one **redactor** that masks before storage/render/export and
emits a receipt per masked field. The plaintext secret exists only inside a `SecretValue` that cannot be
logged; `resolve` returns it and the caller must explicitly `reveal()` it at the moment of use.

---

## 1. The contract

```python
class SecretValue:                    # never loggable, never serialisable
    def reveal(self) -> str: ...      # the only way to obtain plaintext
    def __repr__(self) -> str:        # "<SecretValue:redacted>"

class BackendCapabilities:            # frozen dataclass
    read_only: bool                   # cannot create/update entries
    interactive_unlock: bool          # may need an unlock (keychain)
    file_backed: bool                 # material is a file (permissions matter)
    conformance_version: str          # "1.0" — raised when the contract changes

class BackendHealth:                  # frozen dataclass
    state: Literal["healthy", "locked", "absent", "ambiguous", "unconfigured"]
    detail: str

class Backend(Protocol):
    backend_id: str
    kind: str                          # "keychain" | "file" | a third-party kind
    def capabilities(self) -> BackendCapabilities: ...
    def open(self) -> None: ...
    def close(self) -> None: ...
    def resolve(self, path: str) -> SecretValue: ...   # fail closed on every error
    def list(self) -> tuple[str, ...]: ...
    def health(self) -> BackendHealth: ...
```

**Errors** (all `BackendError` subclasses) are the *vocabulary of denial*:
`BackendLocked`, `BackendAbsent`, `BackendAmbiguous`, `BackendUnavailable`, `BackendPermissionError`.

Rules, normative:

- `resolve` returns a `SecretValue`, never a bare `str`; a driver that returns a string is refused by the
  loader (same admission approach as store drivers).
- `resolve` **never** logs, never caches across calls, and never falls back to an environment variable, a
  config value, or a stale copy. Any failure raises; there is no partial success.
- `list` returns slot **paths**, never values.
- `health` is non-secret and cheap enough for `doctor`.

## 2. Drivers

| Driver | `kind` | Caps | Notes |
|---|---|---|---|
| keychain | `"keychain"` | `interactive_unlock=True` | macOS `security find-generic-password -w -s <service> -a <path>`; Linux `secret-tool lookup`. Unlock-per-resolve; never writes plaintext to disk. Run through an injectable `CommandRunner` so tests never touch a real keychain. |
| file | `"file"` | `file_backed=True`, `read_only=True` | A `0600` credential file (JSON object of `path → value` or `path\nvalue`). Permissions enforced **at open and at resolve** (`umask 000` cannot widen them). `doctor` warns loudly when a file backend is in use. |

Both drivers share one conformance suite; a deliberately broken backend must fail it.

## 3. Fail-closed engine

`FailClosedEngine(backends)` resolves a reference to a secret or a **structured denial**:

```python
@dataclass(frozen=True)
class Denial:
    reason: Literal["backend-locked", "backend-absent", "backend-ambiguous",
                    "backend-unavailable", "backend-permission", "unknown-backend"]
    detail: str                        # actionable, never a value

def resolve(self, backend_id: str, path: str) -> SecretValue | Denial
```

Normative properties (the fault matrix):

1. **No fallback, ever** — no env var, no config value, no cached plaintext, no static default. A denial is
   returned; issuance is denied by the caller with `resolve`'s reason.
2. **Ambiguity is refusal** — a backend id that is not registered, a duplicate registration, or a path that
   matches more than one entry is `backend-ambiguous`/`unknown-backend`, never first-match-wins.
3. **Pending is allowed, allow is not** — `BackendLocked` may be reported as *pending* by a deployment that
   is mid-unlock; the engine says `backend-locked` and issuance waits or denies. It never proceeds.
4. Every denial is returned with a reason that names the backend and path but never a value.

`doctor` renders the engine's registry + health so the effective setup is explained (M0's `doctor` grows a
`backends` check detail).

## 4. Redactor + receipts

`redact(text) -> Redaction(text, receipts)`; `receipts` are `RedactionReceipt(receipt_id, subject, field,
class, count, redactor_version, created_at)` rows written through the store.

| Class | Shape |
|---|---|
| `api-key` | `sk-…`, `ghp_…`, `github_pat_…`, `AKIA…` |
| `bearer` | `Bearer <token>`, `Authorization: …` |
| `private-key` | `-----BEGIN … PRIVATE KEY-----` blocks (masked to the end marker) |
| `connection-string` | `scheme://user:pass@host` |
| `jwt` | `eyJ….eyJ….…` |
| `slack-token` | `xox[baprs]-…` |
| `env-assignment` | `NAME=<masked>` for a secret-shaped value |

Rules: redaction runs **before** anything is stored, rendered, or exported (I7); the masked form keeps a
short safe tail (`***…7f2a`) so a human can correlate without learning the value; a receipt is emitted once
per masked field with a count; the redactor never receives a `SecretValue` (callers pass text, and
`SecretValue` refuses to be interpolated). The pattern set is the **same single source** used by the M0
config validator and the M2 contract guards (`agentkeys.redact` re-exports them).

## 5. Rotation without restart (CUJ-10)

A reference re-resolves per use; the engine holds **no** cached plaintext, so rotating the backend slot is
picked up on the next resolve. A test rotates a slot and asserts the next resolve returns the new value and
the old one is never seen again.

## 6. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 3.1 | `tests/test_backend_contract.py` | `SecretValue` cannot be revealed by `repr`/`str`/f-string/JSON; capability + health records; error vocabulary |
| 3.2 | `tests/test_backend_keychain.py` | resolve/list/health through a fake `CommandRunner`; locked → `BackendLocked`; per-resolve unlock; never a value in `list` |
| 3.3 | `tests/test_backend_file.py` | `0600` enforced at open and resolve under `umask 000`; wrong perms → `BackendPermissionError`; malformed file → `BackendAbsent`/ambiguous |
| 3.4 | `tests/backends_conformance.py` | one suite for both drivers; a broken backend fails it |
| 3.5 | `tests/test_failclosed_matrix.py` | every backend failure → a `Denial` (or pending), never a value; no fallback path exists |
| 3.6 | `tests/test_redactor_receipts.py` | every class masked; receipt per field; masked output scan finds 0 secrets; store/export contain no plaintext |

## 7. Review

Settled here: (1) `resolve` returns an opaque `SecretValue`, so a log line cannot leak it; (2) drivers are
gated by the same admission + conformance posture as store drivers; (3) ambiguity is always a refusal;
(4) the redactor reuses the M0/M2 pattern single source instead of a third copy; (5) no caching, so rotation
works (CUJ-10). Deferred: enterprise/cloud backends (R10, v0.1.x), backend conformance *gating at install*
(M11), evasion detection (M9).

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `3.CR`.