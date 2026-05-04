==================================
xtb_step Phase H -- File Drop Notes
==================================

Two design changes from the citations / units discussion:

1. Citation levels: promote the three DFT-D4 (Caldeweyher 2017, 2019,
   2020) papers from level 2 to level 1.  Reasoning is below.

2. Thermochemistry units: convert ZPE, H(T), T*S, G(T), and the total
   free energy from xtb's native E_h to kJ/mol at parse time.  Add a
   derived ``entropy`` quantity in J/mol/K so the chemist's natural
   form of S (rather than just T*S) appears in the table.


Rationale: citation levels
==========================

After looking at how MOPAC handles citations, my Phase G placement of
the D4 papers at level 2 was wrong.  MOPAC puts at level 1 the
program citation, the Hamiltonian paper, every dispersion correction
the user enabled (PM6-D3 cites Grimme 2010, PM6-DH+ cites Korth 2010,
etc.), and even individual element-parameter papers when those
elements are present.  A typical MOPAC PM7 calculation produces a
level-1 list of 5-10 references.

The SEAMM convention is "level 1 = anything that contributed to
producing this result; let the user cull to fit the journal's
citation budget".  Level 2 is for component-of-component references
that the user almost never wants in a primary list.

By that standard, the three D4 papers belong at level 1 whenever
GFN2-xTB is the active method, because GFN2's dispersion correction
is part of the method.  A user writing a paper with GFN2-xTB
calculations might cite all three (or just one canonical one), but
SEAMM's job is to surface them in the primary list rather than hide
them.

So Phase H promotes them.  GFN1, GFN0, and GFN-FF still do not
trigger D4 citations (those methods use older D3-style or different
dispersion treatments).

The current level-1 list for a default GFN2-xTB + ALPB-water
calculation is now:

* SEAMM (from the framework, automatic)
* RDKit (from from_smiles_step, automatic)
* Bannwarth 2021 (xTB program)
* Bannwarth 2019 (GFN2-xTB)
* Ehlert 2021 (ALPB)
* Caldeweyher 2017, 2019, 2020 (DFT-D4)
* xtb_step itself (from the plug-in self-cite, automatic)

A chemist writing a paper would probably keep all of these for a
methods section.  No level-2 citations fall out of v1 yet -- they
will once we add MD (need metadynamics ref), TD-xTB, etc.


Rationale: thermochemistry units
================================

Looking at thermochemistry_step's metadata, all of H, U, ZPE, G are
declared in kJ/mol and S in J/mol/K.  That matches what every modern
chemistry textbook and every Gaussian / Q-Chem / ORCA paper reports.
xtb's native output is in E_h, which is fine for the electronic
energy but unhelpful for thermo quantities -- nobody publishes
"G(T) = 0.002482 E_h".

This drop converts thermo energies at parse time using
``Q_(value, "E_h").to("kJ/mol")``, the same idiom used in
``thermochemistry_step``, ``gaussian_step``, and ``psi4_step``.  The
electronic energy and orbital energies stay in their existing units
(E_h for total/electronic energy, eV for HOMO/LUMO/gap) -- those are
also the chemistry-paper conventions.

I also added a derived ``entropy`` quantity (S in J/mol/K)
alongside ``entropy_term`` (T*S in kJ/mol).  xtb's output gives only
T*S; the entropy itself is computed as ``T*S * 1000 / T``.  Both
appear in the results table; only ``entropy`` (J/mol/K, the form
used in standard chemistry tables) is stored as a database property
since T*S as a separate property is rarely useful.


Files in this drop
==================

Replace existing
----------------

``xtb_step/energy.py``
    ``_cite_references``: the three Caldeweyher D4 cite calls now use
    ``level=1`` instead of ``level=2``.  Docstring rewritten to
    describe SEAMM's "level 1 = comprehensive contributing-papers
    list, user culls" convention.  Method-specific citations
    (Bannwarth/Grimme/Pracht/Spicher) and the solvation citations
    (Ehlert/Stahn) keep their existing level=1.

``xtb_step/substep.py``
    ``parse_thermo_block``: now converts E_h to kJ/mol on the fly
    using ``ureg.hartree.to("kJ/mol").magnitude`` as the conversion
    factor.  Also computes the new ``entropy`` field (S in J/mol/K)
    from the T*S column via ``S = T*S * 1000 / T``.  Returned dict
    keys are: ``temperature`` (K), ``zero_point_energy``,
    ``enthalpy``, ``entropy_term``, ``gibbs_free_energy``,
    ``total_free_energy`` (all kJ/mol), ``entropy`` (J/mol/K).

``xtb_step/metadata.py``
    All thermo entries' ``units`` field changed from ``"E_h"`` to
    ``"kJ/mol"``; ``format`` changed from ``.6f`` (which is
    appropriate for E_h with 6 significant decimals) to ``.4f``
    (appropriate for kJ/mol values that range from single digits to
    a few thousand).  New ``entropy`` entry in J/mol/K with a
    database property name ``entropy#xTB#{model}``.  ``entropy_term``
    is no longer a database property (it remains a results-table row
    for users who like the T*S form).

``xtb_step/frequencies.py``
    The thermo block in ``analyze`` now includes ``"entropy"`` in
    the key tuple, ordered between ``entropy_term`` and
    ``gibbs_free_energy`` so the table reads naturally:
    ZPE, H(T), T*S, S, G(T), total free, T.


Not in this drop
================

``tk_*.py``, ``optimization.py``, ``__init__.py``, ``setup.py``,
``energy_parameters.py``, ``optimization_parameters.py``,
``frequencies_parameters.py``, ``xtb.py``, the data files, and the
installer are unchanged.


Sanity check on the conversion
==============================

From the previous job.out (water, GFN2-xTB):

* ZPE was 0.020101 E_h = 52.78 kJ/mol.  Experimental water ZPE is
  ~55-56 kJ/mol; GFN2-xTB underestimates slightly, which is
  consistent with what the literature reports for tight-binding
  methods on hydrogen-bond systems.
* G(T) (the G(RRHO) contribution) was 0.002482 E_h = 6.52 kJ/mol.
  Reasonable for water at 298 K.
* T*S was 0.021400 E_h = 56.18 kJ/mol; entropy = 56.18 * 1000 / 298.15
  = 188.4 J/mol/K.  Literature water gas-phase entropy at 298.15 K
  is ~189 J/mol/K -- agrees almost exactly.  This is a nice
  sanity check on the parser and the conversion.


Test plan
=========

1. ``make lint && make install && make test`` -- still pass.
2. Re-run the water Energy/Optimization/Frequencies flowchart.
3. The Frequencies summary table should now show ZPE, H(T), T*S, S,
   G(T), total free energy in kJ/mol (with S in J/mol/K), with
   numbers that look like 52.78, 62.71, 56.18, 188.4, 6.52,
   -13311.78 (or thereabouts -- water E in kJ/mol scaled from
   -5.07 E_h).
4. The references list should now include the three Caldeweyher
   papers in the *primary* references section, not the secondary
   one.  The total primary count for GFN2-xTB+ALPB should be 6
   xtb-related references plus the framework refs.

Code style
==========

All four files compile cleanly, all lines <= 88 characters.  The
diffs are localized: one method body changed in ``substep.py``, six
metadata entries updated in ``metadata.py``, six lines changed in
``energy.py`` (the ``level=2`` -> ``level=1`` and the docstring),
and one tuple item added in ``frequencies.py``.
