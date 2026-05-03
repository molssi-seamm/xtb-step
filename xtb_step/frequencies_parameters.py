# -*- coding: utf-8 -*-
"""
Control parameters for the xTB Frequencies step in a SEAMM flowchart.
"""

import logging
import pprint  # noqa: F401

from .optimization_parameters import OptimizationParameters

logger = logging.getLogger(__name__)


class FrequenciesParameters(OptimizationParameters):
    """The control parameters for an xTB Frequencies substep.

    Inherits everything from :class:`OptimizationParameters` because xtb's
    ``--ohess`` (the recommended frequency runtype) is an optimize-then-
    Hessian. When the user disables the initial optimization, the
    optimization-level and structure-handling parameters are simply ignored
    by the run() method.

    Adds:

    * ``optimize first`` -- whether to optimize the geometry before the
      Hessian (``--ohess`` if yes, ``--hess`` if no).
    * ``temperature`` -- the temperature for the thermochemistry table.
    * ``pressure`` -- the pressure for the thermochemistry table.
    """

    #: Local parameters added on top of OptimizationParameters.parameters.
    parameters = {
        "optimize first": {
            "default": "yes",
            "kind": "enum",
            "default_units": "",
            "enumeration": ("yes", "no"),
            "format_string": "s",
            "description": "Optimize first:",
            "help_text": (
                "Whether to optimize the geometry before computing the "
                "Hessian. 'yes' uses xtb's --ohess (recommended -- "
                "Hessians on unoptimized geometries are not physically "
                "meaningful). 'no' uses --hess and assumes the input "
                "geometry is already at a stationary point."
            ),
        },
        "temperature": {
            "default": 298.15,
            "kind": "float",
            "default_units": "K",
            "enumeration": tuple(),
            "format_string": ".2f",
            "description": "Temperature:",
            "help_text": (
                "Temperature for the thermochemistry table. "
                "Default 298.15 K (standard conditions)."
            ),
        },
        "pressure": {
            "default": 1.0,
            "kind": "float",
            "default_units": "atm",
            "enumeration": tuple(),
            "format_string": ".3f",
            "description": "Pressure:",
            "help_text": (
                "Pressure for the thermochemistry table. Default 1 atm. "
                "Note that xtb's thermo treatment uses the ideal-gas "
                "approximation; pressure enters only via the standard-"
                "state correction."
            ),
        },
    }

    def __init__(self, defaults={}, data=None):
        """Initialize the parameters."""
        logger.debug("FrequenciesParameters.__init__")
        super().__init__(
            defaults={**FrequenciesParameters.parameters, **defaults},
            data=data,
        )
