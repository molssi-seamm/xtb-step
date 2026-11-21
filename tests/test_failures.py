# -*- coding: utf-8 -*-

"""The xTB step must fail loudly when xtb fails (Thermochemistry 5921, 2026-11-21:
257 failed optimisations ended "finished" with no exceptions counted).

* Unit tests of Energy._check_xtb_run.
* Run-path tests (seamm_exec.testing): a flowchart with a fake xtb that exits with a
  Fortran runtime error, one that writes no xtbout.json, and one that succeeds.
"""

import json
from pathlib import Path
import textwrap

import pytest

from xtb_step.energy import Energy

SOURCE = Path(__file__).resolve().parents[1]

SPEC = """\
title: xTB failure test
steps:
- Water: {}
- xTB:
    steps:
    - Energy
"""

GOOD_JSON = {
    "total energy": -5.070544440612,
    "electronic energy": -5.104925358219,
    "HOMO-LUMO gap / eV": 14.2,
    "dipole / a.u.": [0.0, 0.0, 0.85],
}


# ---------------------------------------------------------------- unit tests
def check(tmp_path, result, data, write_json=True):
    if write_json:
        (tmp_path / "xtbout.json").write_text(json.dumps(GOOD_JSON))
    return Energy._check_xtb_run(None, tmp_path, result, data)


def test_success_passes(tmp_path):
    check(
        tmp_path, {"returncode": 0, "stdout": "", "stderr": ""}, {"total_energy": -5.07}
    )


def test_nonzero_returncode_raises(tmp_path):
    err = (
        "\n".join(f"line {i}" for i in range(40))
        + "\nMissing comma between descriptors"
    )
    with pytest.raises(RuntimeError) as exc:
        check(
            tmp_path,
            {"returncode": 2, "stdout": "", "stderr": err},
            {"total_energy": -5.0},
        )
    msg = str(exc.value)
    assert "return code 2" in msg
    assert str(tmp_path) in msg
    assert "Missing comma between descriptors" in msg
    assert "line 19" not in msg  # only the last 20 lines are quoted


def test_missing_json_raises(tmp_path):
    with pytest.raises(RuntimeError, match="no xtbout.json"):
        check(
            tmp_path,
            {"returncode": 0, "stdout": "x", "stderr": ""},
            {},
            write_json=False,
        )


def test_no_energy_raises(tmp_path):
    with pytest.raises(RuntimeError, match="no total energy"):
        check(tmp_path, {"returncode": 0, "stdout": "", "stderr": ""}, {})


def test_no_result_raises(tmp_path):
    with pytest.raises(RuntimeError, match="could not be run"):
        check(tmp_path, None, {}, write_json=False)


# ---------------------------------------------------------- run-path tests
FAKE = """\
#!{python}
import json, sys
from pathlib import Path
mode = {mode!r}
print(" * xtb version 6.8.0 (fake)")
if mode == "crash":
    sys.stderr.write("At line 624 of file src/optimizer.f90\\n"
                     "Fortran runtime error: Missing comma between descriptors\\n")
    sys.exit(2)
if mode == "good":
    Path("xtbout.json").write_text(json.dumps({good}))
print("normal termination of xtb")
"""


def fake_xtb(tmp_path, mode):
    import sys

    path = tmp_path / "bin" / "xtb"
    path.parent.mkdir(parents=True)
    path.write_text(
        textwrap.dedent(FAKE).format(python=sys.executable, mode=mode, good=GOOD_JSON)
    )
    path.chmod(0o755)
    return str(path)


def run(tmp_path, mode):
    from seamm_exec.testing import run_spec

    code = fake_xtb(tmp_path, mode)
    return run_spec(tmp_path, SPEC, inis={"xtb": {"code": code}}, source=SOURCE)


def test_run_path_good(tmp_path):
    pytest.importorskip("seamm_exec.testing")
    job = run(tmp_path, "good")
    assert "-5.07054" in (job / "job.out").read_text()


@pytest.mark.parametrize(
    "mode, expected",
    [("crash", "return code 2"), ("nojson", "no xtbout.json")],
)
def test_run_path_failure_is_an_error(tmp_path, mode, expected):
    pytest.importorskip("seamm_exec.testing")
    with pytest.raises(AssertionError) as exc:
        run(tmp_path, mode)
    text = str(exc.value)
    assert "The xTB calculation in" in text
    assert expected in text
    if mode == "crash":
        assert "Missing comma between descriptors" in text
