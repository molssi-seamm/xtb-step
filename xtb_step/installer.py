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
