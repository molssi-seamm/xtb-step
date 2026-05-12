=============================
xtb_step v1 -- Scope Document
=============================

:Status: Draft, agreed in chat
:Plug-in:    ``xtb_step``
:Top-level class: ``xTB``
:Step display name: ``xTB``
:Sub-steps: ``Energy``, ``Optimization``, ``Frequencies``


Goal of v1
==========

Produce a SEAMM plug-in that lets a flowchart run xTB single-point
energies, geometry optimizations, and vibrational frequencies (with the
thermochemistry table that xTB prints alongside a Hessian run), for
molecular systems, with optional implicit solvation, using xTB's
GFN0/GFN1/GFN2/GFN-FF methods.  The plug-in installs xTB automatically
via conda (``seamm-xtb`` environment from conda-forge), integrates with
the SEAMM property database, and fails gracefully on periodic input.

It is not intended to be production-grade or to expose every xTB
option; subsequent releases will add MD, metadynamics, reaction-path,
mode-following, and electronic-property workflows.


Why this is not redundant with the existing DFTB+ xTB driver
============================================================

``dftbplus_step`` already exposes GFN1-xTB and GFN2-xTB through DFTB+'s
internal xTB driver, and the SEAMM paper [Saxe2025]_ uses that route for
the methylisocyanide benchmark.  A standalone ``xtb_step`` adds:

- GFN0-xTB and GFN-FF, neither of which is available via DFTB+
- Native ALPB and CPCM-X solvation [Ehlert2021]_
- Native xTB Hessian and the xTB thermochemistry block
- A direct path to MD, metadynamics, and other xTB drivers in v2+


Naming and Packaging
====================

