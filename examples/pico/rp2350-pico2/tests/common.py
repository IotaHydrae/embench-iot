"""Shared helpers for the port's offline tests.

No board, no debugger, no network.  The only external requirement is the coremark
checkout, because the `PICO-TURBO:` state-line grammar and the "clock landed where
asked" rule are imported from there rather than copied (`embench_log.py`); when it
is missing that is an environment problem, not a test failure.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.dirname(HERE)

# The tests import the port's own modules (embench_log, run) from the directory
# above, so that they test the code that actually runs.
if PORT not in sys.path:
    sys.path.insert(0, PORT)

FIXTURES = os.path.join(HERE, "fixtures")


class EnvironmentMissing(Exception):
    """A shared dependency is absent.  Workspace exit code 3, never FAIL."""


def fixture(name):
    """The text of one file under `fixtures/`; provenance is in tests/README.md."""
    with open(os.path.join(FIXTURES, name)) as fh:
        return fh.read()
