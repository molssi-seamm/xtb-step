# -*- coding: utf-8 -*-
"""
Control parameters for the xTB Optimization step in a SEAMM flowchart.
"""

import logging
import pprint  # noqa: F401

from .energy_parameters import EnergyParameters

logger = logging.getLogger(__name__)


class OptimizationParameters(EnergyParameters):
    """The control parameters for an xTB Optimization substep.

    Inherits the method/charge/multiplicity/accuracy/solvation parameters
    from :class:`EnergyParameters` and adds the optimizer-specific knobs.
    """

    #: Optimization level enumeration. xtb's ``--opt LEVEL`` accepts these
    #: predefined criterion sets (energy and gradient convergence
    #: thresholds), per the xTB documentation
    #: https://xtb-docs.readthedocs.io/en/latest/optimization.html
    OPT_LEVELS = (
        "crude",
        "sloppy",
        "loose",
        "lax",
        "normal",
        "tight",
        "vtight",
        "extreme",
    )

    #: Local parameters added on top of EnergyParameters.parameters.
    parameters = {
        "optimization level": {
            "default": "normal",
            "kind": "enum",
            "default_units": "",
            "enumeration": OPT_LEVELS,
            "format_string": "s",
            "description": "Optimization level:",
            "help_text": (
                "The convergence criteria preset for xtb's ANCopt "
                "geometry optimizer. 'normal' is the default. 'tight' or "
                "tighter is recommended before a frequency calculation."
            ),
        },
        "max iterations": {
            "default": "default",
            "kind": "integer",
            "default_units": "",
            "enumeration": ("default",),
            "format_string": "d",
            "description": "Maximum iterations:",
            "help_text": (
                "Maximum number of optimization iterations. Use 'default' "
                "to let xtb decide (typically scales with system size)."
            ),
        },
        "structure handling": {
            "default": "Overwrite the current configuration",
            "kind": "enum",
            "default_units": "",
            "enumeration": (
                "Overwrite the current configuration",
                "Add a new configuration",
                "Add a new system",
                "Discard the optimized structure",
            ),
            "format_string": "s",
            "description": "Optimized structure:",
            "help_text": (
                "What to do with the optimized geometry. 'Overwrite' "
                "replaces the current configuration's coordinates in "
                "place. 'Add a new configuration' keeps the input "
                "geometry and stores the optimized one as a new "
                "configuration in the same system. 'Add a new system' "
                "creates a fresh system entirely. 'Discard' keeps the "
                "input unchanged and just records the energy."
            ),
        },
    }

    def __init__(self, defaults={}, data=None):
        """Initialize the parameters.

        Combines (a) the inherited EnergyParameters set, (b) the local
        OptimizationParameters set, and (c) any caller-supplied defaults.
        """
        logger.debug("OptimizationParameters.__init__")
        super().__init__(
            defaults={**OptimizationParameters.parameters, **defaults},
            data=data,
        )
