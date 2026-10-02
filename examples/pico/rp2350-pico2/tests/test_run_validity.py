#!/usr/bin/env python3
"""A finished run has to be attributable: the clock landed, and the lines pair.

ORACLE: SPEC for the clock rule, INVARIANT for the pairing.
SOURCE: <coremark>/tools/probe_parse.py `clock_landed` and <coremark>/AGENTS.md
        hardware rule 1 -- the state line's hardware-counter measured clock must be
        the clock that was asked for (within one part in a thousand, or 1 kHz,
        whichever is larger); examples/pico/rp2350-pico2/run.py `outcome` and this
        repository's AGENTS.md -- a result line is also the line that says the run
        finished, so a state line with no result means the run started and stopped
        inside itself.
EXPECTED: real off-by-one readings count as landed; a line clamped back to the
          stock clock does not; `pass` exits 0, `FAIL` and a missing result exit 1.
"""

import unittest

import common
import embench_log
import run

ORACLE = {
    "type": "SPEC (clock) / INVARIANT (pairing)",
    "source": "<coremark>/tools/probe_parse.py clock_landed + <coremark>/AGENTS.md "
              "rule 1; run.py outcome + embench-iot/AGENTS.md",
    "expected": "measured clock lands where asked; one result line per state line",
}


class TestClockLanded(unittest.TestCase):
    def test_readme_example_landed(self):
        st = embench_log.parse_state(common.fixture("readme-example.log"))
        self.assertTrue(embench_log.clock_landed(st["asked"], st["measured"]))

    def test_real_off_by_one_landed(self):
        # 520001 measured for 520000 asked is a real reading, not a mismatch.
        st = embench_log.parse_state(common.fixture("state-520001-measured.log"))
        self.assertTrue(embench_log.clock_landed(st["asked"], st["measured"]))

    def test_clamped_to_stock_not_landed(self):
        # Reconstructed from the recorded observation in
        # <pico-turbo>/boards/weact_rp2350a.cmake: an out-of-envelope voltage
        # request at 520 MHz was clamped and the application ran at 150 MHz, while
        # the run itself completed.
        st = embench_log.parse_state(common.fixture("clamped-to-stock.log"))
        self.assertFalse(embench_log.clock_landed(st["asked"], st["measured"]))


class TestOutcome(unittest.TestCase):
    def test_readme_example_passes_with_zero(self):
        log = embench_log.parse_log(common.fixture("readme-example.log"))
        self.assertEqual(run.outcome(log), ("passed", 0))

    def test_fail_verdict_is_failed_with_one(self):
        log = embench_log.parse_log(common.fixture("fail-verdict.log"))
        self.assertEqual(run.outcome(log), ("failed", 1))

    def test_state_without_result_is_stuck(self):
        log = embench_log.parse_log(common.fixture("stuck-no-result.log"))
        self.assertEqual(run.outcome(log), ("stuck", 1))

    def test_nothing_at_all_is_no_output(self):
        log = embench_log.parse_log("")
        self.assertEqual(run.outcome(log), ("no-output", 1))


def require_environment():
    """The clock rule and the state grammar are coremark's; they must be there."""
    if embench_log.coremark_dir() is None:
        raise common.EnvironmentMissing(
            "no coremark checkout with tools/probe_parse.py and tools/probe.py "
            "(set COREMARK_DIR, or check out coremark as a sibling)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
