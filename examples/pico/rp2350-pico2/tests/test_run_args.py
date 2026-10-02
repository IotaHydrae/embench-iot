#!/usr/bin/env python3
"""`run.py` takes `--benchmark` and `--scale`, and passes them into the build.

ORACLE: SPEC
SOURCE: examples/pico/rp2350-pico2/run.py (`arg_parser`, `configure_cmd`) and
        CMakeLists.txt, which reads `EMBENCH_BENCHMARK`, `GLOBAL_SCALE_FACTOR`,
        `PICO_TURBO_SYS_CLK_KHZ` and `PICO_BOARD`; sconstruct.py declares the same
        defaults for the scale factor (`gsf` 1, `warmup_heat` 1).
EXPECTED: `--benchmark` is required (argparse exits 2 = INVALID_USAGE); `--scale`
          defaults to 1 and reaches `-DGLOBAL_SCALE_FACTOR`; the benchmark, clock
          and board reach their own `-D` flags.
"""

import contextlib
import io
import unittest

import common
import run

ORACLE = {
    "type": "SPEC",
    "source": "examples/pico/rp2350-pico2/run.py arg_parser/configure_cmd; "
              "examples/pico/rp2350-pico2/CMakeLists.txt; sconstruct.py defaults",
    "expected": "--benchmark required; --scale default 1 and reaches the cmake build",
}


def parse(argv):
    return run.arg_parser().parse_args(argv)


def configure(argv):
    """`configure_cmd` for these arguments, with --pico-turbo pinned so the test
    does not depend on the host's directory layout."""
    args = parse(["--benchmark", argv[0]] + argv[1:])
    args.pico_turbo = "/pico-turbo"
    return run.configure_cmd(args, "/src", "/build")


class TestArguments(unittest.TestCase):
    def test_benchmark_is_required(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                parse([])
        self.assertEqual(ctx.exception.code, 2)      # INVALID_USAGE

    def test_defaults(self):
        args = parse(["--benchmark", "statemate"])
        self.assertEqual(args.scale, 1)
        self.assertEqual(args.khz, 520000)
        self.assertEqual(args.board, "weact_rp2350a")

    def test_scale_is_taken(self):
        self.assertEqual(parse(["--benchmark", "statemate", "--scale", "100"]).scale,
                         100)


class TestConfigureCommand(unittest.TestCase):
    def test_scale_reaches_cmake(self):
        self.assertIn("-DGLOBAL_SCALE_FACTOR=100",
                      configure(["statemate", "--scale", "100"]))

    def test_benchmark_reaches_cmake(self):
        self.assertIn("-DEMBENCH_BENCHMARK=matmult-int", configure(["matmult-int"]))

    def test_clock_and_board_reach_cmake(self):
        cmd = configure(["statemate", "--khz", "150000", "--board", "pico2"])
        self.assertIn("-DPICO_TURBO_SYS_CLK_KHZ=150000", cmd)
        self.assertIn("-DPICO_BOARD=pico2", cmd)

    def test_pico_turbo_dir_reaches_cmake(self):
        self.assertIn("-DPICO_TURBO_DIR=/pico-turbo", configure(["statemate"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
