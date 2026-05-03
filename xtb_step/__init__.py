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

from .energy_step import EnergyStep  # noqa: F401
from .energy import Energy  # noqa: F401
from .energy_parameters import EnergyParameters  # noqa: F401
from .tk_energy import TkEnergy  # noqa: F401

from .optimization_step import OptimizationStep  # noqa: F401
from .optimization import Optimization  # noqa: F401
from .optimization_parameters import OptimizationParameters  # noqa: F401
from .tk_optimization import TkOptimization  # noqa: F401

from .frequencies_step import FrequenciesStep  # noqa: F401
from .frequencies import Frequencies  # noqa: F401
from .frequencies_parameters import FrequenciesParameters  # noqa: F401
from .tk_frequencies import TkFrequencies  # noqa: F401

# Handle versioneer
from ._version import get_versions

__author__ = "Paul Saxe"
__email__ = "psaxe@molssi.org"
versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions
