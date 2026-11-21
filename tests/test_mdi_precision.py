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


def test_engine_uses_tblite_environment(monkeypatch):
    """The engine runs in tblite-environment (seamm-tblite) when xtb.ini names it,
    and in conda-environment otherwise (installations before 2026.11.21)."""
    assert "seamm-xtb" in _argv(monkeypatch)
    assert (
        xtb_step.xtb_step.tblite_environment(
            {"conda-environment": "seamm-xtb", "tblite-environment": "seamm-tblite"}
        )
        == "seamm-tblite"
    )
    assert (
        xtb_step.xtb_step.tblite_environment({"conda-environment": "seamm-xtb"})
        == "seamm-xtb"
    )


def test_environment_files():
    """seamm-xtb holds a current xtb and no tblite; seamm-tblite holds tblite 0.5.0
    (tblite 0.6 with dftd4 4.2 segfaults for GFN2; re-checked 2026-11-21)."""
    import importlib.resources

    data = importlib.resources.files("xtb_step") / "data"
    xtb = (data / "seamm-xtb.yml").read_text()
    tblite = (data / "seamm-tblite.yml").read_text()
    assert (
        "xtb=6.7.1" in xtb
        and "tblite" not in xtb.split("dependencies:")[1].split("#")[0]
    )
    assert "tblite-python=0.5.0" in tblite and "pymdi" in tblite
