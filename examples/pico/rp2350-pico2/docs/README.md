# Embench Pico port — knowledge index

> Scope: this workspace's RP2350 Pico port only (`examples/pico/rp2350-pico2/`).
> Upstream Embench and the measured results are linked, not copied.

## Scope

This repository is upstream Embench-IoT plus one port.  The knowledge base for the
workspace-owned part is this directory and the port's own `README.md`; the upstream
tree (`src/`, `support/`, `doc/`, `README.md`, `benchmark_*.py`, `ChangeLog`) is
read-only material and is not documented here.  The repository rules — the boundary,
"no SWD during a run", DWT unusable, reuse-before-copy — are in
[`AGENTS.md`](../../../../AGENTS.md).

## Index

| Document | What it answers |
| --- | --- |
| [`../README.md`](../README.md) | the port: build and run, the three console lines, the two deliberate differences from the reference port, `--scale` |
| [`../boardsupport.c`](../boardsupport.c) | source of truth for the output grammar (`printf`) and the timing hooks `start_trigger`/`stop_trigger` |
| [`../run.py`](../run.py) | one benchmark on the board; imports coremark's flash path and console reader, judges the log |
| [`../embench_log.py`](../embench_log.py) | the console grammar in one place, imported by both `run.py` and the tests |
| [`../tests/README.md`](../tests/README.md) | the board-free tests: output grammar, run validity, `run.py` arguments |
| [`../boards/weact_rp2350a.h`](../boards/weact_rp2350a.h) | why this board has a name of its own; the measured ceiling lives in pico-turbo |
| [`../../../../AGENTS.md`](../../../../AGENTS.md) | repository rules: boundary, SWD discipline, DWT, `--scale`, drift check |

## Canonical sources elsewhere (link, do not copy)

| Knowledge | Canonical document |
| --- | --- |
| Hardware discipline, SWD/soak/pairing rules, board limits | [`<coremark>/AGENTS.md`](../../../../../coremark/AGENTS.md) |
| Compiler ladder and the measured `statemate` / `matmult-int` differences | [`<coremark>/TOOLCHAINS.md`](../../../../../coremark/TOOLCHAINS.md) |
| Per-board scores, the `time_us_32()` 0.05% check (section 8) | [`<coremark>/RANKINGS.md`](../../../../../coremark/RANKINGS.md) |
| Clock, voltage and flash divider interpretation | [`<pico-turbo>/docs/measurements.md`](../../../../../pico-turbo/docs/measurements.md) |
| Embench harness contract (`start_trigger`/`stop_trigger`, GDB reference flow) | [`doc/README.md`](../../../../doc/README.md) |

`<coremark>` and `<pico-turbo>` are sibling checkouts, which is also what `run.py`
assumes (`COREMARK_DIR`, or a sibling directory named `coremark`).

## Maintenance

- Upstream is never rewritten; keep this repository's documents in English.
- One fact, one canonical document: the results table lives in `<coremark>`, the
  clock configuration in `pico-turbo`.  Add only what is new here, and link.
- Every change re-runs the drift check against `boardsupport.c`, `run.py` and
  `CMakeLists.txt`, then `python3 ../tests/run_tests.py` (see
  [`AGENTS.md`](../../../../AGENTS.md), rule 6).
