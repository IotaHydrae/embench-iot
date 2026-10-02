#!/usr/bin/env python3
"""The port's console contract: CoreMark's state line plus Embench's two lines.

The `PICO-TURBO:` state line is the CoreMark port's, and its one canonical parser
lives in the coremark repository (`tools/probe_parse.py`, `parse_state_line`).
This module imports that parser rather than copying it -- the grammar and the
"clock landed where asked" rule are coremark's, and a second copy here would
drift from it.  What is added here is only what this port prints itself (see
boardsupport.c):

    EMBENCH: <benchmark> scale <n> heat <h>
    EMBENCH-PICO: <benchmark> <microseconds> us <pass|FAIL>

Facts only: the parse_* functions extract fields and report which lines were seen.
Whether a run is *valid* is a decision -- run.py makes it in outcome(), and
tests/test_run_validity.py makes it against explicit oracles.

The state line's "measured" field is the chip's own hardware frequency-counter
reading, not a read-back of the configuration; that is what makes a result
attributable to a configuration.
"""

import os
import re
import sys
from collections import namedtuple

Scale = namedtuple("Scale", "bench scale heat")
Result = namedtuple("Result", "bench us verdict")
Log = namedtuple("Log", "state scale result")

# Anchored per line, and tolerant only of trailing blanks.  A line the console
# reader truncated (it can drop bytes when the CDC port is grabbed too late) must
# not half-match and produce a confident partial reading.
SCALE_RE = re.compile(
    r"^EMBENCH: (?P<bench>\S+) scale (?P<scale>\d+) heat (?P<heat>\d+)[ \t\r]*$",
    re.M)
RESULT_RE = re.compile(
    r"^EMBENCH-PICO: (?P<bench>\S+) (?P<us>\d+) us (?P<verdict>\w+)[ \t\r]*$",
    re.M)


class CoremarkMissing(RuntimeError):
    """There is no coremark checkout to import the shared parser from."""


def coremark_dir():
    """Where the coremark checkout is, or None.

    Not written down: `COREMARK_DIR`, then a sibling directory called `coremark`.
    The sibling layout is what the workspace uses and what run.py documents.  Both
    files must be there: `probe.py` is the flash path and console reader, and
    `probe_parse.py` is the shared state-line grammar.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    embench_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    for cand in (os.environ.get("COREMARK_DIR"),
                 os.path.join(os.path.dirname(embench_root), "coremark")):
        if not cand:
            continue
        tools = os.path.join(cand, "tools")
        if all(os.path.exists(os.path.join(tools, f))
               for f in ("probe.py", "probe_parse.py")):
            return os.path.abspath(cand)
    return None


_PROBE_PARSE = None


def load_probe_parse():
    """coremark's `probe_parse` module, imported once; raises if it is absent.

    Reuse is deliberate: `parse_state_line` and `clock_landed` are coremark's
    rules.  If coremark is not checked out this is an environment problem, not a
    test failure -- callers turn `CoremarkMissing` into ENVIRONMENT_ERROR.
    """
    global _PROBE_PARSE
    if _PROBE_PARSE is None:
        cm = coremark_dir()
        if cm is None:
            raise CoremarkMissing(
                "no coremark checkout with tools/probe_parse.py found: set "
                "COREMARK_DIR, or check out coremark as a sibling of this repository")
        tools = os.path.join(cm, "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        import probe_parse
        _PROBE_PARSE = probe_parse
    return _PROBE_PARSE


def parse_state(text):
    """The `PICO-TURBO:` state line as a dict, or None (coremark's parser)."""
    return load_probe_parse().parse_state_line(text)


def clock_landed(asked, measured):
    """Did the hardware-counter clock land where it was asked?  (coremark's rule)"""
    return load_probe_parse().clock_landed(asked, measured)


def format_state(state):
    """The state line's body as text, for logs and for `result.json`.

    Reproduces boardsupport.c's wording.  A field the captured line did not carry
    (coremark's parser leaves `clk_peri_khz`/`usb_ok` as None on an older or
    truncated line) prints as `?`, so a missing reading is never shown as a good
    one.
    """
    if state is None:
        return None
    clk_peri = ("%d kHz" % state["clk_peri_khz"]
                if state["clk_peri_khz"] is not None else "?")
    usb = "ok" if state["usb_ok"] else ("WRONG" if state["usb_ok"] is False else "?")
    return ("%d kHz asked, %d kHz configured, %d kHz measured, vreg sel %d, "
            "flash %d kHz, clk_peri %s, usb %s"
            % (state["asked"], state["configured"], state["measured"],
               state["vreg_sel"], state["flash_khz"], clk_peri, usb))


def parse_scale(text):
    """The first EMBENCH scale line, or None."""
    m = SCALE_RE.search(text)
    if not m:
        return None
    return Scale(bench=m.group("bench"), scale=int(m.group("scale")),
                 heat=int(m.group("heat")))


def parse_result(text):
    """The first EMBENCH-PICO result line, or None."""
    m = RESULT_RE.search(text)
    if not m:
        return None
    return Result(bench=m.group("bench"), us=int(m.group("us")),
                  verdict=m.group("verdict"))


def parse_log(text):
    """Everything the host needs from one console log."""
    return Log(state=parse_state(text), scale=parse_scale(text),
               result=parse_result(text))
