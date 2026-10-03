# AGENTS.md — embench-iot, the part this workspace owns

## Skills（本仓遵守）

本仓的一切工作遵循工作区 `../AGENTS.md` 约定的四份 skill。**摘要随仓携带**（离线可读），
完整版在工作区 `skills/`。

| skill | 本仓副本 | 一句话 |
| --- | --- | --- |
| Repository Exploration | [`skills/developer-repository-exprolation/Summary.md`](skills/developer-repository-exprolation/Summary.md) | 先理解再修改；证据优先于直觉 |
| Knowledge | [`skills/developer-knowledge/Summary.md`](skills/developer-knowledge/Summary.md) | 首屏结论、事实分级、信息预算、漂移检查 |
| Testing | [`skills/developer-testing/Summary.md`](skills/developer-testing/Summary.md) | tests/tools 分层、oracle 声明、退出码、N 次测量 |
| Code Quality | [`skills/developer-code-quality/Summary.md`](skills/developer-code-quality/Summary.md) | **能跑 ≠ 完成**；可读性有硬标准 |

### 动手前的四行闸门（**强制**）

改任何代码或配置**之前**先写出这四行 ✓。**第 1 行或第 4 行写不出来就停手** ✗ —— 那是在猜 ✗。

```text
已验证：<确认了什么，凭据是什么：代码/实测/构建日志>
仍未知：<还没确认的；不许用推测填空>
最小改动：<只改一处，为什么是这一处>
生效验证：<如何证明改动真的生效：探针 / grep 生成物 / 构建日志里的编译行>
```

**先确认仪器，再相信读数** ✓ —— 宏没被注入、文件没被编译、配置被 defconfig 覆盖，
这三件事的症状都是"结果莫名其妙" ✗。


> Upstream Embench is read-only here.  Everything this workspace changes lives in
> `examples/pico/rp2350-pico2/`; the port's knowledge index is
> [`examples/pico/rp2350-pico2/docs/README.md`](examples/pico/rp2350-pico2/docs/README.md).

Workspace-wide knowledge-base and testing conventions are in
[`../AGENTS.md`](../AGENTS.md).  This file only records what is specific to this
repository: the boundary, and the rules a result from this port has to obey.

## TL;DR

- **Do not modify upstream Embench.**  `src/`, `support/`, `doc/`, `README.md`,
  `benchmark_speed.py`, `benchmark_size.py`, `ChangeLog`, `sconstruct.py`, `pylib/`
  are the upstream project and stay byte for byte as imported.
- **Never touch SWD while a timed region is running.**  A halt costs that round its
  timing while leaving the checksum correct — a validated result with a wrong number.
- **The RP2350 DWT cycle counter does not count.**  Time with the SDK's `time_us_32()`.
- **Reuse the coremark repository's flash path and console reader**; do not write a
  second one, and do not change coremark to make reuse convenient.
- **A number is quoted together with `--scale`, the benchmark, the board, the clock
  and the compiler**; `--scale 1` and `--scale 100` are different measurements.
- English only in this repository; no commit, push, absolute host paths, internal
  IPs, credentials or proxy settings, and no board serial numbers.

## Upstream versus ours

| Path | Owner | May this workspace change it? |
| --- | --- | --- |
| `src/`, `support/`, `doc/` | upstream Embench-IoT | **no** |
| `README.md`, `ChangeLog`, `sconstruct.py` | upstream | **no** |
| `benchmark_speed.py`, `benchmark_size.py`, `pylib/` | upstream | **no** |
| `examples/arm/`, `examples/native/`, `examples/riscv32/`, … | upstream reference ports | **no** |
| `examples/pico/rp2350-pico2/` | this workspace | yes |
| `examples/pico/rp2350-pico2/docs/`, `tests/` | this workspace | yes |
| `AGENTS.md` (this file) | this workspace | yes |

If a task appears to need an upstream change, stop and report it instead.  The same
applies to the sibling repositories: to change behavior in `coremark` or
`pico-turbo`, raise it there — the fix does not belong in a copy carried here.

## Iron rules

### 1. Nothing touches SWD during a run

The reference Embench flow runs the target under GDB and breaks on `start_trigger`
and `stop_trigger` (`pylib/run_stm32f4-discovery.py`, documented in `doc/README.md`).
**This port rejects that flow.**  A debugger halt costs the round its timing while
the benchmark's own CRC stays correct: a result that validated itself and is still
wrong, which is the worst class of false signal.  The application prints its result
and the host only reads the console.

SWD is still used *around* the run — `run.py` identifies the chip, blanks the flash
and reads the image back through the debugger — but never between `start_trigger()`
and `stop_trigger()`.  The flash write and the reboot go through the chip's own
bootrom with `picotool` (see `<coremark>/AGENTS.md`, rule 8b).

A post-mortem read is allowed: when there is no result line, `run.py` reads the
program counter to say *where* the run stopped.  That is after the timed region and
is diagnostic, not measurement.

