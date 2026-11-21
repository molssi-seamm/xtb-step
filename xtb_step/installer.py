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
        """Install xtb's environment and the tblite engine's environment."""
        super().install()
        self.install_tblite()

    def update(self):
        """Update both environments.

        seamm-xtb is recreated from its file rather than updated: before
        2026.11.21 it also held tblite 0.5.0, which pins xtb 6.4.1, and
        ``conda env update`` does not remove packages, so it could not move to
        the current xtb.
        """
        data = self.exe_config.get_values("local")
        if data.get("installation") == "conda":
            environment = data.get("conda-environment") or self.environment
            print(
                f"    Recreating Conda environment '{environment}' from "
                f"{self.environment_file.name}. This may take a minute or two."
            )
            if self.conda.exists(environment):
                self.conda.delete_environment(environment)
            self.conda.create_environment(self.environment_file, name=environment)
            self.exe_config.set_value("local", "conda-environment", environment)
            self.exe_config.save()
            self.install_tblite()
            print("    Done!\n")
        else:
            super().update()

    def install_tblite(self):
        """Create or update the tblite MDI engine's environment and record it
        as ``tblite-environment`` in xtb.ini (conda installations only)."""
        data = self.exe_config.get_values("local")
        if data.get("installation") != "conda":
            return
        environment = data.get("tblite-environment") or self.tblite_environment
        if self.conda.exists(environment):
            print(f"    Updating Conda environment '{environment}' for tblite.")
            self.conda.update_environment(
                self.tblite_environment_file, name=environment
            )
        else:
            print(f"    Installing Conda environment '{environment}' for tblite.")
            self.conda.create_environment(
                self.tblite_environment_file, name=environment
            )
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
