# Embench on a Pico 2, clocked by pico-turbo

> Nineteen Embench workloads, one per build, on a WeAct RP2350A: pico-turbo owns the
> clock, the application times itself with `time_us_32()` and prints its own result,
> and nothing touches SWD while a timed region is running.

## TL;DR

- One run: `COREMARK_DIR=<coremark> PICO_SDK_PATH=<pico-sdk> ./run.py --benchmark statemate --scale 100`.
- The console carries three lines: the chip's own state report, the benchmark with its `--scale`, and the result.  The result line is also the line that says the run finished.
- **No debugger during a run** — one halt costs that round its timing while the benchmark's checksum stays correct.  SWD is used only *around* the run (identify, blank, read back).
- **The RP2350 DWT cycle counter does not count** (11 s at 150 MHz read 168 cycles), so the port times with the SDK's `time_us_32()`.
- `run.py` imports coremark's flash path and console reader rather than copying them.
- Quote every number with its `--scale`, benchmark, board, clock and compiler.  **2 of 19 benchmarks have been measured so far**; the results are in `<coremark>/TOOLCHAINS.md`.

## The port

One Embench benchmark per build, with the clock, the core voltage and the flash
divider owned by [pico-turbo](https://github.com/IotaHydrae/pico-turbo) exactly as in
the [coremark repository](https://github.com/IotaHydrae/coremark) this was ported
from.  The point of running nineteen benchmarks instead of one is the question
CoreMark cannot answer on its own: whether a compiler that is 5% slower on CoreMark
is 5% slower at everything, or whether CoreMark happened to contain the one function
that compiler translates badly.

```sh
COREMARK_DIR=<coremark> PICO_SDK_PATH=<pico-sdk> \
  ./run.py --benchmark statemate --scale 100
```

`run.py` builds, flashes, reads the flash back and compares it with the build, runs,
and prints the result.  It imports the coremark repository's flash path and console
reader rather than copying them: blanking the flash through the debugger (which
brings the bootrom's USB up), writing with picotool through the bootrom, reading the
image back over SWD, and holding the CDC port open before the application starts are
the parts of that bench that were learned the hard way, and two copies of them would
drift.

```
PICO-TURBO: 520000 kHz asked, 520000 kHz configured, 520000 kHz measured, vreg sel 19, flash 52000 kHz, clk_peri 520000 kHz, usb ok
EMBENCH: statemate scale 100 heat 1
EMBENCH-PICO: statemate 702013 us pass
```

The first line is the chip's own report of what it is doing, measured with the
hardware frequency counter rather than read back out of the configuration; the second
fixes the benchmark and the scaling that produced the number; the third is the result,
and it is also the line that says the run finished.

## Two deliberate differences from the reference port

**No debugger during a run.**  Embench's reference flow
([`pylib/run_stm32f4-discovery.py`](../../../pylib/run_stm32f4-discovery.py),
documented in [`doc/README.md`](../../../doc/README.md)) drives a GDB session
and breaks on `start_trigger` and `stop_trigger`, reading the Cortex-M DWT cycle
counter (`*0xe0001004`) at each and the verification return value out of `$r0` at
exit.  This bench rejects that: **nothing may touch SWD while a run is in progress**,
because a halt costs that round its timing while leaving the benchmark's checksum
correct -- a validated result with a wrong number, which is the worst kind.  So the
application prints its own line and the host only reads the console.  The probe is
still used *around* the run -- to identify the chip, to blank the flash and to read
the image back -- but never between the two triggers, so the timing does not depend on
a debugger session being attached and powered during the timed region.

**Microseconds, not cycles.**  The reference `boardsupport.c` times with the Cortex-M
cycle counter in DWT.  **That counter does not count on this chip.**  With the same
enable sequence (`DEMCR.TRCENA`, then `DWT_CTRL.CYCCNTENA`) an eleven-second timed
region at 150 MHz read **168** cycles where 1.68e9 were expected.  The likely reason
is that the debug and trace blocks sit in a power domain a debugger has to bring up
-- **a hypothesis, not verified** -- and, per the paragraph above, that is not
something to depend on here.  The port times with the SDK's `time_us_32()` instead,
the same timer the coremark port uses; that port's timer was checked against the
host's clock to 0.05% (`<coremark>/RANKINGS.md`, section 8).  **This port has not been
re-checked independently** -- the agreement is inherited from the shared timer, not
re-measured here.

This costs one thing and buys another.  It costs the obvious instrument for the
question "did the newer compiler emit more instructions, or make each one more
expensive?" -- a cycle count next to an instruction count would have separated those,
and without DWT this bench has no finer instrument than a microsecond.  It buys the
removal of a host-side parameter: the reference converts cycles to milliseconds with a
`cpu_mhz` it has to be told, whereas here the tick *is* time and the clock the chip
measured itself at is on the first line.

## Scaling

Embench sizes each benchmark so that a run takes about four seconds **on the platform
its numbers were published for**.  On a chip at 520 MHz the same work is over in
milliseconds: `statemate` at `--scale 1` takes 7 ms, which is why the example above
uses `--scale 100` to reach about 0.7 s.  `--scale` is Embench's
`GLOBAL_SCALE_FACTOR`, which all nineteen benchmarks honour, and a number here should
always be quoted with it -- the second output line is there for that reason.

## Status

Ported and running.  **Two of the nineteen benchmarks have been measured so far**
(`statemate`, `matmult-int`); the tables, with the compilers and clocks they were
measured at, are in the coremark repository's `TOOLCHAINS.md`.  Two points are not a
geometric mean: a GM/GSD over the suite needs all nineteen.
