=========
Solvation
=========

The plug-in supports all three implicit solvation models that xTB
itself provides. The choice is set by the ``Implicit solvation``
parameter on every sub-step.

Solvation models
================

ALPB
----

**Analytical Linearized Poisson-Boltzmann** model. The current
recommended default for xTB-family calculations with implicit
solvation.

Parametrized for GFN1-xTB, GFN2-xTB, and GFN-FF.  **Not parametrized
for GFN0-xTB**; if you select GFN0 with ALPB, xtb will emit a
warning or refuse to run.

Citation: Ehlert, Stahn, Spicher, Grimme,
*J. Chem. Theory Comput.* **2021**, *17*, 4250.

GBSA
----

The earlier **Generalized Born / Surface Area** model. Retained
for backward compatibility with published xTB results. Use ALPB
for new work unless you have a specific reason.

Parametrized for the same methods as ALPB, with the same GFN0
caveat.

Citation: same paper as ALPB (Ehlert *et al.* 2021).

CPCM-X
------

**Conductor-like Polarizable Continuum Model** with extended
parameterization. Uses the Minnesota Solvation Database, so it
supports a wider range of solvents than ALPB / GBSA.

Citation: Stahn, Ehlert, Grimme,
*J. Phys. Chem. A* **2023**, *127*, 7036.

Supported solvents
==================

The plug-in's solvent dropdown lists the union of solvents
supported by xTB for ALPB / GBSA. Some solvents are
method-specific:

* **DMF** and **n-hexane** are GFN2-only.
* **Benzene** is GFN1-only.

xtb itself will warn or refuse at run time if you select an
unsupported method/solvent combination, so trying it is safe.

For ALPB/GBSA the supported list is::

    acetone, acetonitrile, benzene*, CH2Cl2, CHCl3, CS2,
    DMF*, DMSO, ether, H2O, methanol, n-hexane*, THF, toluene

(``*`` = method-specific as noted above).

CPCM-X uses the much larger Minnesota Solvation Database; the
plug-in's dropdown is enforced as an enumeration, but you can
also pass a variable that resolves to a free-text solvent name
if you need a solvent that is not in the dropdown.

Layout in the dialog
====================

When ``Implicit solvation`` is ``none``, the ``Solvent`` widget is
hidden. As soon as you select any other model, the ``Solvent``
widget appears, indented under the solvation-model row, with its
default of ``H2O``. Set it to ``none`` again and it disappears.

This makes flowcharts with no solvation visually clean while still
giving you immediate access to the solvent selector when you need
it.

Tips
====

* For aqueous biomolecule work, ``GFN2-xTB`` + ``ALPB`` +
  ``H2O`` is the standard starting point.
* For non-aqueous solvents, the same combination works for the
  solvents in the supported list; for everything else, switch to
  ``CPCM-X``.
* Implicit solvation changes geometries somewhat -- compare gas-phase
  and solvated optimized geometries if your downstream analysis is
  geometry-sensitive (e.g. conformer ratios).
