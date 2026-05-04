# -*- coding: utf-8 -*-

"""This file contains metadata describing the results from xTB.

The dictionary ``metadata`` is consumed by SEAMM's ``store_results`` machinery
on ``seamm.Node`` to:

* describe the computational models (Hamiltonians) the plug-in supports;
* enumerate any keywords the plug-in defines (xTB is controlled almost
  entirely by command-line flags, so this section is small);
* enumerate the results the plug-in can produce, with their dimensionality,
  units, the property name in the SEAMM database, and which sub-step
  (calculation) generates them.
"""

metadata = {}

# ---------------------------------------------------------------------------
# Computational models
# ---------------------------------------------------------------------------
# xTB is a tight-binding family of methods; "Hamiltonian" is used loosely here
# to group GFN0/GFN1/GFN2/GFN-FF together. ``periodic`` is False because v1
# refuses periodic input.
#
# ``elements`` reflects the parametrization range. GFN0/1/2 are parametrized
# for Z = 1-86 (H-Rn). GFN-FF covers the whole periodic table up to Z = 86 as
# well, per Spicher & Grimme 2020.
metadata["computational models"] = {
    "Tight binding": {
        "models": {
            "GFN2-xTB": {
                "parameterizations": {
                    "GFN2-xTB": {
                        "elements": "1-86",
                        "periodic": False,
                        "reactions": True,
                        "optimization": True,
                        "code": "xtb",
                    },
                },
            },
            "GFN1-xTB": {
                "parameterizations": {
                    "GFN1-xTB": {
                        "elements": "1-86",
                        "periodic": False,
                        "reactions": True,
                        "optimization": True,
                        "code": "xtb",
                    },
                },
            },
            "GFN0-xTB": {
                "parameterizations": {
                    "GFN0-xTB": {
                        "elements": "1-86",
                        "periodic": False,
                        "reactions": True,
                        "optimization": True,
                        "code": "xtb",
                    },
                },
            },
            "GFN-FF": {
                "parameterizations": {
                    "GFN-FF": {
                        "elements": "1-86",
                        "periodic": False,
                        "reactions": False,
                        "optimization": True,
                        "code": "xtb",
                    },
                },
            },
        },
    },
}

# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------
# xTB does not really have an input deck for the simple workflows we expose
# in v1; control happens via command-line flags. We leave this empty for now
# but keep the slot so future work (e.g. xcontrol detailed input) has a
# natural home.
metadata["keywords"] = {}

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
# Each entry's ``calculation`` field lists which sub-step (matching
# ``self._calculation`` in the substep classes) can produce that result. The
# ``property`` field, if present, is the database property name, with the
# ``{model}`` placeholder substituted at storage time with the active xTB
# Hamiltonian (e.g. "GFN2-xTB").
metadata["results"] = {
    "total_energy": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The total energy",
        "dimensionality": "scalar",
        "property": "total energy#xTB#{model}",
        "type": "float",
        "units": "E_h",
        "format": ".6f",
    },
    "electronic_energy": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The electronic energy (excluding nuclear repulsion)",
        "dimensionality": "scalar",
        "property": "electronic energy#xTB#{model}",
        "type": "float",
        "units": "E_h",
        "format": ".6f",
    },
    "homo_lumo_gap": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The HOMO-LUMO gap",
        "dimensionality": "scalar",
        "property": "band gap#xTB#{model}",
        "type": "float",
        "units": "eV",
        "format": ".4f",
    },
    "homo_energy": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The HOMO orbital energy",
        "dimensionality": "scalar",
        "property": "HOMO energy#xTB#{model}",
        "type": "float",
        "units": "eV",
        "format": ".4f",
    },
    "lumo_energy": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The LUMO orbital energy",
        "dimensionality": "scalar",
        "property": "LUMO energy#xTB#{model}",
        "type": "float",
        "units": "eV",
        "format": ".4f",
    },
    "dipole_moment": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The molecular dipole moment magnitude",
        "dimensionality": "scalar",
        "property": "dipole moment#xTB#{model}",
        "type": "float",
        "units": "debye",
        "format": ".4f",
    },
    "dipole_vector": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The molecular dipole moment vector",
        "dimensionality": [3],
        "type": "float",
        "units": "debye",
    },
    "partial_charges": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The atomic partial charges",
        "dimensionality": ["n_atoms"],
        "type": "float",
        "units": "e",
    },
    "gradients": {
        "calculation": ["Energy", "Optimization", "Frequencies"],
        "description": "The gradient of the energy with respect to the coordinates",
        "dimensionality": [3, "n_atoms"],
        "property": "gradients#xTB#{model}",
        "type": "json",
        "units": "E_h/Å",
    },
    "frequencies": {
        "calculation": ["Frequencies"],
        "description": "The vibrational frequencies",
        "dimensionality": ["n_modes"],
        "type": "float",
        "units": "1/cm",
    },
    "ir_intensities": {
        "calculation": ["Frequencies"],
        "description": "The IR intensities for each vibrational mode",
        "dimensionality": ["n_modes"],
        "type": "float",
        "units": "km/mol",
    },
    "reduced_masses": {
        "calculation": ["Frequencies"],
        "description": "The reduced masses for each vibrational mode",
        "dimensionality": ["n_modes"],
        "type": "float",
        "units": "amu",
    },
    "zero_point_energy": {
        "calculation": ["Frequencies"],
        "description": "The zero-point vibrational energy",
        "dimensionality": "scalar",
        "property": "zero point energy#xTB#{model}",
        "type": "float",
        "units": "kJ/mol",
        "format": ".4f",
    },
    "enthalpy": {
        "calculation": ["Frequencies"],
        "description": "The thermal enthalpy H(T)",
        "dimensionality": "scalar",
        "type": "float",
        "units": "kJ/mol",
        "format": ".4f",
    },
    "entropy_term": {
        "calculation": ["Frequencies"],
        "description": "The entropic contribution T*S",
        "dimensionality": "scalar",
        "type": "float",
        "units": "kJ/mol",
        "format": ".4f",
    },
    "entropy": {
        "calculation": ["Frequencies"],
        "description": "The entropy S",
        "dimensionality": "scalar",
        "property": "entropy#xTB#{model}",
        "type": "float",
        "units": "J/mol/K",
        "format": ".4f",
    },
    "gibbs_free_energy": {
        "calculation": ["Frequencies"],
        "description": "The Gibbs free energy G(T)",
        "dimensionality": "scalar",
        "property": "Gibbs free energy#xTB#{model}",
        "type": "float",
        "units": "kJ/mol",
        "format": ".4f",
    },
    "total_free_energy": {
        "calculation": ["Frequencies"],
        "description": "The total free energy (electronic + G(RRHO))",
        "dimensionality": "scalar",
        "type": "float",
        "units": "kJ/mol",
        "format": ".4f",
    },
    "temperature": {
        "calculation": ["Frequencies"],
        "description": "The temperature for the thermochemistry",
        "dimensionality": "scalar",
        "type": "float",
        "units": "K",
        "format": ".2f",
    },
}
