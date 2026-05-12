===================================
xtb_step Phase D -- File Drop Notes
===================================

This drop addresses the six items from your last review:

1. Top-level ``xtb.py`` no longer sets ``self._metadata`` -- you
   already have that fix in place.
2. ``energy_parameters.py`` now has ``"extra keywords"`` declared --
   you already have that fix; this drop additionally drops ``charge``
   and ``multiplicity`` per items 3 below.
3. Net charge and spin multiplicity moved off the parameters and onto
   the configuration -- now read via ``configuration.charge`` and
   ``configuration.spin_multiplicity`` in ``substep.base_xtb_args``.
4. The Energy dialog now hides the ``solvent`` widget when
   ``solvation model == "none"`` and indents it under the solvation
   row when shown.
5. ``setup.py`` got a ``console_scripts`` entry for the installer --
   you already added that.
6. Results are now reported as a tabulated summary (Gaussian-style),
   with the table accumulated through the inheritance chain.


Files in this drop
==================

Replace existing
----------------

``xtb_step/energy_parameters.py``
    Drops ``charge`` and ``multiplicity`` from the parameter set.
    Keeps ``extra keywords``, ``method``, ``accuracy``, ``solvation
    model``, ``solvent``, ``results``. The class docstring explains
    the convention.

``xtb_step/substep.py``
    ``base_xtb_args(P, configuration)`` now reads charge and
    multiplicity from the configuration:

    .. code-block:: python

        charge = int(configuration.charge)
        mult = int(configuration.spin_multiplicity)

    Same as MOPAC's ``mopac.py:run()``. No other changes to this file.

``xtb_step/metadata.py``
    Adds ``"format"`` strings to the scalar float results so the
    table can format them sensibly:

    * total / electronic / electronic energy and ZPE / G(T): ``.6f``
    * HOMO / LUMO / gap: ``.4f``
    * dipole moment: ``.4f``
    * temperature: ``.2f``

    No structural changes -- the same 17 results, same property
    names, same dimensionalities.

