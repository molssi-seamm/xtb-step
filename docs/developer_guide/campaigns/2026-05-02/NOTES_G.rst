==================================
xtb_step Phase G -- File Drop Notes
==================================

Three small fixes from your last review:

1. The substep dialogs (Energy, Optimization, Frequencies) need to
   be sized as large as the top-level xTB step dialog so the results
   tab is usable without scrolling.  Added the same screen-sizing
   code to ``TkEnergy.create_dialog`` so all three substep dialogs
   inherit it.

2. The xtb output suggests several citations beyond what we currently
   add to the references handler -- in particular DFT-D4 dispersion
   citations (Caldeweyher 2017/2019/2020), which apply when GFN2-xTB
   is in use (GFN2 uses a D4-style dispersion correction), and
   Stahn 2023 for CPCM-X solvation.  Added these to
   ``data/references.bib`` and to ``Energy._cite_references`` with
   appropriate level (level 1 for CPCM-X since it is the primary
   model citation; level 2 for the D4 papers since they are
   component citations).

3. The solvent widget hides correctly but its indentation is wrong
   because the main-column labels have varying lengths.  Switched to
   the Gaussian-step pattern (``w1 - w2 + 30``-style
   ``columnconfigure``) which ensures the indented label starts at
   the column-0 value position regardless of how long the
   main-column labels are.


Files in this drop
==================

Replace existing
----------------

``xtb_step/tk_energy.py``
    Two changes:

    * ``create_dialog`` now sizes the dialog to 90% width by 80% height
      of the screen, centered, immediately after
      ``super().create_dialog(...)`` returns.  Pattern lifted from
      ``TkxTB.create_dialog``.  ``TkOptimization`` and
      ``TkFrequencies`` inherit this automatically (their
      ``create_dialog`` calls ``super().create_dialog`` first).
    * ``reset_energy_frame`` now uses the Gaussian-step indentation
      idiom: ``widgets`` for the main column, ``widgets2`` for the
      indented column, ``align_labels`` on each separately, and
      ``e_frame.columnconfigure(0, minsize=w1 - w2 + 30)`` to size
      column 0 so column 1's label lines up with column 0's value
      positions.

``xtb_step/energy.py``
    Extended ``_cite_references`` to:

    * Add a level-1 citation for CPCM-X (Stahn 2023) when CPCM-X is
      the chosen solvation model.  The existing Ehlert 2021 citation
      remains for ALPB / GBSA.
    * Add three level-2 component citations (Caldeweyher 2017, 2019,
      2020 for DFT-D4) whenever GFN2-xTB is the active method.  GFN1,
      GFN0, and GFN-FF use older / different dispersion treatments
      and do NOT trigger these.  This matches what xtb's own output
      recommends.

    The structure of the function is otherwise unchanged --
    method-specific citations stay at level 1 keyed off ``method``,
    solvation citations stay at level 1 keyed off
    ``solvation_model``, the new component citations are added at
    level 2 in a clearly labelled block at the bottom.

``xtb_step/data/references.bib``
    Four new BibTeX entries appended:

    * ``Stahn2023`` -- CPCM-X solvation (J. Phys. Chem. A 2023, 127,
      7036-7043, DOI 10.1021/acs.jpca.3c04382)
    * ``Caldeweyher2017`` -- D3-extension dispersion model
      (J. Chem. Phys. 2017, 147, 034112)
    * ``Caldeweyher2019`` -- D4 dispersion correction (J. Chem.
      Phys. 2019, 150, 154122)
    * ``Caldeweyher2020`` -- D4 dispersion for periodic systems
      (Phys. Chem. Chem. Phys. 2020, 22, 8499-8512)


Not in this drop
================

``tk_optimization.py`` and ``tk_frequencies.py`` are unchanged from
Phase F.  They inherit the dialog-sizing change automatically through
``super().create_dialog(...)``.  The other modules
(``substep.py``, ``frequencies.py``, etc.) and the data files
``properties.csv``, ``seamm-xtb.yml``, ``xtb.ini`` are also
unchanged.


Test plan after copying
========================

1. ``make lint && make install && make test`` -- still pass.
2. Open all three substep edit dialogs.  All three should now be
   90% x 80% of your screen, with the results tab visible without
   scrolling.
3. Open Energy.  Set "Implicit solvation" to "ALPB" (or any non-
   ``none`` value).  The Solvent label should now be visually
   indented from the left edge so its label starts roughly where
   the values column starts.  Switch back to "none"; solvent
   disappears.  The previous "barely indented" look should be gone.
4. Run a flowchart with GFN2-xTB.  The references list should now
   include three Caldeweyher entries (level 2 -- they appear in the
   *secondary* references list, not primary).  Run the same
   flowchart with GFN1-xTB or GFN-FF; the Caldeweyher entries
   should NOT appear.
5. Run a flowchart with CPCM-X solvation.  Stahn 2023 should appear
   in the primary references list.


Anything still missing
======================

The xtb output suggests further citations for advanced workflows that
are out of scope for v1 of the plug-in:

* sTDA-xTB, mass-spec, metadynamics, SPH calculations, ONIOM, DIPRO,
  the program-package paper (Grimme, Mueller, Hansen 2023).

When v1.x or v2 adds the corresponding workflows (MD, metadynamics,
TD-xTB), the matching citations should be added here too.  For now
the level-1 + level-2 set covers what xtb actually used during a
single-point / opt / freq run with GFN2-xTB plus optional implicit
solvation -- which is exactly what v1 supports.


Code style
==========

All files compile cleanly, all lines <= 88 characters.  The diffs
against Phase F are surgical (10-line block added to
``create_dialog``, 6-line block changed in ``reset_energy_frame``,
~30-line block added to ``_cite_references``, 4 new BibTeX entries
in ``references.bib``).
