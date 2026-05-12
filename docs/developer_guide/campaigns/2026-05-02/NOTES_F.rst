===================================
xtb_step Phase F -- File Drop Notes
===================================

Three real bugs from your last test run, all fixed:

1. ``KeyError: 'optimization frame'`` and the analogous ``'frequencies
   frame'`` error when opening the Optimization / Frequencies edit
   dialogs.  Root cause: my Phase E ``TkEnergy.create_dialog`` ended
   with ``self.reset_dialog()``, which Python's MRO dispatched to the
   subclass ``reset_dialog`` -- but at that point the subclass
   ``create_dialog`` had not yet built its own frames, so the lookup
   blew up.

2. (Same bug, fixed by the same removal in
   ``TkOptimization.create_dialog`` and ``TkFrequencies.create_dialog``.)

3. ``xtbopt.xyz`` and ``xtbtopo.mol`` were not coming back from the
   work directory because ``return_files`` only listed
   ``["xtbout.json", "xtbrestart"]``.  Extended to glob over the
   commonly-written xtb output files.


Files in this drop
==================

Replace existing
----------------

``xtb_step/tk_energy.py``
    One-line change: removed the ``self.reset_dialog()`` call at the
    end of ``create_dialog``, and added a comment explaining why it
    must not go there.  Detailed reasoning below.

``xtb_step/tk_optimization.py``
    Same one-line removal at the end of ``create_dialog``.

``xtb_step/tk_frequencies.py``
    Same one-line removal at the end of ``create_dialog``.

``xtb_step/energy.py``
    Changed ``return_files`` from
    ``["xtbout.json", "xtbrestart"]`` to::

        return_files = [
            "xtbout.json",
            "xtbrestart",
            "*.xyz",          # xtbopt.xyz and any other xyz files
            "*.mol",          # xtbtopo.mol topology file
            "*.log",          # xtbopt.log optimization trajectory
            "vibspectrum",    # Turbomole-format IR spectrum
            "hessian",        # Turbomole-format Hessian matrix
            "g98.out",        # Gaussian-98 output for visualization
        ]

    Modeled on the Gaussian step's use of ``["*.cube"]`` /
    ``["*"]`` glob patterns in its CubeGen invocations.


Why the dialog bug happened
===========================

The flow when the user double-clicks an Optimization step:

1. ``seamm.tk_node.edit()`` calls ``self.create_dialog()``.
2. Python's MRO dispatches to ``TkOptimization.create_dialog()``.
3. ``TkOptimization.create_dialog`` calls ``super().create_dialog()``,
   which goes to ``TkEnergy.create_dialog()``.
4. ``TkEnergy.create_dialog`` builds ``self["energy frame"]``, creates
   the energy widgets, binds the solvation-model widget, and (in
   Phase E) called ``self.reset_dialog()`` at the end.
5. ``self.reset_dialog()`` is *also* MRO-dispatched, so it goes to
   ``TkOptimization.reset_dialog()``.
6. ``TkOptimization.reset_dialog`` does
   ``row = super().reset_dialog()`` (which lays out the energy frame
   fine) then tries ``self["optimization frame"].grid(...)`` --
   **but the optimization frame doesn't exist yet**.  Subclass
   ``create_dialog`` has not built it.  KeyError.

The MOPAC pattern (which I should have copied more carefully) ends
each ``create_dialog`` with ``self.logger.debug("Finished creating
the dialog")`` and ``return frame``, and **never** calls
``self.reset_dialog`` from within ``create_dialog``.  The seamm
framework's ``tk_node.edit()`` calls ``reset_dialog`` itself, after
``create_dialog`` has fully unwound through all the subclass and
parent calls, so by the time ``reset_dialog`` runs every frame
exists.

This is now noted in the comments at the bottom of each
``create_dialog``.


Why the missing files happened
==============================

Your directory listing for step 3.2 (Optimization) showed::

    coord.xyz, stderr.txt, stdout.txt, step.out,
    xtb.err, xtb.out, xtbout.json, xtbrestart

xtb's own log (the ``xtb.out`` file you sent) reports::

    Writing topology from bond orders to xtbtopo.mol
    optimized geometry written to: xtbopt.xyz

So xtb did write both files into the working directory, but the
seamm executor's "return files" mechanism only copies back the files
listed in ``return_files`` to the long-term step directory.  The
defaults in Phase D were too restrictive.

The new globs are deliberately permissive -- ``*.xyz`` /  ``*.mol`` /
``*.log`` will pick up anything xtb might write under those
extensions in any future xtb release, plus the explicit names for
the Turbomole-format files (``vibspectrum``, ``hessian``) and the
Gaussian-format file (``g98.out``).


Not in this drop
================

All the other files from Phase D / Phase E (``substep.py``,
``metadata.py``, ``frequencies.py``, ``optimization.py``,
``energy_parameters.py``, ``optimization_parameters.py``,
``frequencies_parameters.py``, ``xtb.py``, ``__init__.py``,
``setup.py``, the data files, the installer) are unchanged.


Test plan after copying
========================

1. ``make lint && make install && make test`` -- still pass.
2. Open the Optimization step's edit dialog.  It should now open
   without a KeyError, and show two frames: the Hamiltonian
   Parameters frame at the top with the dynamic solvent visibility,
   and the Optimization frame below with optimization level / max
   iterations / structure handling.
3. Open the Frequencies step's edit dialog.  Three frames now:
   Hamiltonian, Optimization, Frequencies / Thermochemistry.
4. Re-run the water flowchart.  After the run, the Optimization step
   directory should contain ``xtbopt.xyz``, ``xtbopt.log``, and
   ``xtbtopo.mol`` in addition to the Phase E files.  The Frequencies
   step directory should additionally contain ``vibspectrum``,
   ``hessian``, and ``g98.out``.
5. The ``WARNING: xtbopt.xyz not found`` log messages from
   ``Optimization._handle_optimized_structure`` should now be silent
   for the optimization step (we have the file) and may still appear
   for the frequency step if xtb under ``--ohess`` writes the
   optimized geometry to a different filename.  If the latter persists,
   check what filename xtb actually used (likely ``xtbopt.xyz`` still
   -- ``--ohess`` is just opt + hess in one invocation -- but worth
   confirming).


Code style
==========

All four files compile cleanly, all lines <= 88 chars.  The diffs
against the previous phase are minimal (a 4-line block removed in
each tk_*.py, a 9-line list extension in energy.py).
