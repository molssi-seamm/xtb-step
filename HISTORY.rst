=======
History
=======

2026.11.26 -- Bugfix: the tblite MDI engine ignored SEAMM's conda wrapper
    * The engine was launched with the conda named in xtb.ini, while SEAMM's local
      executor prefers CONDA_EXE. On clusters CONDA_EXE is SEAMM's wrapper that unpacks
      an environment kept as an archive onto the node, so an archive-only seamm-tblite
      could not start ("MDI engine exited (return code 1) before connecting"; ARC,
      SEAMM job 6088). The engine now uses the same conda as the executor: CONDA_EXE,
      else the ini's, and a prefix (-p) for an environment given as a path.

2026.11.21.1 -- Bugfix: the installer bypassed SEAMM's environment policies
    * 2026.11.21's installer made the two conda environments itself, which skipped the
      installation's policies: shared or prefixed code environments, environments kept
      as archives (as on clusters with slow shared file systems), and the guard against
      replacing an environment SEAMM did not make. It now leaves ``seamm-xtb`` to the
      standard installer and makes ``seamm-tblite`` the same way, as a directory or an
      archive as the installation keeps them. A ``seamm-xtb`` directory that still holds
      tblite from before 2026.11.21 is removed first, so it is made again from the new
      environment file.

2026.11.21 -- Bugfix: xTB optimisations crashed, and failures went unnoticed
    * Geometry optimisations failed after the first cycle with the conda-forge
      environment as it now resolves: xtb 6.4.1, which the tblite 0.5.0 pin forced
      into the environment, stops with "Fortran runtime error: Missing comma between
      descriptors" under the gfortran 16 runtime. The xtb executable now has its own
      environment, ``seamm-xtb``, with xtb 6.7.1, and the tblite MDI engine has
      ``seamm-tblite`` with tblite 0.5.0 (tblite 0.6 with dftd4 4.2 still crashes
      for GFN2). Updating the plug-in's installation recreates ``seamm-xtb`` and
      creates ``seamm-tblite``, and records it as ``tblite-environment`` in xtb.ini;
      until then the engine keeps using ``conda-environment``.
    * When xtb fails -- a non-zero exit, no ``xtbout.json``, or no energy -- the step
      now stops with an error naming the directory and quoting the end of xtb's error
      output. Before, it printed "No results were collected" and carried on, so a Loop
      of failed calculations finished with no errors counted.

2026.11.11 -- Settings fingerprints for xTB's model-chemistry calculations
    * Calculations through an xTB **Model Chemistry** (e.g. ``xTB:SQM@GFN2-xTB``) now
      carry a fingerprint of their settings -- the program and its version, the method
      and the accuracy -- like the other codes' calculations. Steps that reuse results,
      such as **Thermochemistry** with its fragment store, can then tell which stored
      xTB results match the calculation they need.
    * Needs seamm-mdi 2026.11.11 or later for the fingerprints; with an older
      seamm-mdi, xTB calculations work as before, without them.

2026.11.5 -- Tight convergence on request for finite differences
    * Steps that take finite differences of xTB's gradients over its MDI engine, such
      as the new Vibrational Analysis step, can now ask for tight convergence: every
      calculation then runs at accuracy 1e-4. The engine starts each SCF from the
      previous structure's, and at the default accuracy that left noise depending on
      the previous structure (water's anharmonic force constants: 92 cm^-1 of noise,
      0.12 with the tighter accuracy).
    * The MDI engine takes an ``--accuracy`` option.

2026.10.20 -- Bugfix: an SCF that did not converge ended the MDI engine
    * In the tblite MDI engine (used e.g. by the Dimer Builder), one structure whose
      SCF did not converge ended the engine, and with it the whole step. A failed SCF
      is now retried from a fresh start, then with more iterations and stronger
      damping, then from another starting guess -- none of which changes the
      converged energy. If none converges, the engine returns NaN for that structure
      and carries on, so the step can leave the point out. For Li+ with ethylene
      carbonate the failures were at large separations, 7-9 Å, and the retries
      converged them.


2026.10.9 -- Bugfix: GFN2-xTB through tblite crashed
    * Any GFN2-xTB calculation through tblite (the MDI engine, as used by the Dimer
      Builder) crashed with a segmentation fault: tblite 0.6 and 0.7 need dftd4 4.2,
      and that combination fails in dftd4's polarizabilities. The environment now pins
      tblite-python 0.5.0 (dftd4 3.7), which works; with it the xtb program is 6.4.1.
      GFN1-xTB was not affected.
    * Internal: requires Python 3.12; CI installs with uv from PyPI (no conda test
      environment); the unused Docker installation option was removed.

2026.5.2: Plug-in created using the SEAMM plug-in cookiecutter.

2026.5.12: Initial working version
    * Support for Energy, Optimization, and Frequencies
    * GFN0-xTB, GFN1-xTB, GFN2-xTB (the default), and GFN-FF supported
    * ALPB, GBSA, or CPCM-X implicit solvation
