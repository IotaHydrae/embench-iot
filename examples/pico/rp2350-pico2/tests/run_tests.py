#!/usr/bin/env python3
"""Run the port's offline tests; report one workspace exit code.

    0 PASS   1 FAIL   2 INVALID_USAGE   3 ENVIRONMENT_ERROR   4 TIMEOUT   5 INCONCLUSIVE

The tests need no board, no debugger and no network.  They do need the coremark
checkout, because the state-line grammar and the "clock landed where asked" rule
are imported from it; when it is missing the module reports ENVIRONMENT_ERROR
rather than FAIL.

    python3 tests/run_tests.py
    python3 tests/run_tests.py --json
    python3 tests/run_tests.py --quiet

`python3 -m unittest discover -s tests` runs the cases too, but only this runner
prints each module's oracle and tells ENVIRONMENT_ERROR (3) apart from FAIL (1).
"""

import argparse
import importlib
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402  (also puts the port directory on sys.path)

VERSION = "1.0"
MODULES = ["test_output_grammar", "test_run_validity", "test_run_args"]

PASS, FAIL, INVALID_USAGE, ENVIRONMENT_ERROR, TIMEOUT, INCONCLUSIVE = range(6)
NAMES = {PASS: "PASS", FAIL: "FAIL", INVALID_USAGE: "INVALID_USAGE",
         ENVIRONMENT_ERROR: "ENVIRONMENT_ERROR", TIMEOUT: "TIMEOUT",
         INCONCLUSIVE: "INCONCLUSIVE"}


class CaseResult(unittest.TestResult):
    """Remembers exception types so `EnvironmentMissing` can be told apart from a
    real failure instead of being sniffed out of a traceback."""

    def __init__(self):
        super().__init__()
        self.exc_types = []

    def addError(self, test, err):
        self.exc_types.append(err[0])
        super().addError(test, err)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def classify(result):
    if result.errors:
        return ENVIRONMENT_ERROR if common.EnvironmentMissing in result.exc_types \
            else FAIL
    if result.failures:
        return FAIL
    if result.skipped:
        return INCONCLUSIVE
    return PASS


def run_module(name):
    module = importlib.import_module(name)
    oracle = getattr(module, "ORACLE",
                     {"type": "NONE", "source": "?", "expected": "?"})
    require = getattr(module, "require_environment", None)
    if require is not None:
        try:
            require()
        except common.EnvironmentMissing as exc:
            return {"test": name, "oracle": oracle, "status": ENVIRONMENT_ERROR,
                    "note": str(exc), "cases": []}
    cases = []
    for case in flatten(unittest.TestLoader().loadTestsFromModule(module)):
        result = CaseResult()
        case(result)
        cases.append({"case": case.id(), "status": classify(result)})
    statuses = [c["status"] for c in cases]
    status = PASS
    if FAIL in statuses:
        status = FAIL
    elif ENVIRONMENT_ERROR in statuses:
        status = ENVIRONMENT_ERROR
    elif INCONCLUSIVE in statuses:
        status = INCONCLUSIVE
    return {"test": name, "oracle": oracle, "status": status, "note": None,
            "cases": cases}


def report_text(entry, quiet):
    out = []
    if not quiet:
        out += ["[TEST] %s" % entry["test"],
                "[ORACLE] %s" % entry["oracle"]["type"],
                "[SOURCE] %s" % entry["oracle"]["source"],
                "[EXPECTED] %s" % entry["oracle"]["expected"]]
    if entry["note"]:
        out.append("  [%s] %s" % (NAMES[entry["status"]], entry["note"]))
    for case in entry["cases"]:
        if quiet and case["status"] == PASS:
            continue
        out.append("  [%s] %s" % (NAMES[case["status"]], case["case"]))
    out.append("[RESULT] %s" % NAMES[entry["status"]])
    return out


def aggregate(statuses):
    if FAIL in statuses:
        return FAIL
    if ENVIRONMENT_ERROR in statuses:
        return ENVIRONMENT_ERROR
    if INCONCLUSIVE in statuses:
        return INCONCLUSIVE
    return PASS


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    ap.add_argument("--quiet", action="store_true",
                    help="print only non-PASS cases and the results")
    ap.add_argument("--version", action="version", version="run_tests " + VERSION)
    args = ap.parse_args(argv)

    entries = [run_module(name) for name in MODULES]
    status = aggregate([entry["status"] for entry in entries])
    if args.json:
        named = []
        for entry in entries:
            named.append(dict(entry, status=NAMES[entry["status"]],
                              cases=[dict(c, status=NAMES[c["status"]])
                                     for c in entry["cases"]]))
        print(json.dumps({"runner": "embench-pico/tests", "version": VERSION,
                          "status": NAMES[status], "tests": named}, indent=1))
    else:
        for entry in entries:
            print("\n".join(report_text(entry, args.quiet)))
        print("\n[OVERALL] %s" % NAMES[status])
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
