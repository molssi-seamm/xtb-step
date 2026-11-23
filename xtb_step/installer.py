# -*- coding: utf-8 -*-

"""Installer for the xTB plug-in.

This handles any further installation needed after installing the Python
package ``xtb-step``.
"""

import importlib
import logging
from pathlib import Path
import re
import subprocess

import seamm_installer

logger = logging.getLogger(__name__)


class Installer(seamm_installer.InstallerBase):
    """Handle further installation needed after installing xtb-step.

    The Python package ``xtb-step`` should already be installed, using
    ``pip``, ``conda``, or similar. This plug-in-specific installer then
    checks for the xtb executable, installing it if needed, and registers
    its location in ``seamm.ini`` (specifically in the ``xtb.ini``
    configuration file in the SEAMM root directory).

    There are a number of ways to determine which are the correct xtb
    executable to use. The aim of this installer is to help the user locate
    the executable. There are a number of possibilities:

    #. The correct executable is already available.

        #. If it is already registered in ``xtb.ini`` there is nothing else
           to do.

        #. It may be in the current path, in which case it needs to be added
           to ``xtb.ini``.

        #. If a module system is in use, a module may need to be loaded to
           give access to xtb.

        #. It cannot be found automatically, so the user needs to locate the
           executable for the installer.

    #. xtb is not installed on the machine. In this case it can be installed
       in a Conda environment. There is one choice:

        #. It can be installed in a separate environment, ``seamm-xtb`` by
           default, using the ``seamm-xtb.yml`` environment file shipped in
           ``xtb_step/data/``.

    The tblite MDI engine (QM-MD with LAMMPS) has its own environment,
    ``seamm-tblite`` (``seamm-tblite.yml``), recorded as ``tblite-environment``
    in xtb.ini. The two are apart since 2026.11.21: the tblite that works pins
    xtb 6.4.1, whose optimiser crashes with the current gfortran runtime.
    """

    def __init__(self, logger=logger):
        # Call the base class initialization, which sets up the commandline
        # parser, amongst other things.
        super().__init__(logger=logger)

        logger.debug("Initializing the xTB installer object.")

        # Define this step's details
        self.environment = "seamm-xtb"
        self.section = "xtb-step"
        self.executables = ["xtb"]

        self.resource_path = importlib.resources.files("xtb_step") / "data"

        # The environment.yaml file for Conda installations.
        logger.debug(f"data directory: {self.resource_path}")
        self.environment_file = self.resource_path / "seamm-xtb.yml"

        # The tblite MDI engine's environment, apart from xtb's
        self.tblite_environment = "seamm-tblite"
        self.tblite_environment_file = self.resource_path / "seamm-tblite.yml"

    def install(self):
        """Install xtb's environment (the base installer: its policies, archive
        storage, ...) and then the tblite engine's environment the same way."""
        super().install()
        self._install_tblite()

    def update(self):
        """Update both environments.

        A ``seamm-xtb`` directory made before 2026.11.21 also holds tblite 0.5.0,
        which pins xtb 6.4.1, and ``conda env update`` does not remove packages,
        so it could not move to the current xtb: such an environment is removed
        first and the base installer makes it again from the new file. Archives
        are always built afresh, so archive storage needs nothing extra.
        """
        self._drop_stale_xtb_environment()
        super().update()
        self._install_tblite()

    def _conda_installation(self):
        """The [local] section of xtb.ini if this is a conda installation SEAMM
        manages here (not shared, not a manual code), else None."""
        if self.shared_codes or self.manual_code:
            return None
        data = self.exe_config.get_values("local")
        if data.get("installation") != "conda":
            return None
        return data

    def _drop_stale_xtb_environment(self):
        """Remove a pre-2026.11.21 ``seamm-xtb`` directory that still holds
        tblite (directory storage only)."""
        data = self._conda_installation()
        if data is None or self.archive_storage:
            return
        environment = data.get("conda-environment") or self.environment
        try:
            if not self.conda.exists(environment) or self._not_ours(environment):
                return
            meta = Path(self.conda.path(environment)) / "conda-meta"
            stale = any(meta.glob("tblite-python-*.json"))
        except Exception:
            return
        if stale:
            print(
                f"    The Conda environment '{environment}' still holds tblite, which "
                "pins an old xtb; removing it so it is made again from "
                f"{Path(self.environment_file).name}."
            )
            self.conda.delete_environment(environment)

    def _tblite_environment_name(self, data):
        """The tblite environment's name: the .ini's, else the default (prefixed
        if this installation prefixes its code environments)."""
        if data.get("tblite-environment"):
            return data["tblite-environment"]
        name = self.tblite_environment
        if self.code_environments == "prefixed":
            from seamm_manager.naming import compute_tag
            from seamm_manager.policy import prefixed_environment

            name = prefixed_environment(name, compute_tag(self.root))
        return name

    def _install_tblite(self):
        """Create or update the tblite MDI engine's environment, in the
        installation's storage (directory or archive), and record it as
        ``tblite-environment`` in xtb.ini."""
        data = self._conda_installation()
        if data is None:
            return
        environment = self._tblite_environment_name(data)
        saved = self.environment_file
        self.environment_file = self.tblite_environment_file
        try:
            if self.archive_storage:
                from seamm_manager import archives

                if archives.current_archive(
                    self.root, environment
                ) is not None and self._archive_up_to_date(environment):
                    print(
                        f"    The archive of the Conda environment '{environment}' "
                        "is up to date (built from this environment file)."
                    )
                else:
                    self._archive(environment, "Building")
            elif self.conda.exists(environment):
                if self._unchanged_since_applied(environment):
                    print(
                        f"    The Conda environment '{environment}' is up to date "
                        "(the environment file is unchanged since it was applied)."
                    )
                else:
                    print(f"    Updating Conda environment '{environment}' for tblite.")
                    self.conda.update_environment(
                        self.environment_file, name=environment
                    )
                    self._record_applied(environment)
            else:
                print(f"    Installing Conda environment '{environment}' for tblite.")
                self.conda.create_environment(self.environment_file, name=environment)
                self._record_applied(environment)
        finally:
            self.environment_file = saved
        self.exe_config.set_value("local", "tblite-environment", environment)
        self.exe_config.save()

    def exe_version(self, config):
        """Get the version of the xtb executable.

        Parameters
        ----------
        config : dict
            Configuration data for invoking xtb. Typical keys are
            ``conda`` (the path to the conda executable) and
            ``conda-environment`` (the name or full path of the env in
            which xtb is installed).

        Returns
        -------
        ("xTB", str)
            A tuple of the code label and the version string reported by
            the executable. The version is ``"unknown"`` if it could not
            be determined.
        """
        environment = config["conda-environment"]
        conda = config["conda"]

        # Build the conda invocation. If the environment string looks like
        # an explicit path (starts with ~ or is absolute), pass it via
        # `-p`; otherwise pass it via `-n`.
        if environment[0] == "~":
            environment = str(Path(environment).expanduser())
            command = f"'{conda}' run --live-stream -p '{environment}' xtb --version"
        elif Path(environment).is_absolute():
            command = f"'{conda}' run --live-stream -p '{environment}' xtb --version"
        else:
            command = f"'{conda}' run --live-stream -n '{environment}' xtb --version"

        logger.debug(f"    Running {command}")
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                shell=True,
            )
        except Exception as e:
            logger.debug(f"    Failed to run {command}: {e}")
            version = "unknown"
        else:
            logger.debug(f"    {result.stdout}")
            # xtb --version prints a banner followed by a line like:
            #     * xtb version 6.7.1 (c3cfd38) compiled by ... on ...
            # We anchor on the literal "xtb version" to avoid matching the
            # banner. The version token is the next whitespace field.
            version = "unknown"
            pattern = re.compile(r"xtb\s+version\s+([\w.+-]+)", re.IGNORECASE)
            for line in result.stdout.splitlines():
                m = pattern.search(line)
                if m:
                    version = m.group(1)
                    break

        return "xTB", version
