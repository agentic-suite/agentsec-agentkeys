# FT-CL-ROTATE — PASS

- pack: `core` · scenario: `SC-06` · class: `P/F`
- driver: `rotation` · duration: 0ms
- detail: rotation is picked up per resolve; old token dies at TTL

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| v1-read | eq | `rotated-v1` | `rotated-v1` | yes |
| v2-read-without-restart | eq | `rotated-v2` | `rotated-v2` | yes |
| pre-rotation-token-dead | eq | `expired` | `expired` | yes |
