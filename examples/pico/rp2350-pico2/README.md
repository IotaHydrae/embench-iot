# Embench on a Pico 2, clocked by pico-turbo

One Embench benchmark per build, on a WeAct RP2350A, with the clock, the core voltage
and the flash divider owned by [pico-turbo](https://github.com/IotaHydrae/pico-turbo)
exactly as in the [coremark repository](https://github.com/IotaHydrae/coremark) this
was ported from.  The point of running nineteen benchmarks instead of one is the
question CoreMark cannot answer on its own: whether a compiler that is 5% slower on
CoreMark is 5% slower at everything, or whether CoreMark happened to contain the one
function that compiler translates badly.

```sh
COREMARK_DIR=<coremark> PICO_SDK_PATH=<pico-sdk> \
  ./run.py --benchmark statemate
```

`run.py` builds, flashes, reads the flash back and compares it with the build, runs,
and prints the result.  It imports the coremark repository's flash path and console
reader rather than copying them -- erasing through the bootrom, writing with
picotool, and holding the CDC port open before the application starts are the parts
of that bench that were learned the hard way, and two copies of them would drift.

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

**No GDB.**  Embench's own runner for the reference Arm platform drives a GDB session
and sets breakpoints on `start_trigger` and `stop_trigger` to read a register at each.
That bench has one rule this one does not: nothing may touch SWD while a run is in
progress, because a halt costs that round its timing while leaving the CRCs correct --
a validated result with a wrong number, which is the worst kind.  So the application
prints its own line and the host only reads the console.  It also means the timing
does not depend on a debugger being attached and powered.

**Microseconds, not cycles.**  The reference `boardsupport.c` times with the Cortex-M
cycle counter in DWT.  **That counter does not count on this chip.**  With the same
enable sequence (`DEMCR.TRCENA`, then `DWT_CTRL.CYCCNTENA`) an eleven-second timed
region at 150 MHz read **168** cycles where 1.68e9 were expected.  The likely reason is
that the debug and trace blocks sit in a power domain a debugger has to bring up --
which, per the paragraph above, is not a thing to depend on here.  The port times with
the SDK's `time_us_32()` instead, which is what the coremark port uses and which was
checked against the host's clock to 0.05%.

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
milliseconds: `statemate` at `--scale 1` takes 7 ms.  `--scale` is Embench's
`GLOBAL_SCALE_FACTOR`, which all nineteen benchmarks honour, and a number here should
always be quoted with it -- the second output line is there for that reason.

## Status

Ported and running.  What has been measured with it, and what it says, is in the
coremark repository's `TOOLCHAINS.md`.
