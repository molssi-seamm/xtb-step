==================================
xtb_step Phase E -- File Drop Notes
==================================

Two issues from your stdout review:

1. ``frequencies.py`` had ``from seamm_util.printing import FormattedText
   as __`` imported but never used.  Removed.
2. ``TkOptimization`` and ``TkFrequencies`` were stand-alone copies of
   the cookiecutter generic ``TkNode`` template -- so they did not
   inherit the dynamic solvent visibility from ``TkEnergy``, and
   future substeps (MD, ...) would have to re-implement the energy
   layout from scratch.  Refactored to the MOPAC pattern:
   ``TkOptimization`` inherits from ``TkEnergy``, ``TkFrequencies``
   inherits from ``TkOptimization``.  The energy frame and its
   conditional solvent layout are now defined exactly once.


Files in this drop
==================

Replace existing
----------------

``xtb_step/frequencies.py``
    Single-line change: removed the unused
    ``from seamm_util.printing import FormattedText as __`` import.
    Otherwise identical to Phase D.

``xtb_step/tk_energy.py``
    Restructured to be the GUI base class.  Modeled on
    ``mopac_step/tk_energy.py``.  Key design points:

    * ``create_dialog`` builds an explicit "energy frame"
      (``ttk.LabelFrame`` titled "Hamiltonian Parameters") and creates
      all energy widgets inside it.  The dialog is no longer a flat
      grid in ``self["frame"]``.
    * ``reset_dialog`` lays out the energy frame at row 0 and
      **returns the next free row** so subclasses can grid their own
      frames below it.
    * ``reset_energy_frame`` lays out the widgets *inside* the energy
      frame, with the conditional solvent visibility (hidden when
      ``solvation model == "none"``, indented in column 1 when shown).

``xtb_step/tk_optimization.py``
    Now ``class TkOptimization(TkEnergy)``.  Adds an "optimization frame"
    (``ttk.LabelFrame`` titled "Optimization") below the energy frame
    and creates only the optimization-specific widgets there
    (``optimization level``, ``max iterations``, ``structure handling``).
    The energy widgets and their dynamic behavior are inherited
    automatically from ``TkEnergy``.

``xtb_step/tk_frequencies.py``
    Now ``class TkFrequencies(TkOptimization)``.  Adds a "frequencies
    frame" titled "Frequencies / Thermochemistry" below the
    optimization frame, holding the frequency-specific widgets
    (``optimize first``, ``temperature``, ``pressure``).  ``optimize
    first`` is bound to ``reset_dialog`` so future iterations can
    hide the optimization frame when the user disables the initial
    optimization (v1 just re-lays out unconditionally).


Why the inheritance chain matches the parameter-class chain
============================================================

The non-GUI side already has::

    EnergyParameters
        <- OptimizationParameters
            <- FrequenciesParameters

It is natural and minimal-code for the GUI to mirror that::

    TkEnergy
        <- TkOptimization
            <- TkFrequencies

Each subclass walks ``ChildParameters.parameters`` and skips keys
already in any parent's parameters (so widgets are not double-created),
which means adding a parameter to ``EnergyParameters`` automatically
puts it in the energy frame for *all* substeps with no further code
change.  Adding a future MD substep with ``MDParameters(EnergyParameters)``
gets the energy frame and its solvent dynamics for free.


Not in this drop
================

``xtb_step/optimization.py``, ``xtb_step/xtb.py``,
``xtb_step/__init__.py``, ``xtb_step/setup.py``,
``xtb_step/energy_parameters.py``, ``xtb_step/substep.py``,
``xtb_step/metadata.py``, ``xtb_step/energy.py``,
``xtb_step/optimization_parameters.py``,
``xtb_step/frequencies_parameters.py``, the data files, and the
installer are all unchanged from your current working tree.


One unrelated thing flagged but not fixed
==========================================

Your stdout shows::

    WARNING:xtb_step.optimization:xtbopt.xyz not found at /Users/psaxe/tmp2/3/2/xtbopt.xyz
    WARNING:xtb_step.optimization:xtbopt.xyz not found at /Users/psaxe/tmp2/3/3/xtbopt.xyz

Step 3.2 is an Optimization that should produce ``xtbopt.xyz``.  Step
3.3 is a Frequencies run with ``--ohess`` (which is opt-then-Hessian),
which xtb may write to a different filename (``xtbhess.xyz`` or
``.xtboptok`` etc.) -- I would need to check current xtb output
conventions.

Worth a quick ``ls`` in those step directories to see what xtb
actually wrote.  This is a separate issue from the dialog refactor;
I would prefer to address it once we have a directory listing
showing what filenames are present, rather than guess at it.


Code style
==========

All four files compile cleanly.  All lines are <= 88 characters.
``black --check`` not run here (no install access in this
environment), so a first ``make format`` may produce small
whitespace adjustments -- those should be one pass and then stable.
