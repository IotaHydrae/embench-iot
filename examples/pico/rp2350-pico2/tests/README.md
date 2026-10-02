# Offline tests for the Pico Embench port

> Board-free tests for the port's console grammar, its run verdicts and `run.py`'s
> arguments; expected values come from the firmware's `printf` format strings, the
> coremark repository's rules and real recorded logs — never from a previous run.

## Run

```sh
python3 tests/run_tests.py            # oracle report, workspace exit code
python3 tests/run_tests.py --json
python3 tests/test_output_grammar.py  # one module, plain unittest
```

No board, probe, network or pico-sdk is needed.  The coremark checkout is needed,
because the `PICO-TURBO:` state-line grammar and the "clock landed where asked"
rule are imported from `<coremark>/tools/probe_parse.py` rather than copied; when
it is absent the affected module reports `ENVIRONMENT_ERROR` (3), not `FAIL`.
`COREMARK_DIR`, or a sibling directory named `coremark`, is how it is found.

## Exit codes and oracles

```text
0 PASS   1 FAIL   2 INVALID_USAGE   3 ENVIRONMENT_ERROR   4 TIMEOUT   5 INCONCLUSIVE
```

Every module declares its oracle in `ORACLE` (`type` / `source` / `expected`), and
`run_tests.py` prints it.  Oracle types follow the workspace convention
(`../../../../../AGENTS.md`): `SPEC`, `INVARIANT`, `RELATIONSHIP`, `GOLDEN`, `BASELINE`, `NONE`,
…  A value measured once is never used as an expectation: a real log line is a
fixture for *parsing* and for the rules, not a golden score.

| Module | Oracle | What it pins down |
| --- | --- | --- |
| `test_output_grammar.py` | `SPEC` — `boardsupport.c` `printf` strings, `embench_log.py`, coremark's `parse_state_line` | the three lines' fields, at more than one clock/vreg; truncated and partial lines do not half-match |
| `test_run_validity.py` | `SPEC` (clock rule) / `INVARIANT` (pairing) — coremark's `clock_landed` + `AGENTS.md`, `run.py:outcome` | off-by-one real readings count as landed, a clamped-to-stock line does not; `pass` → 0, `FAIL`/no result → 1; a state line with no result is `stuck` |
| `test_run_args.py` | `SPEC` — `run.py` `arg_parser`/`configure_cmd`, `CMakeLists.txt`, `sconstruct.py` defaults | `--benchmark` required (exit 2); `--scale` default 1; both reach the cmake `-D` flags |

## Fixtures and their provenance

`fixtures/` are fixtures, not goldens: the tests assert the *fields and rules*, not
the scores.  Each is one of:

- **real** — copied byte for byte from a recorded log;
- **derived** — a real fragment with one line removed to reproduce a documented
  failure;
- **reconstructed** — the format and the configuration are documented, the exact
  text was not preserved.

| Fixture | Kind | Source |
| --- | --- | --- |
| `readme-example.log` | real | [`../README.md`](../README.md) output example, recorded from a run at 520 MHz, `--scale 100` |
| `state-520001-measured.log` | real | `<coremark>/probe-weact_rp2350a-20260930-105632/logs/console-520000-auto-1-1--O2.log` (a 520001 kHz reading for a 520000 kHz request) |
| `state-150000-stock.log` | real | `<coremark>/probe-weact_rp2350a-20260929-204928/logs/console-150000-auto-1-1.log` |
| `clamped-to-stock.log` | reconstructed | the clamp observation in `<pico-turbo>/boards/weact_rp2350a.cmake`: a 1.65 V request at 520 MHz left the application at the stock 150 MHz, flash 15 MHz, while the run completed |
| `stuck-no-result.log` | derived | `readme-example.log` without its result line; the failure mode is in this repository's `AGENTS.md` and `<coremark>/AGENTS.md` rule 5a — a state line with no result means the run started and stopped inside itself |
| `fail-verdict.log` | reconstructed | `readme-example.log` with the result line the `boardsupport.c` `printf` produces when `verify_benchmark` fails (`%s` = `FAIL`) |

## Reuse

The state-line parser and `clock_landed` are coremark's
(`<coremark>/tools/probe_parse.py`); this repository adds only the two Embench
lines and the verdict mapping.  If more shared parsing is wanted, the change
belongs in coremark — see [`../../../../AGENTS.md`](../../../../AGENTS.md), rule 3.

These tests say nothing about a board.  Flashing, read-back comparison and the
"No SWD during a run" rule are exercised by `../run.py` on hardware, following the
coremark hardware discipline.
