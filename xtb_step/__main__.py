# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""Handle the installation of the xTB step."""

from .installer import Installer


def run():
    """Handle the extra installation needed.

    * Find and/or install the xtb executable.
    * Add or update information in the SEAMM xtb.ini file for xTB.
    """

    # Create an installer object
    installer = Installer()
    installer.run()


if __name__ == "__main__":
    run()
