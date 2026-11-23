# -*- coding: utf-8 -*-

"""The installer's two environments (2026.11.21): seamm-xtb through the base
installer, seamm-tblite the same way, in directory or archive storage, and nothing
for a shared installation. Fakes stand in for conda, the .ini file and the base
installer, so nothing is installed."""

from pathlib import Path

import pytest

pytest.importorskip("seamm_manager")

from xtb_step.installer import Installer  # noqa: E402


class FakeConfig:
    def __init__(self, values):
        self.values = dict(values)
        self.saved = 0

    def get_values(self, section):
        return dict(self.values)

    def set_value(self, section, key, value):
        self.values[key] = value

    def save(self):
        self.saved += 1


class FakeConda:
    def __init__(self, root, envs):
        self.root = Path(root)
        self.envs = dict(envs)  # name -> list of package names
        self.calls = []

    def exists(self, name):
        return name in self.envs

    def path(self, name):
        meta = self.root / name / "conda-meta"
        meta.mkdir(parents=True, exist_ok=True)
        for pkg in self.envs.get(name, []):
            (meta / f"{pkg}-1.0-0.json").write_text("{}")
        return self.root / name

    def delete_environment(self, name):
        self.calls.append(("delete", name))
        self.envs.pop(name, None)

    def create_environment(self, environment_file, name=None, **kwargs):
        self.calls.append(("create", name, Path(environment_file).name))
        self.envs[name] = []

    def update_environment(self, environment_file, name=None, **kwargs):
        self.calls.append(("update", name, Path(environment_file).name))
        self.envs.setdefault(name, [])


def make(tmp_path, monkeypatch, envs, archive=False, shared=False, ini=None):
    inst = object.__new__(Installer)
    inst.environment = "seamm-xtb"
    inst.section = "xtb-step"
    data = Path(__file__).resolve().parents[1] / "xtb_step" / "data"
    inst.environment_file = data / "seamm-xtb.yml"
    inst.tblite_environment = "seamm-tblite"
    inst.tblite_environment_file = data / "seamm-tblite.yml"
    conda = FakeConda(tmp_path / "envs", envs)
    config = FakeConfig(
        ini or {"installation": "conda", "conda-environment": "seamm-xtb"}
    )
    cls = type(inst)
    for name, value in (
        ("conda", conda),
        ("exe_config", config),
        ("archive_storage", archive),
        ("shared_codes", shared),
        ("manual_code", False),
        ("code_environments", "own"),
        ("root", tmp_path),
    ):
        monkeypatch.setattr(cls, name, property(lambda self, v=value: v))
    # The base installer's own work on seamm-xtb is not under test here.
    import seamm_manager.installer_base as base

    monkeypatch.setattr(base.InstallerBase, "update", lambda self: None)
    monkeypatch.setattr(base.InstallerBase, "install", lambda self: None)
    monkeypatch.setattr(cls, "_not_ours", lambda self, env: False)
    return inst, conda, config


def test_update_directory_drops_stale_xtb_and_makes_tblite(tmp_path, monkeypatch):
    inst, conda, config = make(
        tmp_path, monkeypatch, {"seamm-xtb": ["xtb", "tblite-python"]}
    )
    inst.update()
    assert ("delete", "seamm-xtb") in conda.calls
    assert ("create", "seamm-tblite", "seamm-tblite.yml") in conda.calls
    assert config.values["tblite-environment"] == "seamm-tblite"
    marker = tmp_path / "envs" / "seamm-tblite" / "conda-meta" / "seamm-xtb-step.sha256"
    assert marker.exists()


def test_update_directory_keeps_current_xtb(tmp_path, monkeypatch):
    inst, conda, config = make(
        tmp_path, monkeypatch, {"seamm-xtb": ["xtb"], "seamm-tblite": ["tblite-python"]}
    )
    inst.update()
    assert ("delete", "seamm-xtb") not in conda.calls
    assert ("update", "seamm-tblite", "seamm-tblite.yml") in conda.calls
    # the instance's environment file is restored after the tblite pass
    assert inst.environment_file.name == "seamm-xtb.yml"


def test_update_archive_builds_the_tblite_archive(tmp_path, monkeypatch):
    inst, conda, config = make(
        tmp_path, monkeypatch, {"seamm-xtb": ["xtb", "tblite-python"]}, archive=True
    )
    built = []
    import seamm_manager.archives as archives

    monkeypatch.setattr(archives, "current_archive", lambda root, env: None)
    monkeypatch.setattr(
        type(inst),
        "_archive",
        lambda self, env, reason: built.append((env, self.environment_file.name)),
    )
    inst.update()
    assert built == [("seamm-tblite", "seamm-tblite.yml")]
    assert conda.calls == []  # no directory work in archive storage
    assert config.values["tblite-environment"] == "seamm-tblite"


def test_shared_installation_is_left_alone(tmp_path, monkeypatch):
    inst, conda, config = make(
        tmp_path, monkeypatch, {"seamm-xtb": ["xtb", "tblite-python"]}, shared=True
    )
    inst.update()
    assert conda.calls == []
    assert "tblite-environment" not in config.values


def test_named_tblite_environment_is_kept(tmp_path, monkeypatch):
    inst, conda, config = make(
        tmp_path,
        monkeypatch,
        {"seamm-xtb": ["xtb"], "my-tblite": ["tblite-python"]},
        ini={
            "installation": "conda",
            "conda-environment": "seamm-xtb",
            "tblite-environment": "my-tblite",
        },
    )
    inst.install()
    assert ("update", "my-tblite", "seamm-tblite.yml") in conda.calls
    assert config.values["tblite-environment"] == "my-tblite"
