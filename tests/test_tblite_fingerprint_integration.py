# -*- coding: utf-8 -*-

"""Integration test: the real tblite MDI engine (seamm-xtb conda environment)
answers <FINGERPRINT, and its record, completed by seamm_mdi, is the fingerprint
xTBStep predicts. Skipped where the environment or a new enough seamm_mdi is not
available (e.g. CI)."""

import importlib.resources
import shutil
import subprocess

import numpy as np
import pytest

from xtb_step.xtb_step import xTBStep


def _engine_available():
    if shutil.which("conda") is None:
        return False
    try:
        from seamm_mdi.mdi_engine import complete_records  # noqa: F401
    except ImportError:
        return False
    result = subprocess.run(
        ["conda", "run", "-n", "seamm-xtb", "python", "-c",
         "import mdi, tblite.interface"],
        capture_output=True,
    )  # fmt: skip
    return result.returncode == 0


def test_real_engine_fingerprint_is_the_prediction():
    if not _engine_available():
        pytest.skip("seamm-xtb tblite engine environment not available")
    from seamm_mdi import MDIEngine

    script = str(importlib.resources.files("xtb_step") / "data" / "tblite_mdi.py")

    def build_argv(hostname, port):
        return [
            "conda", "run", "--live-stream", "-n", "seamm-xtb", "python", script,
            "-mdi",
            f"-role ENGINE -name TBLITE -method TCP -port {port} "
            f"-hostname {hostname}",
            "--method", "GFN2-xTB", "--charge", "0", "--uhf", "0",
        ]  # fmt: skip

    xyz = np.array([[0.0, 0.0, 0.0], [0.7572, 0.5859, 0.0], [-0.7572, 0.5859, 0.0]])
    with MDIEngine(build_argv, elements=[8, 1, 1], timeout=120.0) as engine:
        assert engine.supports("<FINGERPRINT") is True
        engine.set_coordinates(xyz, units="Å")
        energy = engine.energy(units="hartree")
        records = engine.fingerprints()
    assert -5.2 < energy < -4.9  # GFN2-xTB water, about -5.07 E_h
    record = records["energy"]
    assert record["program"] == "tblite"
    assert records["hessian"] is None
    mc = {"method": "GFN2-xTB", "options": {"mdi_method_arg": "GFN2-xTB"}}
    expected = xTBStep.expected_fingerprints(
        None, mc, kind="energy", version=record["version"]
    )
    assert record["fingerprint"] in expected