``xtb_step/energy.py``
    Two visible changes:

    * ``description_text`` no longer mentions charge or multiplicity.
      Otherwise unchanged.
    * ``analyze`` now builds a ``tabulate``-formatted summary with
      ``Property | Value | Units`` columns, takes an optional
      ``table=`` argument so subclasses can prepend rows, prints the
      result with a centered title, and gracefully handles missing
      results.
    * ``run`` reads ``extra keywords`` from ``P`` and appends them
      after the substep-specific args (so users can override / add
      to xTB's CLI flags).

``xtb_step/frequencies.py``
    The ``analyze`` method replaces the old
    ``_post_run_thermo_and_freqs``. It re-parses the JSON / vibspectrum
    / thermo block, calls ``store_results`` for the new fields, and
    builds a single ordered table:

    1. Frequency-count summary rows ("Number of frequencies",
       "Imaginary frequencies").
    2. Energy / orbital / dipole rows (same set as Energy.analyze).
    3. Thermochemistry rows (ZPE, H, T*S, G(T), total free energy,
       temperature).

    The table is printed with a "Frequencies / Thermochemistry" title.

``xtb_step/tk_energy.py``
    Dynamic dialog. The solvation-model widget is bound to a
    ``reset_energy_frame`` method (modeled on
    ``mopac_step.tk_energy``). When the model changes, the frame is
    re-laid out: ``solvent`` appears in column 1 (indented) only when
    the model is not ``"none"``. The labels in each column are
    aligned with ``sw.align_labels`` separately so they read cleanly.


Not in this drop
================

``xtb_step/optimization.py``
    Unchanged from Phase B. It does not need to override
    ``analyze``: when ``Energy.run()`` calls ``self.analyze(data, P=P)``
    on an ``Optimization`` instance, Python's MRO picks up the
    inherited ``Energy.analyze`` automatically. If you ever want
    optimization-specific rows ("Convergence: ...", "Max gradient:
    ..."), the simplest pattern is to override ``analyze`` to add
    rows then call ``super().analyze(data=data, table=table, P=P)``.

``xtb_step/xtb.py``, ``xtb_step/__init__.py``, ``xtb_step/setup.py``
    Use the versions you uploaded.

``xtb_step/xtb_parameters.py``
    From the Phase C drop. With the working
    no-``self._metadata``-at-top-level approach you found, this file
    is no longer referenced by ``xtb.py`` and could be removed. If
    you remove it, also remove the ``from .xtb_parameters import
    xTBParameters`` line from ``__init__.py``. (Leaving it in is
    harmless -- the class just sits there unused.)


Open issues / risk register for this drop
==========================================

1. **Configuration attribute names.** I'm assuming
   ``configuration.charge`` and ``configuration.spin_multiplicity``
   are the right attribute names on a molsystem ``Configuration``,
   based on the MOPAC code I quoted. If a different attribute name
   is used in the version of molsystem you have, you'll see an
   ``AttributeError`` and we'll need to adjust.

2. **Dialog widget API.** ``self["solvation model"].combobox.bind(...)``
   is the pattern from ``mopac_step.tk_energy``. If the seamm-widgets
   version installed in your env exposes the underlying widget
   differently (some plug-ins use ``self[key].bind(...)`` directly,
   without ``.combobox``), the bind will fail at dialog-creation
   time.  If that happens, change ``smodel.combobox.bind`` to
   ``smodel.bind``.

3. **store_results called twice in Frequencies.** Energy.run() calls
   ``store_results`` once with the JSON-derived data, then
   ``Frequencies.analyze`` calls it again with the freq + thermo
   additions. SEAMM's ``store_results`` is idempotent for repeated
   calls with the same property name, but if you see duplicate
   property entries in the database, this is where to look.

4. **Frequencies.analyze duplicates the Energy.analyze table-build
   loop.** This is intentional but not pretty: I needed to interleave
   the freq-count rows BEFORE the energy rows but the thermo rows
   AFTER, which the simple "subclass adds then super() prints" pattern
   in Gaussian doesn't quite handle. If we ever want a cleaner
   factoring, the right move is to add a helper method on Energy
   like ``_append_energy_rows(table, data)`` that
   ``Frequencies.analyze`` can call between its own pre- and post-
   sections.


What to test
============

1. ``make lint && make install && make test`` -- still passes.
2. Open the Energy substep dialog. The solvent widget should be
   hidden when "Implicit solvation" is "none". Pick "ALPB" -- solvent
   should appear, indented. Pick "none" again -- solvent disappears.
3. Run a simple Energy job (e.g. methane). The job.out should
   contain a tabulated summary like:

   .. code-block::

                          xTB (GFN2-xTB) Results
        ╭─────────────────────────────────────┬───────────┬───────╮
        │             Property                │   Value   │ Units │
        ├─────────────────────────────────────┼───────────┼───────┤
        │           The total energy          │ -4.174678 │  E_h  │
        │       The HOMO orbital energy       │ -13.4827  │   eV  │
        │       The LUMO orbital energy       │   2.4567  │   eV  │
        │         The HOMO-LUMO gap           │  15.9394  │   eV  │
        │  The molecular dipole moment ...    │   0.0000  │ debye │
        ╰─────────────────────────────────────┴───────────┴───────╯

   (Exact wording and number of rows depends on which keys xTB
   actually emitted in xtbout.json.)
4. Run an Optimization job. Same table; geometry updated.
5. Run a Frequencies job on water. Table should now include
   "Number of frequencies", "Imaginary frequencies", and the
   thermochemistry rows beneath the energy rows.
6. Run on O2 in its triplet state and on O2- (a stored
   configuration with charge -1, multiplicity 2). xTB should pick
   up the charge and multiplicity from the configuration without
   any per-step parameter editing -- demonstrating the SEAMM
   convention for high-throughput.


Code style
==========

All files compile cleanly. All lines are <= 88 characters. I have
not been able to run ``black --check`` here, so a first
``make format`` may produce small whitespace adjustments -- those
should be one pass and then stable.