### 2. DWT does not count on this chip — use `time_us_32()`

**Measured:** with the reference enable sequence (`DEMCR.TRCENA`, then
`DWT_CTRL.CYCCNTENA`), an eleven-second timed region at 150 MHz read **168** cycles
where about 1.68e9 were expected.  **Hypothesis, not verified:** the debug and trace
blocks sit in a power domain that a debugger has to bring up.  Do not present that
cause as fact, and do not solve it by attaching a debugger — rule 1 forbids it.

The port times with the SDK's `time_us_32()`, the same timer the coremark port uses.
The 0.05% agreement with the host clock (`<coremark>/RANKINGS.md`, section 8) was
measured on **that** port; this port reuses the same timer and has **not** been
re-checked independently.  A cycle count next to an instruction count is therefore
not available here, which is a real limitation of this bench.

### 3. Reuse coremark's flash path and console reader

`run.py` imports `<coremark>/tools/probe.py`: `Debugger.flash_and_run()` blanks the
flash through the debugger, writes with picotool through the bootrom, reads back over
SWD, and reboots through the bootrom; `--reader` is the console reader that holds the
CDC port open before the application starts.  Two copies of that would drift, and the
copy that drifted would be the one that lost a result.

To reuse more of it (for example a shared log parser), **propose the change in
`coremark`** and use it from there.  Do not patch coremark from here and do not fork
its functions into this repository.

### 4. A number is not a number without its configuration

Quote every measurement with:

- `--scale` (Embench's `GLOBAL_SCALE_FACTOR`) — the application prints it on the
  `EMBENCH:` line for exactly this reason;
- the benchmark name;
- the board (`--board`);
- the clock (`--khz`) **and** the clock the chip measured itself at, from the
  `PICO-TURBO:` state line;
- the compiler (toolchain version), as `<coremark>/TOOLCHAINS.md` does.

`statemate --scale 1` finishes in about 7 ms at 520 MHz, so a time without its scale
factor cannot be compared with anything.  A time from a compiler that is not named
is not comparable either (the compiler is worth −5.3% … +27.5% between workloads).

### 5. Only verified conclusions; guesses are marked

Facts from source, a reproducible experiment or a real recorded log may be stated
directly.  Anything inferred is written as a hypothesis with "not verified".  Do not
turn one observed value into a threshold, tolerance or golden fixture — see
[`../AGENTS.md`](../AGENTS.md) for the oracle rules the tests follow.

### 6. Drift check on every knowledge update

Runtime facts belong to the code.  When a document changes, re-check its claims
against `boardsupport.c`, `run.py` and `CMakeLists.txt`: the three output-line
formats, the `--scale` semantics, `time_us_32()`, and the flash path.  Correct the
document from the code; keep historic measurements but label the configuration they
came from; obsolete *conclusions* are what gets deleted.  Stale comments in code may
be corrected (comments only, never behavior).  Report the drift list with the change.

## Division of labour

| Repository | Owns |
| --- | --- |
| `coremark` | the measurement bench and the chip/board limits; the authoritative tables (`RANKINGS.md`, `TOOLCHAINS.md`) and the hardware discipline (`AGENTS.md`) |
| `pico-turbo` | clock, core voltage and flash divider; `boards/<board>.cmake` and their measurements |
| `embench-iot` (here) | the Pico port and its output grammar; the nineteen-workload answer CoreMark cannot give |
| `dhrystone` | its own port and score |

The port's results are recorded in `<coremark>/TOOLCHAINS.md` — that is the canonical
place; this repository keeps the port and links to them rather than copying them.

## Verification (offline first)

```sh
python3 examples/pico/rp2350-pico2/tests/run_tests.py
```

runs every board-free test (output grammar, run validity, `run.py` argument
handling).  A missing coremark checkout is `ENVIRONMENT_ERROR` (exit 3), not a
failure.  On hardware, follow the discipline above and the coremark hardware rules;
`run.py` already starts the console reader before the write and compares the flash
read-back with the build.

## No commits without instruction

Do not `git commit` or `git push` unless explicitly told to.  Commit identity and
message conventions, if a commit is ever requested, follow the workspace root
[`../AGENTS.md`](../AGENTS.md).

## 驱动工具的方式（与工作区规范同源）

- **不许盲目 `sleep`，不许 blanket 超时** ✓ —— 用**轮询就绪**（0.2 s 间隔）+ **秒级超时** ✓。
  硬件测试必须**显式定义就绪检测**，不要依赖"设备恰好已经跑着" ✓。
- 反例：`sleep 22` + `timeout 300` ⇒ 明明 0.4 s 就有结论的操作拖到几分钟 ✗。
- 正解：`usb.core.find` 轮询 ✓、控制请求 0.5 s 超时 ✓、shell 命令 `timeout 10` ✓。
