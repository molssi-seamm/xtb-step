# -*- coding: utf-8 -*-
"""
Control parameters for the xTB Energy step in a SEAMM flowchart.
"""

import logging
import seamm
import pprint  # noqa: F401

from .substep import (
    METHODS,
    SOLVATION_MODELS,
    SOLVENTS_GBSA_ALPB,
)

logger = logging.getLogger(__name__)


class EnergyParameters(seamm.Parameters):
    """The control parameters for an xTB Energy substep.

    These parameters are inherited by Optimization (which adds optimizer
    controls) and Frequencies (which adds Hessian controls). Anything that is
    common to all substeps -- method, accuracy, solvation -- lives here.

    Note that net charge and spin multiplicity are NOT parameters of this
    step. They are properties of the configuration, accessed at run time
    via ``configuration.charge`` and ``configuration.spin_multiplicity``.
    This matches the convention throughout SEAMM: O2 (S=0), O2 triplet,
    and O2+ are different chemical species, not different parameter
    settings on the same calculation.
    """

    parameters = {
        "method": {
            "default": "GFN2-xTB",
            "kind": "enum",
            "default_units": "",
            "enumeration": METHODS,
            "format_string": "s",
            "description": "xTB method:",
            "help_text": (
                "The xTB Hamiltonian or force-field to use. GFN2-xTB is "
                "the default, recommended self-consistent method "
                "(Bannwarth, Ehlert, Grimme, JCTC 2019). GFN1-xTB is the "
                "earlier self-consistent method. GFN0-xTB is non-SCF and "
                "useful for rough screening or as a robust starting point. "
                "GFN-FF is a generic force field automatically "
                "parameterized by xTB."
            ),
        },
        "accuracy": {
            "default": 1.0,
            "kind": "float",
            "default_units": "",
            "enumeration": tuple(),
            "format_string": ".3f",
            "description": "Accuracy:",
            "help_text": (
                "The xTB accuracy multiplier (xtb --acc). Lower values "
                "give tighter integral and SCC convergence; the default "
                "1.0 is appropriate for most calculations. Useful range: "
                "roughly 0.0001 to 1000."
            ),
        },
        "solvation model": {
            "default": "none",
            "kind": "enum",
            "default_units": "",
            "enumeration": SOLVATION_MODELS,
            "format_string": "s",
            "description": "Implicit solvation:",
            "help_text": (
                "Implicit solvation model. ALPB (analytical linearized "
                "Poisson-Boltzmann, Ehlert et al. JCTC 2021) is the "
                "current recommended default and is parametrized for "
                "GFN1-xTB, GFN2-xTB, and GFN-FF (not GFN0-xTB). GBSA is "
                "the legacy generalized-Born model. CPCM-X uses the "
                "Minnesota Solvation Database."
            ),
        },
        "solvent": {
            "default": "H2O",
            "kind": "enum",
            "default_units": "",
            "enumeration": SOLVENTS_GBSA_ALPB,
            "format_string": "s",
            "description": "Solvent:",
            "help_text": (
                "The solvent for implicit solvation. Available solvents "
                "depend on the solvation model. Some solvents are "
                "method-specific in xTB (e.g. DMF and n-hexane are "
                "GFN2-only, benzene is GFN1-only); xtb will issue a "
                "warning at runtime if an unsupported combination is "
                "selected."
            ),
        },
        "extra keywords": {
            "default": [],
            "kind": "list",
            "default_units": "",
            "enumeration": tuple(),
            "format_string": "",
            "description": "Extra keywords",
            "help_text": (
                "Extra keywords to append to those from the GUI. "
                "This allows you to add to and override the GUI."
            ),
        },
        "results": {
            "default": {},
            "kind": "dictionary",
            "default_units": "",
            "enumeration": tuple(),
            "format_string": "",
            "description": "results",
            "help_text": "The results to save to variables or in tables.",
        },
    }

    def __init__(self, defaults={}, data=None):
        """Initialize the parameters.

        Parameters
        ----------
        defaults : dict
            A dictionary of parameters to initialize. The class-level
            parameters are used first; ``defaults`` overrides/adds to them.
        data : dict
            A dictionary of keys and a sub-dictionary with value and units
            for updating the current default values.
        """
        logger.debug("EnergyParameters.__init__")
        super().__init__(
            defaults={**EnergyParameters.parameters, **defaults}, data=data
        )
