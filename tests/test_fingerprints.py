# -*- coding: utf-8 -*-

"""The settings fingerprints of the tblite MDI engine: what the engine records
(data/tblite_settings.py, completed on the driver's side) and what xTBStep predicts
must be the same, and differ for different settings."""

import pytest

from seamm_util.fingerprint import calculation_record

from xtb_step.xtb_step import tblite_settings, xTBStep

GFN2 = {"level": "xTB:SQM@GFN2-xTB", "method": "GFN2-xTB", "step": "xTB",
        "options": {"mdi_method_arg": "GFN2-xTB"}}  # fmt: skip
GFN1 = {"level": "xTB:SQM@GFN1-xTB", "method": "GFN1-xTB", "step": "xTB",
        "options": {"mdi_method_arg": "GFN1-xTB"}}  # fmt: skip


def predict(mc=GFN2, version="0.5.0", **options):
    return xTBStep.expected_fingerprints(
        None, mc, kind="energy", options=options, version=version
    )


def test_the_engines_record_is_the_prediction():
    """The engine sends its record without the hash; completed as seamm_mdi
    completes it, it is the predicted fingerprint."""
    settings = tblite_settings()
    record = settings.settings_record("GFN2-xTB", 1.0, version="0.5.0")
    assert "fingerprint" not in record
    try:
        from seamm_mdi.mdi_engine import complete_records
    except ImportError:  # an older seamm_mdi: complete it as it would
        complete_records = None
    if complete_records is not None:
        done = complete_records({"energy": record, "hessian": None})
        assert done["hessian"] is None
        fingerprint = done["energy"]["fingerprint"]
    else:
        fingerprint = calculation_record(
            record["program"], record["version"], record["files"]
        )["fingerprint"]
    assert predict() == [fingerprint]


def test_different_settings_differ():
    base = predict()[0]
    assert predict(mc=GFN1)[0] != base
    assert predict(precision="tight")[0] != base
    assert predict(version="0.6.0")[0] != base


def test_what_does_not_change_the_energy():
    base = predict()
    # only major.minor of the version is hashed
    assert predict(version="0.5.1") == base
    # the structure (charge, spin, geometry) belongs to the species
    assert (
        xTBStep.expected_fingerprints(object(), GFN2, kind="energy", version="0.5.0")
        == base
    )
    # no analytic Hessian: a Hessian has the energy's fingerprint
    assert (
        xTBStep.expected_fingerprints(None, GFN2, kind="hessian", version="0.5.0")
        == base
    )


def test_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        xTBStep.expected_fingerprints(None, GFN2, kind="dipole", version="0.5.0")


def test_settings_text():
    settings = tblite_settings()
    assert settings.settings_text("GFN2-xTB") == "method GFN2-xTB\naccuracy 1.0\n"
    assert settings.settings_text("GFN2-xTB", 1e-4).endswith("accuracy 0.0001\n")
    assert settings.PROGRAM == "tblite"
