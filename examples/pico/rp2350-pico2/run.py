#!/usr/bin/env python3
"""One Embench benchmark, on the board, with pico-turbo owning the clock.

    run.py --benchmark statemate
    run.py --benchmark matmult-int --khz 150000
    run.py --benchmark statemate --toolchain /path/to/toolchain/usr

The flash path, the read-back comparison and the console reader are the coremark
repository's, imported rather than copied: erasing through the bootrom, writing
with picotool, comparing the flash against the build byte for byte, and holding
the CDC port open before the application starts are the parts of this bench that
were learned the hard way, and two copies of them would drift.

What this adds is the benchmark and the shape of the result.  Embench's own
reference runner drives a GDB session and breaks on start_trigger and stop_trigger
to read a cycle counter out of a register; this bench does not use a debugger
during a run -- a halt costs the round its timing -- so the application prints its
own line and this reads it:

    EMBENCH-PICO: <benchmark> <microseconds> us <pass|FAIL>

Set COREMARK_DIR if the coremark checkout is not a sibling of this repository.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EMBENCH_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def coremark_dir():
    """Where the coremark checkout is, so its debugger path can be imported.  Not
    written down: COREMARK_DIR, then a sibling directory called coremark."""
    for cand in (os.environ.get("COREMARK_DIR"),
                 os.path.join(os.path.dirname(EMBENCH_ROOT), "coremark")):
        if cand and os.path.exists(os.path.join(cand, "tools", "probe.py")):
            return os.path.abspath(cand)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--benchmark", required=True,
                    help="a directory under src/, e.g. statemate")
    ap.add_argument("--board", default="weact_rp2350a")
    ap.add_argument("--khz", type=int, default=520000)
    ap.add_argument("--scale", type=int, default=1,
                    help="GLOBAL_SCALE_FACTOR; Embench sizes a run to about four "
                         "seconds on its reference platform, and this one is faster")
    ap.add_argument("--toolchain", default=None,
                    help="a toolchain prefix, as PICO_TOOLCHAIN_PATH")
    ap.add_argument("--sdk", default=os.environ.get("PICO_SDK_PATH")
                    or os.path.expanduser("~/.pico-sdk"))
    ap.add_argument("--pico-turbo", default=os.environ.get("PICO_TURBO_DIR")
                    or os.path.join(os.path.dirname(EMBENCH_ROOT), "pico-turbo"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--keep", action="store_true", help="do not rebuild")
    args = ap.parse_args()

    cm = coremark_dir()
    if not cm:
        sys.exit("no coremark checkout found: set COREMARK_DIR to one with tools/probe.py")
    # Checked here because both halves of the coremark tooling need it -- the flash
    # path opens the bootrom with pyusb and the console reader does the same to the
    # application's port -- and the failure is a traceback from inside probe.py that
    # reads like a bug in the bench.  The interpreter that ran this file is the one
    # that matters: the reader is started with sys.executable.
    try:
        import usb.core                 # noqa: F401
    except ImportError:
        sys.exit("this interpreter has no pyusb, which the flash path and the "
                 "console reader both need.  The checkout's .venv has it:\n"
                 "  %s/.venv/bin/python3 %s" % (cm, os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(cm, "tools"))
    import probe                      # noqa: E402  (the bench's own tooling)

    args.out = args.out or os.path.join(os.getcwd(),
                                        "embench-%s-%s" % (args.benchmark,
                                                           args.board))
    build = os.path.join(args.out, "build")
    logs = os.path.join(args.out, "logs")
    os.makedirs(logs, exist_ok=True)

    env = dict(os.environ)
    env["PICO_SDK_PATH"] = args.sdk
    if args.toolchain:
        env["PICO_TOOLCHAIN_PATH"] = args.toolchain

    # ---- build ------------------------------------------------------------
    if not args.keep:
        cmd = ["cmake", "-S", HERE, "-B", build,
               "-DPICO_BOARD=%s" % args.board,
               "-DPICO_TURBO_DIR=%s" % args.pico_turbo,
               "-DPICO_TURBO_SYS_CLK_KHZ=%d" % args.khz,
               "-DEMBENCH_BENCHMARK=%s" % args.benchmark,
               "-DGLOBAL_SCALE_FACTOR=%d" % args.scale]
        rc, out = probe.run(cmd, timeout=300,
                            log_path=os.path.join(logs, "cmake.log"), env=env)
        if rc != 0:
            sys.exit("configure failed:\n" + out[-2000:])
        m = re.search(r"^-- pico-turbo: (.*)$", out, re.M)
        if m:
            probe.log("  %s" % m.group(1))
        rc, out2 = probe.run(["cmake", "--build", build, "-j",
                              str(os.cpu_count() or 4)],
                             timeout=600, log_path=os.path.join(logs, "build.log"),
                             env=env)
        if rc != 0:
            sys.exit("build failed:\n" + out2[-2000:])

    elf = os.path.join(build, "embench-pico.elf")
    if not os.path.exists(elf):
        sys.exit("no %s -- did the build run?" % elf)

    # ---- identify, then run ----------------------------------------------
    fake = argparse.Namespace(interface="interface/cmsis-dap.cfg", adapter_speed=1000)
    dbg = probe.Debugger(fake, logs)
    family, out = dbg.identify()
    if family is None:
        sys.exit("the debug probe did not identify a chip")
    probe.log("  chip %s, %s at %d kHz, benchmark %s"
              % (family, args.board, args.khz, args.benchmark))

    # The reader first: the port is held open before the application starts, or the
    # SDK drops everything it writes.  (Same order, same reason, as probe.py.)
    rlog = os.path.join(logs, "console.log")
    reader = subprocess.Popen(
        [sys.executable, os.path.join(cm, "tools", "probe.py"), "--reader",
         rlog, "60", json.dumps(["EMBENCH-PICO:"])])
    time.sleep(2)

    ok, out, rb = dbg.flash_and_run(elf, tag="flash")
    diff = dbg.readback_diff(elf, rb)
    if diff is None or diff[0]:
        reader.terminate()
        sys.exit("the image in the flash is not the image that was built (%s)"
                 % ("no read-back" if not diff else "%d bytes differ" % diff[0]))
    probe.log("    flashed and read back: 0 differing bytes of %d" % diff[1])

    try:
        reader.wait(timeout=180)
    except subprocess.TimeoutExpired:
        reader.terminate()

    text = open(rlog).read() if os.path.exists(rlog) else ""
    state = re.search(r"^PICO-TURBO: (.*)$", text, re.M)
    if state:
        probe.log("    state: %s" % state.group(1))
    emb = re.search(r"^EMBENCH: (.*)$", text, re.M)
    if emb:
        probe.log("    %s" % emb.group(1))

    result = re.search(r"^EMBENCH-PICO: (\S+) (\d+) us (\w+)$", text, re.M)
    if not result:
        addr, sym = dbg.pc(elf)
        probe.log("    NO RESULT -- program counter %s %s"
                  % (hex(addr) if addr else "?", sym or ""))
        return 1

    us = int(result.group(2))
    probe.log("    %s: %d us, %s" % (result.group(1), us, result.group(3)))
    json.dump({"benchmark": result.group(1), "us": us,
               "verified": result.group(3) == "pass",
               "board": args.board, "khz": args.khz, "scale": args.scale,
               "toolchain": args.toolchain,
               "state_line": state.group(1) if state else None},
              open(os.path.join(args.out, "result.json"), "w"), indent=1)
    return 0 if result.group(3) == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
