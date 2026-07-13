#!/usr/bin/env python3
"""Atheris fuzz harness for nostril's nonsense() detector.

Ported from the original OSS-Fuzz-style harness (archive/original-master
mayhem/nonsense_fuzz.py): feed arbitrary unicode strings to nonsense(),
which raises ValueError on inputs it deems non-testable (too short,
non-alphabetic, ...) — that is expected API behavior, not a bug.

nostril has a known upstream defect: string_score() looks up character
n-grams in a defaultdict(NGramData) whose default factory can't be called
with zero args, so any input containing an n-gram absent from the trained
table raises TypeError (recorded as Mayhem defect 3229461, CWE-704,
nostril/nonsense_detector.py:468). Nearly every mutated input trips it,
which makes the raw target exit on almost every deep execution and leaves
Mayhem's coverage collection with an empty (all-crashing) corpus — a 0-edge
run. The harness treats that one known TypeError as handled so fuzzing can
explore the scoring path; any other unexpected exception still crashes and
surfaces as a new finding.
"""
import sys

import atheris

with atheris.instrument_imports():
    from nostril import nonsense


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    n_str = fdp.ConsumeUnicodeNoSurrogates(64)
    try:
        nonsense(n_str)
    except ValueError:
        pass
    except TypeError as e:
        # Known upstream bug (Mayhem defect 3229461): untrained n-gram hits the
        # zero-arg NGramData default factory. Anything else is a new bug.
        if "NGramData.__new__" not in str(e):
            raise


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
