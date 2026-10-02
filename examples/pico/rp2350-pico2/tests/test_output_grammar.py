#!/usr/bin/env python3
"""The three console lines parse as `boardsupport.c` actually prints them.

ORACLE: SPEC
SOURCE: examples/pico/rp2350-pico2/boardsupport.c -- the printf() format strings in
        `initialise_board()` and `__wrap_verify_benchmark()`; embench_log.py -- the
        anchored patterns for the two Embench lines; the `PICO-TURBO:` line's
        grammar is coremark's (`<coremark>/tools/probe_parse.py`, `parse_state_line`).
EXPECTED: every documented field extracted exactly, at more than one clock/vreg
          combination; a truncated or partial line never half-matches into a
          confident reading.
"""

import unittest

import common
import embench_log

ORACLE = {
    "type": "SPEC",
    "source": "examples/pico/rp2350-pico2/boardsupport.c printf() format strings; "
              "embench_log.py; <coremark>/tools/probe_parse.py (state line)",
    "expected": "each documented field extracted exactly; malformed lines rejected",
}


class TestStateLine(unittest.TestCase):
    def test_readme_example_fields(self):
        st = embench_log.parse_state(common.fixture("readme-example.log"))
        self.assertEqual(st, {"asked": 520000, "configured": 520000,
                              "measured": 520000, "vreg_sel": 19,
                              "flash_khz": 52000, "clk_peri_khz": 520000,
                              "usb_ok": True})

    def test_real_off_by_one_reading_is_kept(self):
        # Real line: the hardware counter reads 520001 kHz for a 520000 request.
        st = embench_log.parse_state(common.fixture("state-520001-measured.log"))
        self.assertEqual(st["asked"], 520000)
        self.assertEqual(st["measured"], 520001)

    def test_real_stock_clock_fields(self):
        st = embench_log.parse_state(common.fixture("state-150000-stock.log"))
        self.assertEqual(
            (st["asked"], st["vreg_sel"], st["flash_khz"], st["clk_peri_khz"]),
            (150000, 11, 37500, 150000))

    def test_usb_wrong_is_reported_not_ok(self):
        # Format-derived: boardsupport.c prints "WRONG" when clk_usb is not 48 MHz.
        st = embench_log.parse_state(
            "PICO-TURBO: 520000 kHz asked, 520000 kHz configured, "
            "520000 kHz measured, vreg sel 19, flash 52000 kHz, "
            "clk_peri 520000 kHz, usb WRONG\n")
        self.assertIs(st["usb_ok"], False)

    def test_without_the_line_is_none(self):
        self.assertIsNone(embench_log.parse_state("nothing here\n"))

    def test_truncated_line_has_no_usb_and_no_clk_peri(self):
        # coremark's grammar keeps the older line that ends at `flash`, so a reader
        # that dropped the tail is not None -- but the missing fields must read as
        # absent, never as "ok".
        st = embench_log.parse_state(
            "PICO-TURBO: 520000 kHz asked, 520000 kHz configured, "
            "520000 kHz measured, vreg sel 19, flash 52000 kHz\n")
        self.assertIsNotNone(st)
        self.assertIsNone(st["usb_ok"])
        self.assertIsNone(st["clk_peri_khz"])

    def test_format_state_reproduces_the_line_body(self):
        # run.py logs this text and writes it to result.json, so it must be the
        # body boardsupport.c printed, minus the "PICO-TURBO: " prefix.
        text = common.fixture("readme-example.log")
        line = next(l for l in text.splitlines() if l.startswith("PICO-TURBO: "))
        self.assertEqual(embench_log.format_state(embench_log.parse_state(text)),
                         line[len("PICO-TURBO: "):])


class TestEmbenchLines(unittest.TestCase):
    def test_readme_scale_line(self):
        sc = embench_log.parse_scale(common.fixture("readme-example.log"))
        self.assertEqual((sc.bench, sc.scale, sc.heat), ("statemate", 100, 1))

    def test_readme_result_line(self):
        r = embench_log.parse_result(common.fixture("readme-example.log"))
        self.assertEqual((r.bench, r.us, r.verdict), ("statemate", 702013, "pass"))

    def test_scale_default_shape_from_printf(self):
        # Format-derived: sconstruct.py defaults warmup_heat to 1 and gsf to 1, and
        # CMakeLists.txt repeats both defaults.
        sc = embench_log.parse_scale("EMBENCH: statemate scale 1 heat 1\n")
        self.assertEqual((sc.scale, sc.heat), (1, 1))

    def test_fail_verdict_is_parsed_as_fail(self):
        r = embench_log.parse_result(common.fixture("fail-verdict.log"))
        self.assertEqual(r.verdict, "FAIL")

    def test_the_other_lines_do_not_match(self):
        self.assertIsNone(embench_log.parse_result(
            "EMBENCH: statemate scale 1 heat 1\n"))
        self.assertIsNone(embench_log.parse_scale(
            "EMBENCH-PICO: statemate 1 us pass\n"))

    def test_fragments_do_not_match(self):
        # The console reader can capture a partial line; a fragment must not parse.
        self.assertIsNone(embench_log.parse_result(
            "ENCH-PICO: statemate 702013 us pass\n"))
        self.assertIsNone(embench_log.parse_scale(
            "BENCH: statemate scale 100 heat 1\n"))

    def test_preamble_and_prose_do_not_break_parsing(self):
        text = ("[reader] no application appeared\n[reader] done\n"
                + common.fixture("readme-example.log") + "tail\n")
        log = embench_log.parse_log(text)
        self.assertEqual(log.result.bench, "statemate")
        self.assertEqual(log.scale.scale, 100)
        self.assertTrue(log.state["usb_ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
