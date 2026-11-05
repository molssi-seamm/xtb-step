=======
History
=======
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
