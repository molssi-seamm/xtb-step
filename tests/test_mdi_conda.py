# -*- coding: utf-8 -*-

"""The tblite MDI engine runs with the conda SEAMM's local executor would use:
CONDA_EXE first (on clusters SEAMM's staging wrapper, which unpacks an
environment kept as an archive onto the node), else the ini's conda. With the
ini's conda only, an archive-only seamm-tblite could not start on ARC (SEAMM job
6088, 2026-11-26)."""

import xtb_step


def _argv(monkeypatch, config):
    monkeypatch.setattr(
        xtb_step.xTBStep,
        "get_executor_config",
        classmethod(lambda cls, executor, options: dict(config)),
    )
    return xtb_step.xTBStep.get_mdi_engine_command(
        None, {}, method="GFN2-xTB", port=1234
    )


CONFIG = {
    "installation": "conda",
    "conda": "/apps/miniforge/bin/conda",
    "conda-environment": "seamm-xtb",
    "tblite-environment": "seamm-tblite",
    "mdi_script": "tblite_mdi.py",
}


def test_conda_exe_wins(monkeypatch):
    monkeypatch.setenv("CONDA_EXE", "/projects/seamm/SEAMM/bin/seamm-conda")
    argv = _argv(monkeypatch, CONFIG)
    assert argv[:5] == [
        "/projects/seamm/SEAMM/bin/seamm-conda",
        "run",
        "--live-stream",
        "-n",
        "seamm-tblite",
    ]


def test_the_ini_conda_without_conda_exe(monkeypatch):
    monkeypatch.delenv("CONDA_EXE", raising=False)
    assert _argv(monkeypatch, CONFIG)[0] == "/apps/miniforge/bin/conda"
    config = {k: v for k, v in CONFIG.items() if k != "conda"}
    assert _argv(monkeypatch, config)[0] == "conda"


def test_an_environment_path_uses_prefix(monkeypatch):
    monkeypatch.delenv("CONDA_EXE", raising=False)
    config = dict(CONFIG, **{"tblite-environment": "/envs/seamm-tblite"})
    argv = _argv(monkeypatch, config)
    assert argv[3:5] == ["-p", "/envs/seamm-tblite"]
