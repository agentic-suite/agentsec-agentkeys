# Backend conformance suite — a guide for driver authors (v0.1.0)

**Status:** implemented in M3 · **Suite:** [`tests/backends_conformance.py`](../../tests/backends_conformance.py) ·
**Design:** [backends design](../design/v0.1.0/backends.md) §6.

**BLUF:** A backend is trustworthy only if it passes the same suite the keychain and file drivers pass. The
suite is strict — deliberately broken drivers must fail it — so a green run means resolve-at-use, never-log,
fail-closed, and honest capabilities all hold.

## Running it

```python
from tests.backends_conformance import run_backend_conformance
from agentkeys.backends.keychain import KeychainBackend

findings = run_backend_conformance(
    lambda key: KeychainBackend(service="agentkeys", runner=my_runner, platform="darwin"),
    slot="agentkeys/dev/token",
    value="the-value-the-driver-resolves",
)
assert findings == [], findings
```

The factory receives a namespace key and must return a backend **isolated to that key**; each check runs
against its own instance, so a file-backed driver cannot see another check's writes.

## What it asserts

| Check | Meaning |
|---|---|
| `capabilities_are_declared` | `capabilities()` returns `BackendCapabilities` at the current conformance version |
| `resolve_returns_an_opaque_secret` | `resolve` returns a `SecretValue`; `repr`/`str` never reveal the value |
| `an_unknown_slot_fails_closed` | an unknown slot raises a `BackendError` — never a value, never a fallback |
| `listing_never_leaks_a_value` | `list()` returns paths only (or reports the enumeration limitation) |
| `health_is_valid_and_non_secret` | a valid health state and a detail that carries no value |
| `file_backed_drivers_enforce_owner_only_permissions` | a file-backed driver's material is `0600` |
| `capabilities_are_honest_about_file_backing` | `file_backed` matches whether the driver reads a file |

## Proving the suite can fail

`tests/backends_fakes.py` provides `LeakyBackend` (returns a bare string), `FallbackBackend` (falls back to
an environment variable), and `ValueListingBackend` (leaks values through `list()`);
`tests/test_backends_conformance.py` asserts each one fails with the expected finding.

## Writing a new backend

1. Implement the full `Backend` surface (`resolve`, `list`, `health`, `capabilities`, `open`, `close`) and
   declare honest capability flags. `admit_backend` refuses a driver that is missing a method.
2. Never cache plaintext, never write it to disk, and never fall back — raise the matching `BackendError`.
3. Register it with the engine (`FailClosedEngine.register`) and run this suite in your own tests.

## Honest limits

- The suite checks shape, honesty, and the fail-closed posture; it does not test a third-party driver's
  unlock semantics or its platform integration.
- Install-time conformance gating for third-party backends arrives with the conformance kit (M11, E13).