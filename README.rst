=================
SEAMM xTB Plug-in
=================

.. image:: https://img.shields.io/github/issues-pr-raw/molssi-seamm/xtb_step
   :target: https://github.com/molssi-seamm/xtb_step/pulls
   :alt: GitHub pull requests

.. image:: https://github.com/molssi-seamm/xtb_step/workflows/CI/badge.svg
   :target: https://github.com/molssi-seamm/xtb_step/actions
   :alt: Build Status

.. image:: https://codecov.io/gh/molssi-seamm/xtb_step/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/molssi-seamm/xtb_step
   :alt: Code Coverage

.. image:: https://github.com/molssi-seamm/xtb_step/workflows/CodeQL/badge.svg
   :target: https://github.com/molssi-seamm/xtb_step/security/code-scanning
   :alt: Code Quality

.. image:: https://github.com/molssi-seamm/xtb_step/workflows/Release/badge.svg
   :target: https://molssi-seamm.github.io/xtb_step/index.html
   :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/xtb_step.svg
   :target: https://pypi.python.org/pypi/xtb_step
   :alt: PyPi VERSION

A SEAMM plug-in for the `xTB <https://github.com/grimme-lab/xtb>`_ family
of extended tight-binding methods from the Grimme group.

* Free software: BSD-3-Clause
* Documentation: https://molssi-seamm.github.io/xtb_step/index.html
* Code: https://github.com/molssi-seamm/xtb_step

Features
--------

* Single-point energies, geometry optimizations, and harmonic
  vibrational frequencies for molecular (non-periodic) systems.
* The full set of xTB Hamiltonians and the GFN-FF force field:

  - **GFN2-xTB** (default) -- self-consistent, multipole electrostatics,
    density-dependent dispersion. Recommended for general use.
  - **GFN1-xTB** -- earlier self-consistent method.
  - **GFN0-xTB** -- non-self-consistent, useful for robust screening.
  - **GFN-FF** -- generic force field, automatically parameterized.

* Implicit solvation with all three xTB-supported models:

  - **ALPB** -- analytical linearized Poisson-Boltzmann
    (Ehlert et al., *J. Chem. Theory Comput.* **2021**, *17*, 4250).
  - **GBSA** -- generalized-Born model.
  - **CPCM-X** -- conductor-like polarizable continuum
    (Stahn et al., *J. Phys. Chem. A* **2023**, *127*, 7036).

  with the standard xTB solvent list (water, methanol, DMSO,
  acetonitrile, etc.).

* Net charge and spin multiplicity are read from the configuration,
  so the same flowchart works unchanged across O\ :sub:`2`,
  triplet O\ :sub:`2`, and O\ :sub:`2`\ :sup:`+` -- a single loop
  can scan a list of systems with different charge/spin states.

* Optimization with all eight xTB convergence levels (crude through
  extreme) and flexible structure handling: overwrite the current
  configuration in place, store the optimized structure as a new
  configuration, store it in a new system, or discard.

* Vibrational analysis using xTB's analytic Hessian, with the
  optimize-then-Hessian (``--ohess``) workflow recommended by xTB
  (or ``--hess`` alone if the geometry is already at a stationary
  point). Thermochemistry quantities (ZPE, H(T), T*S, S, G(T),
  total free energy) are reported in chemist-friendly units of
  kJ/mol and J/mol/K, not E\ :sub:`h`.

* Tabulated results in the local ``step.out`` and storage in the
  SEAMM property database using the standard ``<name>#xTB#{model}``
  property-naming convention, so downstream plug-ins
  (Thermochemistry, Reaction Path, ...) can pick up the values.

* Automatic citation tracking. The principal xTB program reference,
  the active GFN method reference, the DFT-D4 dispersion references
  (for GFN2-xTB), and the implicit-solvation reference are all added
  to the run's reference list automatically.

* Automatic installation of the xtb executable into a dedicated
  ``seamm-xtb`` conda environment via the standard SEAMM Installer.

Acknowledgements
----------------

This package was created with the `molssi-seamm/cookiecutter-seamm-plugin`_ tool, which
is based on the excellent Cookiecutter_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`molssi-seamm/cookiecutter-seamm-plugin`: https://github.com/molssi-seamm/cookiecutter-seamm-plugin

Developed by the Molecular Sciences Software Institute (MolSSI_),
which receives funding from the `National Science Foundation`_ under
award CHE-2136142.

.. _MolSSI: https://molssi.org
.. _`National Science Foundation`: https://www.nsf.gov
