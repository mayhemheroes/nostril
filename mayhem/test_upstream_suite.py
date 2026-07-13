#!/usr/bin/env python3
"""Pytest form of nostril's upstream test suite (tests/test.py).

Upstream ships its suite as a plain script (tests/test.py) that runs
module-level `assert nonsense(...)` known-answer checks and then evaluates
the detector against the labeled/unlabeled datasets under tests/, printing
the expected error counts in comments/messages ("expect 6 false positives",
"expect 79.50% accuracy", ...). This file runs the SAME checks over the SAME
upstream datasets, turning each documented expectation into a hard pytest
assertion so a neutered nonsense() fails loudly.

One upstream case is skipped: the /usr/share/dict/web2 recall test — that
dictionary file is macOS-specific and does not exist in the Linux image.
"""
import os
import sys

import pytest

THISDIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THISDIR)
TESTS = os.path.join(ROOT, "tests")
sys.path.insert(0, ROOT)

# Alias the imports: pytest would otherwise try to collect nostril's own
# test_labeled/test_unlabeled evaluation helpers as test functions.
from nostril import dataset_from_pickle, nonsense  # noqa: E402
from nostril import test_labeled as run_labeled  # noqa: E402
from nostril import test_unlabeled as run_unlabeled  # noqa: E402

# tests/test.py resolves its dataset paths relative to the CWD.
os.chdir(TESTS)


# ── module-level known-answer asserts from tests/test.py ──────────────────
NONSENSE_STRINGS = [
    "lakdfqtajaklj",
    "AaBbCcDdEeFGgHhIiJjKkLlMmNnOoPpQqRrSsTtU",
    "AcoGQMJyIapivScpnfuXUDMtgTtvAACYdAyABnSLpoABhzZWAAVvAYAAAnqUAFTPo",
    "BCDEFGHIJKLMNOPQRSTUVWXYZ",
    "CDjjiJJTbvFWaSdEtUygGMoGl",
    "CQgHAwIDFQIDAxYCAQIeAQIXgAAKCRC",
    "CgKDQpPUkdBTklaSUHIENPTUJVFRFRQKLStLStLStLStLStLStLStLStLStLSt",
    "aoaoesuouooeueooeuoaeuoeou",
    "iuewrofahgalkfgaufpiupqrjf",
    "ieeoienkjadfakj",
    "lalalaalkjuogaajfajlfal",
]


@pytest.mark.parametrize("s", NONSENSE_STRINGS)
def test_known_nonsense(s):
    assert nonsense(s)


# ── dataset evaluations from tests/test.py, expectations from its output ──
def test_labeled_real_not_real():
    # "expect 6 false positives, 5 false negatives"
    fp_list, fn_list, tested, skipped, _ = run_labeled(
        "labeled-cases/real-not-real.csv", nonsense
    )
    assert len(fp_list) == 6
    assert len(fn_list) == 5
    assert tested == 4625


def test_unlabeled_ludiso():
    # "expect 6 false positives"
    tp, tn, fp, fn, skipped, _ = run_unlabeled("unlabeled-cases/ludiso.txt", nonsense)
    assert fp == 6
    assert fn == 0
    assert tn == 2534


def test_unlabeled_osx_identifiers():
    # "expect 5 false positives"
    tp, tn, fp, fn, skipped, _ = run_unlabeled(
        "unlabeled-cases/select-identifiers-from-osx-frameworks.txt", nonsense
    )
    assert fp == 5
    assert fn == 0
    assert tn == 25936


def test_unlabeled_random_by_hand():
    # "expect 79.50% accuracy"
    tp, tn, fp, fn, skipped, _ = run_unlabeled(
        "unlabeled-cases/random-by-hand.txt", nonsense, sense="invalid"
    )
    accuracy = 100 * (tp + tn) / (tp + tn + fp + fn)
    assert round(accuracy, 2) == 79.50


@pytest.mark.skipif(
    not os.path.exists("/usr/share/dict/web2"),
    reason="upstream recall test needs the macOS dictionary /usr/share/dict/web2",
)
def test_unlabeled_web2_dictionary():
    # "expect 89 false positives (99.96% correct)"
    tp, tn, fp, fn, skipped, _ = run_unlabeled("/usr/share/dict/web2", nonsense)
    assert fp == 89


def test_unlabeled_github_identifiers():
    # "expect 7 false positives"
    tp, tn, fp, fn, skipped, _ = run_unlabeled(
        "../nostril/training/identifier-corpora/random-identifiers-from-github.txt",
        nonsense,
    )
    assert fp == 7
    assert fn == 0
    assert tn == 4013


def test_unlabeled_machine_generated_random():
    # "expect 91.70% accuracy" over the first 1M pickled random strings
    random_strings = dataset_from_pickle("unlabeled-cases/random_set.pklz")
    tp, tn, fp, fn, skipped, _ = run_unlabeled(
        random_strings[:1000000], nonsense, sense="nonsense"
    )
    accuracy = 100 * (tp + tn) / (tp + tn + fp + fn)
    assert round(accuracy, 2) == 91.70
    assert tp == 914882
