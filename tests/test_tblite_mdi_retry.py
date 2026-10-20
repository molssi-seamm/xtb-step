# -*- coding: utf-8 -*-

"""The tblite MDI engine retries an SCF that does not converge, and gives up with
None (NaN to the driver) rather than ending the engine (science, 2026-10-20: one
Li+ dimer point stopped whole Dimer Builder jobs)."""

import importlib.util
from pathlib import Path

import pytest

ENGINE = Path(__file__).parents[1] / "xtb_step" / "data" / "tblite_mdi.py"


@pytest.fixture(scope="module")
def engine():
    spec = importlib.util.spec_from_file_location("tblite_mdi", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCalc:
    """Fails the first ``n_fail`` SCFs; records the settings of each attempt."""

    def __init__(self, n_fail):
        self.n_fail = n_fail
        self.settings = {"max-iter": 250, "mixer-damping": 0.4, "guess": 0}
        self.attempts = []

    def set(self, name, value):
        self.settings[name] = value

    def singlepoint(self, res=None, copy=True):
        self.attempts.append((res is not None, dict(self.settings)))
        if len(self.attempts) <= self.n_fail:
            raise RuntimeError("SCF not converged in 250 cycles")
        return {"energy": -1.0}


def test_converged_first_time(engine):
    calc = FakeCalc(0)
    assert engine.singlepoint(calc, "previous") == {"energy": -1.0}
    assert len(calc.attempts) == 1
    assert calc.attempts[0][0] is True  # warm start from the previous result


def test_retried_from_a_fresh_start(engine):
    calc = FakeCalc(2)
    assert engine.singlepoint(calc, "previous") == {"energy": -1.0}
    # warm start, then fresh starts with the retry settings
    assert [warm for warm, _ in calc.attempts] == [True, False, False]
    assert calc.attempts[2][1] == {"max-iter": 1000, "mixer-damping": 0.1, "guess": 0}
    # the defaults are restored for the next geometry
    assert calc.settings == {"max-iter": 250, "mixer-damping": 0.4, "guess": 0}


def test_gives_up_with_none(engine):
    calc = FakeCalc(100)
    assert engine.singlepoint(calc, None) is None
    assert len(calc.attempts) == 1 + len(engine.RETRIES)
    assert calc.settings == {"max-iter": 250, "mixer-damping": 0.4, "guess": 0}