- Repository name: ``xtb_step``
- Top-level class: ``xTB`` (preserving the code's case)
- Step display name: ``xTB``
- Conda environment: ``seamm-xtb`` (deps: ``python``, ``xtb`` from
  conda-forge -- requires verification that ``xtb`` is published on
  conda-forge under that exact name)
- Group in the menus:

  - Top-level: ``Simulations``
  - Sub-steps:  ``Calculations``

- Stevedore entry points (in ``setup.py``):

  - ``org.molssi.seamm`` -> top-level ``xTB``
  - ``org.molssi.seamm.tk`` -> top-level ``xTB``
  - ``org.molssi.seamm.xtb`` -> three sub-steps
  - ``org.molssi.seamm.xtb.tk`` -> three sub-steps


Architecture
============

Subflowchart pattern modeled on ``fhi_aims_step``.  The top-level
``xTB`` step contains a subflowchart; the user adds ``Energy``,
``Optimization``, or ``Frequencies`` sub-step nodes into it.

Class hierarchy:

- ``Energy`` is the base class with the parameters and machinery shared
  by all sub-steps (method, charge, multiplicity, solvation, accuracy,
  threading, the JSON parser, the executable-finding, the property
  storage).
- ``Optimization`` inherits from ``Energy`` and adds optimizer
  parameters (level, max iterations) and structure-handling controls.
- ``Frequencies`` inherits from ``Energy`` and adds the
  optimize-first toggle and thermochemistry temperature/pressure.

Each sub-step invokes the ``xtb`` binary itself with its own command
line.  The top-level ``run()`` method only iterates the subflowchart
and lets each substep run; it does not build a single combined input
file (this is the pattern in ``fhi_aims_step``, not the pattern in
``mopac_step`` or ``lammps_step``).

The cookiecutter-generated top-level ``run()`` uses the wrong
(LAMMPS-style) template and must be replaced before the plug-in will
run.


Methods
=======

Single enumeration parameter, exposed at the ``Energy`` level so all
sub-steps inherit it:

==============  =====================  =================================================
Choice          xTB CLI flag            Citation
==============  =====================  =================================================
GFN2-xTB (def)  ``--gfn 2``             [Bannwarth2019]_
GFN1-xTB        ``--gfn 1``             [Grimme2017]_
GFN0-xTB        ``--gfn 0``             [Pracht2019]_
GFN-FF          ``--gfnff``             [Spicher2020]_
==============  =====================  =================================================

The general xTB review [Bannwarth2021]_ is cited at level 1 whenever
any of these methods is used.


Tasks and CLI mapping
=====================

============  =================================================================
Sub-step       xTB invocation
============  =================================================================
Energy         ``xtb coord.xyz --<method> --json [--alpb solvent] --chrg N --uhf M``
Optimization   adds ``--opt <level>`` (level in
                  {crude,sloppy,loose,normal,tight,vtight,extreme}; default
                  ``normal``)
Frequencies    ``--ohess <level>`` (optimize-then-Hessian) by default;
                  ``--hess`` if user disables initial optimization
============  =================================================================

The ``Frequencies`` sub-step harvests xTB's thermochemistry block
(ZPE, S, Cv, H, G at a chosen temperature/pressure) directly from the
xTB output.  No separate Thermochemistry sub-step in v1.  The standalone
``thermochemistry_step`` plug-in remains usable downstream for users who
want finite-difference verification, per [Saxe2025]_ Section 3.


Solvation
=========

Two parameters at the ``Energy`` level:

- ``solvation model``: enumeration ``none`` (default), ``ALPB``,
  ``GBSA``, ``CPCM-X``
- ``solvent``: enumeration of xTB's supported solvent list (water,
  methanol, DMSO, acetone, acetonitrile, chloroform, dichloromethane,
  DMF, ether, hexane, octanol, THF, toluene, ...).  The exact list
  depends on the xTB version and on the solvation model; we will pull
  the canonical list from the xTB documentation
  (https://xtb-docs.readthedocs.io/) at implementation time.

CLI mapping:

- ``ALPB`` -> ``--alpb <solvent>``
- ``GBSA`` -> ``--gbsa <solvent>``
- ``CPCM-X`` -> ``--cpcmx <solvent>``


Periodic Systems
================

xTB's PBC support is limited and not part of v1.  Behavior on periodic
input:

1. At the start of every sub-step's ``run()``, check
   ``configuration.periodicity``.
2. If non-zero, ``printer.important()`` an explanatory message.
3. ``raise RuntimeError`` so the flowchart stops with a clear error.

This matches the convention used elsewhere in the SEAMM plug-in
ecosystem.


Installation
============

Default ``installation = conda``, conda environment ``seamm-xtb`` from
``data/seamm-xtb.yml``.  The ``.ini`` follows the
``dftbplus.ini`` template (DFTB+ is also conda-default since it's on
conda-forge).  Sections: ``[docker]`` and ``[local]``, with ``[local]``
supporting installation modes ``conda``, ``modules``, ``local``, and
``docker``.

Following the ``mopac_step`` pattern, the plug-in provides an
``installer.py`` that knows how to:

- create the conda environment
- check whether xTB is callable
- report the installed xTB version


Input / Output Strategy
=======================

Input:
  Write ``coord.xyz`` (XYZ format).  All other options are passed on
  the xtb command line; no input deck file is needed.  Charge and
  multiplicity go through ``--chrg N`` and ``--uhf M`` (where M is
  the number of unpaired electrons; xTB convention).

Output:
  Primary parser uses the JSON output produced by ``--json`` (file
  ``xtbout.json``).  Energies, gradients, dipole, Mulliken/CM5
  charges, HOMO/LUMO are pulled from there.  The thermochemistry block
  (ZPE, entropy, Cp, Gibbs free energy) is parsed from the text
  ``xtb.out`` because, as of recent xTB versions, the thermo block is
  not part of the JSON output.  This needs verification at
  implementation time against a current xtb release.

Working directory layout:
  Each sub-step gets its own directory under the SEAMM job tree
  (handled automatically by ``seamm.Node``).  The directory contains
  ``coord.xyz``, ``xtbout.json``, ``xtb.out``, ``stdout.txt``,
  ``stderr.txt``, and (for optimization) ``xtbopt.xyz`` and
  ``xtbopt.log``.


Properties Seed
===============

Initial ``data/properties.csv`` entries, using the
``<name>#xTB#{model}`` convention from ``mopac_step``.  ``{model}`` is
filled with the active method (``GFN2-xTB`` etc.) at runtime.

- ``total energy#xTB#{model}``  (float, E_h)
- ``electronic energy#xTB#{model}``  (float, E_h)
- ``HOMO energy#xTB#{model}``  (float, eV)
- ``LUMO energy#xTB#{model}``  (float, eV)
- ``band gap#xTB#{model}``  (float, eV)
- ``dipole moment#xTB#{model}``  (float, D)
- ``gradients#xTB#{model}``  (json, E_h/Bohr)
- ``force constants#xTB#{model}``  (json, E_h/Bohr^2)
- ``enthalpy of formation#xTB#{model}``  (float, kJ/mol)
- ``zero point energy#xTB#{model}``  (float, kJ/mol)
- ``entropy#xTB#{model}``  (float, J/mol/K)
- ``constant pressure heat capacity#xTB#{model}``  (float, J/mol/K)
- ``Gibbs free energy#xTB#{model}``  (float, kJ/mol)


Out of Scope for v1
===================

The following xTB capabilities are deliberately deferred:

- Molecular dynamics (``--md``)
- Metadynamics (``--metadyn``)
- Nudged elastic band / reaction path (``--path``)
- Mode-following (``--modef``)
- Vertical IP/EA, Fukui (``--vipea``, ``--vfukui``)
- Custom xcontrol files
- Periodic systems
- ONIOM / QM-MM via wrappers


Open Items to Verify at Implementation Time
===========================================

1. Exact ``xtbout.json`` schema in the current xTB release.  Will
   verify against https://xtb-docs.readthedocs.io/ before writing the
   parser.  Fall back to text scraping if needed.
2. Whether ``xtb`` is actually published on conda-forge under the
   package name ``xtb``.  Will check with ``conda search -c
   conda-forge xtb``.
3. Whether to expose ``--acc N`` (accuracy multiplier, default 1.0).
   Recommend yes, since it's the main quality knob users actually turn.
4. Whether to expose OMP thread count as a parameter.  Recommend yes,
   mirroring ``mopac_step`` and ``dftbplus_step``.
5. Whether ``--bhess`` (biased single-point Hessian) is worth
   exposing alongside ``--hess`` / ``--ohess``.  Recommend no for v1.


Skeleton Issues to Fix Before First Useful Build
================================================

The cookiecutter-generated skeleton has two issues that need to be
addressed before any code-fill-in:

1. **Top-level ``run()`` template is wrong.**  ``xtb_step/xtb.py``
   uses the LAMMPS-style "build single ``molssi.dat`` from
   ``node.get_input()`` and run the binary once" template.  This is
   not the right pattern for xTB.  Replace with the
   ``fhi_aims_step``-style iterate-and-let-substeps-run pattern.

2. **``pkg_resources`` is deprecated.**  Replace ``pkg_resources``
   imports with ``importlib.resources`` in ``xtb.py``,
   ``energy.py``, ``optimization.py``, and ``frequencies.py``.


References
==========

.. [Saxe2025] Saxe, P.; et al.  *SEAMM: A Simulation Environment for
              Atomistic and Molecular Modeling.*  J. Phys. Chem. A
              **2025**, 129, 6973-6993.
              https://doi.org/10.1021/acs.jpca.5c03164

.. [Bannwarth2021] Bannwarth, C.; Caldeweyher, E.; Ehlert, S.; Hansen,
                   A.; Pracht, P.; Seibert, J.; Spicher, S.; Grimme, S.
                   *Extended tight-binding quantum chemistry methods.*
                   WIREs Comput. Mol. Sci. **2021**, 11, e1493.
                   https://doi.org/10.1002/wcms.1493

.. [Bannwarth2019] Bannwarth, C.; Ehlert, S.; Grimme, S.  *GFN2-xTB --
                   An Accurate and Broadly Parametrized Self-Consistent
                   Tight-Binding Quantum Chemical Method with Multipole
                   Electrostatics and Density-Dependent Dispersion
                   Contributions.*  J. Chem. Theory Comput.  **2019**,
                   15, 1652-1671.
                   https://doi.org/10.1021/acs.jctc.8b01176

.. [Grimme2017] Grimme, S.; Bannwarth, C.; Shushkov, P.  *A Robust
                and Accurate Tight-Binding Quantum Chemical Method for
                Structures, Vibrational Frequencies, and Noncovalent
                Interactions of Large Molecular Systems Parametrized
                for All spd-Block Elements (Z = 1-86).*  J. Chem.
                Theory Comput.  **2017**, 13, 1989-2009.
                https://doi.org/10.1021/acs.jctc.7b00118

.. [Pracht2019] Pracht, P.; Caldeweyher, E.; Ehlert, S.; Grimme, S.
                *A Robust Non-Self-Consistent Tight-Binding Quantum
                Chemistry Method for Large Molecules.*  ChemRxiv,
                **2019**.  https://doi.org/10.26434/chemrxiv.8326202.v1
                (Note: GFN0-xTB has no formal journal paper as of last
                check; verify the citation status at implementation
                time.)

.. [Spicher2020] Spicher, S.; Grimme, S.  *Robust Atomistic Modeling of
                 Materials, Organometallic, and Biochemical Systems.*
                 Angew. Chem. Int. Ed.  **2020**, 59, 15665-15673.
                 https://doi.org/10.1002/anie.202004239

.. [Ehlert2021] Ehlert, S.; Stahn, M.; Spicher, S.; Grimme, S.  *Robust
                and Efficient Implicit Solvation Model for Fast
                Semiempirical Methods.*  J. Chem. Theory Comput.
                **2021**, 17, 4250-4261.
                https://doi.org/10.1021/acs.jctc.1c00471
