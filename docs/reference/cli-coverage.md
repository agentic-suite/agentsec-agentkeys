# CLI coverage test — no flag ships undocumented

**Status:** test plan for M13 (`13.1`). The test walks the argparse tree and fails when a flag is missing
from [`docs/reference/cli.md`](cli.md), or when the doc names a flag the parser does not have.

```python
# tests/docs/test_cli_coverage.py (shape)
parser = _build_parser()
flags = walk(parser)            # every option string, recursively, except -h/--help
doc = Path("docs/reference/cli.md").read_text()
assert {flag for flag in flags if flag not in doc} == set()
```

The reverse direction is checked against the documented flag rows for the commands that exist, so a
renamed or removed flag fails the build instead of drifting.
