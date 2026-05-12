============
Optimization
============

The ``Optimization`` sub-step minimizes the geometry using xTB's
ANC (approximate normal coordinate) optimizer. After the run the
optimized geometry is harvested from ``xtbopt.xyz`` and applied to
the SEAMM configuration according to your **Structure handling**
choice.

Dialog
======

The dialog has two panels.

Hamiltonian Parameters
----------------------

The same panel as in the :doc:`Energy <energy>` sub-step:
``xTB method``, ``Accuracy``, ``Implicit solvation``, and (when
solvation is on) ``Solvent``.

Optimization
------------

Optimization level
    The xTB ``--opt`` preset, in order of increasing convergence
    tightness: ``crude``, ``sloppy``, ``loose``, ``lax``, ``normal``
    (default), ``tight``, ``vtight``, ``extreme``. The presets set
    both the energy and the gradient convergence criteria.
    ``normal`` is appropriate for general use; use ``tight`` or
    tighter before a frequency calculation if you are not using the
    :doc:`Frequencies <frequencies>` sub-step's
    ``--ohess`` workflow.

Maximum iterations
    Maximum number of optimization iterations. Set to ``default``
    to let xTB decide based on system size, or enter an integer to
    override.

Optimized structure
    What to do with the optimized geometry:

    * **Overwrite the current configuration** (default) -- replace
      the coordinates of the input configuration in place. The
      input geometry is lost. Most common choice for a simple
      optimization step.
    * **Add a new configuration** -- keep the input geometry as a
      configuration of the system, and store the optimized geometry
      as a new configuration of the same system. Useful if you want
      to compare initial and optimized structures.
    * **Add a new system** -- store the optimized geometry as a
      configuration of a freshly created system.
    * **Discard the optimized structure** -- compute the optimized
      energy but throw the geometry away. Useful if you only want
      energetics and want to keep the input geometry sacred.

Output
======

The ``Optimization`` sub-step prints the same results table as the
:doc:`Energy <energy>` sub-step (total and electronic energy, gap,
dipole) but with values at the optimized geometry.

The work directory contains, in addition to the Energy files,
``xtbopt.xyz`` (the optimized geometry) and ``xtbopt.log`` (the
optimization trajectory in XMOL format -- each frame is one
optimization step).
