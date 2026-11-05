# -*- coding: utf-8 -*-

"""precision="tight" asks the tblite MDI engine for accuracy 1e-4 (finite
differences of gradients need it: the warm-started SCF otherwise leaves noise
that depends on the previous geometry)."""

import xtb_step


def _argv(monkeypatch, **kwargs):
    monkeypatch.setattr(
        xtb_step.xTBStep,
        "get_executor_config",
        classmethod(
            lambda cls, executor, options: {
                "installation": "conda",
                "conda": "conda",
                "conda-environment": "seamm-xtb",
                "mdi_script": "tblite_mdi.py",
            }
        ),
    )
    return xtb_step.xTBStep.get_mdi_engine_command(
        None, {}, method="GFN2-xTB", port=1234, **kwargs
    )


def test_tight_precision(monkeypatch):
    argv = _argv(monkeypatch, precision="tight")
    i = argv.index("--accuracy")
    assert argv[i + 1] == "1e-4"


def test_default_precision(monkeypatch):
    assert "--accuracy" not in _argv(monkeypatch)
