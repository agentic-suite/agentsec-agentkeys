# Field-test traceability — v0.1.0

> Generated from `cases.yaml`, committed results, and the hand-maintained report.
> Verdicts in the report are hand-entered; this file only proves every plan case
> has a case, a result, and a row.

| Case | Plan scenario | Requirements | Feature | CUJ | Result | Report row |
|---|---|---|---|---|---|---|
| FT-AG-OFFLINE | SC-39 | R5, E4, E12 | F16 | CUJ-11 | pass | yes |
| FT-AP-CONTEXTDUMP | SC-40 | R1, E5, E10 | F19 | CUJ-3 | pass | yes |
| FT-AP-EVIDENCE | SC-43 | E5, E10 | F19 | CUJ-3 | pass | yes |
| FT-AP-FLOOD | — | E4, E10 | F19 | CUJ-6 | pass | yes |
| FT-AP-TAMPER | SC-41 | R1, E5, E10 | F19 | CUJ-3 | pass | yes |
| FT-AP-WIDEN | SC-42 | E7 | F19 | CUJ-5 | pass | yes |
| FT-BR-AUDIENCE | SC-08 | R3, E3, E7 | F5 | CUJ-5 | pass | yes |
| FT-BR-SESSION | SC-10 | R3, E3, E7 | F5 | CUJ-5 | pass | yes |
| FT-BR-STALE | SC-11 | R3, E3, E7 | F5 | CUJ-5 | pass | yes |
| FT-BR-TOOL | SC-09 | R3, E3, E7 | F5 | CUJ-5 | pass | yes |
| FT-CL-ENV | SC-02 | R2, E7 | F2 | CUJ-1 | pass | yes |
| FT-CL-EXCHANGE | SC-04 | R2, E7 | F4 | CUJ-1 | pass | yes |
| FT-CL-FIRST | SC-01 | R1, R2, R5, R17, E1, E7 | F1 | CUJ-1 | warn | yes |
| FT-CL-HEADER | SC-03 | R2, E7, E14 | F3 | CUJ-12 | pass | yes |
| FT-CL-ROTATE | SC-06 | R1, R5, E6 | F7 | CUJ-10 | pass | yes |
| FT-CL-TTL | SC-05 | E6 | F5 | — | pass | yes |
| FT-CL-TWOHARNESS | SC-07 | E8 | F17 | CUJ-12 | pass | yes |
| FT-CONF-BACKENDS | — | E9, E13 | F18 | CUJ-13 | pass | yes |
| FT-CONF-STANDARDS | — | E13 | F18 | CUJ-14 | pass | yes |
| FT-DK-AIRGAP | SC-39 | E4, E12 | F16 | CUJ-11 | not-run | yes |
| FT-DK-BOUNDARY | — | R8, E10 | F12 | CUJ-4 | not-run | yes |
| FT-DK-COMPOSE | — | E2, E4 | F15 | — | not-run | yes |
| FT-DK-EVIDENCE | SC-43 | E5 | F19 | CUJ-3 | not-run | yes |
| FT-DK-IMAGE | — | E2, E15 | F15 | — | not-run | yes |
| FT-DK-QUICKSTART | SC-01 | R1, R17 | F1 | CUJ-1 | not-run | yes |
| FT-DK-SINGLEWRITER | — | E2 | F15 | — | not-run | yes |
| FT-EV-CLOUD | SC-15 | R7, E10 | F11 | CUJ-6 | pass | yes |
| FT-EV-DOTENV | SC-14 | R7, E10 | F11 | CUJ-6 | pass | yes |
| FT-EV-ENFORCE | SC-17 | R7, E10 | F11 | CUJ-6 | warn | yes |
| FT-EV-KEYCHAIN | SC-16 | R7, E10 | F11 | CUJ-6 | pass | yes |
| FT-FC-ABSENT | SC-19 | R5, E4, E9 | F8 | CUJ-8 | pass | yes |
| FT-FC-CONFIG | SC-20 | E4 | F16 | CUJ-8 | pass | yes |
| FT-FC-CRASH | SC-23 | E1, E2, E4 | F15 | — | pass | yes |
| FT-FC-LOCKED | SC-18 | R5, E4, E9 | F8 | CUJ-8 | pass | yes |
| FT-FC-SINK | SC-22 | E4, E12 | F9 | CUJ-9 | pass | yes |
| FT-FC-STORE | SC-21 | E2, E4 | F15 | CUJ-8 | pass | yes |
| FT-HC-CLAUDE | SC-35 | E8 | F17 | CUJ-12 | pass | yes |
| FT-HC-CURSOR | SC-36 | E8 | F17 | CUJ-12 | warn | yes |
| FT-HC-GENERIC | SC-37 | E1, E8 | F20 | CUJ-13 | pass | yes |
| FT-HC-NOTYET | SC-38 | E8 | F17 | CUJ-14 | pass | yes |
| FT-HONESTY-GAPS | — | E15 | F18 | CUJ-14 | pass | yes |
| FT-HONESTY-REPORT | — | E15 | F18 | CUJ-14 | pass | yes |
| FT-LA-EVENT | SC-32 | R6, E12 | F9 | CUJ-9 | pass | yes |
| FT-LA-EXPORT | SC-29 | R6, E12 | F10 | CUJ-9 | pass | yes |
| FT-LA-NOSECRET | SC-31 | E5, E12 | F14 | CUJ-9 | pass | yes |
| FT-LA-TAMPER | SC-30 | R6, E12 | F10 | CUJ-9 | pass | yes |
| FT-MP-SCANMIGRATE | SC-51 | R17 | F21 | CUJ-1 | pass | yes |
| FT-NFR-A11Y | — | E4 | F16 | — | pass | yes |
| FT-NFR-BACKEND | — | R5 | F7 | — | pass | yes |
| FT-NFR-CLOCK | SC-05 | E6 | F5 | — | pass | yes |
| FT-NFR-COLDSTART | — | E2 | F15 | — | pass | yes |
| FT-NFR-INJECT | — | E7 | F2 | — | pass | yes |
| FT-NFR-LEDGER | — | R6 | F9 | — | pass | yes |
| FT-NFR-PORT | — | E4 | F16 | — | pass | yes |
| FT-NFR-RESTART | — | E2 | F15 | — | pass | yes |
| FT-NFR-RSS | — | E2 | F15 | — | pass | yes |
| FT-NFR-THROUGHPUT | — | R3 | F5 | — | pass | yes |
| FT-OPS-BACKUP | — | E11, E12 | F15 | CUJ-9 | pass | yes |
| FT-OPS-DOCTOR | — | E4, E10 | F8 | CUJ-8 | pass | yes |
| FT-OPS-DRILL | — | R4 | F6 | CUJ-2 | pass | yes |
| FT-OPS-MIGRATE | — | E11 | F15 | CUJ-8 | pass | yes |
| FT-OPS-RESTORE | SC-30 | E11, E12 | F15 | CUJ-9 | pass | yes |
| FT-OPS-RETENTION | — | E12 | F9 | CUJ-9 | pass | yes |
| FT-OPS-SERVE | — | E2, E10 | F15 | CUJ-8 | pass | yes |
| FT-RK-ATTR | SC-28 | R4, R6 | F6 | CUJ-2 | pass | yes |
| FT-RK-INFLIGHT | SC-26 | R4, E3 | F6 | CUJ-2 | pass | yes |
| FT-RK-KILLTIME | SC-24 | R4, E3, E6 | F6 | CUJ-2 | pass | yes |
| FT-RK-SCOPE | SC-25 | R4 | F6 | CUJ-2 | pass | yes |
| FT-RK-UNKNOWN | SC-27 | R4 | F6 | CUJ-2 | pass | yes |
| FT-SC-INREPO | — | E15 | F18 | CUJ-14 | pass | yes |
| FT-ST-NOPASSTHRU | SC-13 | R8, E14 | F12 | CUJ-4 | pass | yes |
| FT-ST-NOSECRET | SC-12 | R8, E7, E14 | F12 | CUJ-4 | pass | yes |
| FT-SU-APPROVED | SC-33 | R9, E3, E9 | F13 | CUJ-7 | pass | yes |
| FT-SU-DENIED | SC-34 | R9, E3, E9 | F13 | CUJ-7 | pass | yes |
