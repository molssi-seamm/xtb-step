# -*- coding: utf-8 -*-

"""
xtb_step
A SEAMM plug-in for xTB
"""

# Bring up the classes so that they appear to be directly in
# the xtb_step package.

from .xtb import xTB  # noqa: F401, E501
from .xtb_step import xTBStep  # noqa: F401, E501
from .tk_xtb import TkxTB  # noqa: F401, E501

from .metadata import metadata  # noqa: F401

# Handle versioneer
from ._version import get_versions

__author__ = "Paul Saxe"
__email__ = "psaxe@molssi.org"
versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions
