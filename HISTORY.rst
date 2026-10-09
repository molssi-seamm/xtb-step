=======
History
=======

2026.10.9 -- Bugfix: GFN2-xTB through tblite crashed
    * Any GFN2-xTB calculation through tblite (the MDI engine, as used by the Dimer
      Builder) crashed with a segmentation fault: tblite 0.6 and 0.7 need dftd4 4.2,
      and that combination fails in dftd4's polarizabilities. The environment now pins
      tblite-python 0.5.0 (dftd4 3.7), which works; with it the xtb program is 6.4.1.
      GFN1-xTB was not affected.

2026.5.2: Plug-in created using the SEAMM plug-in cookiecutter.

2026.5.12: Initial working version
    * Support for Energy, Optimization, and Frequencies
    * GFN0-xTB, GFN1-xTB, GFN2-xTB (the default), and GFN-FF supported
    * ALPB, GBSA, or CPCM-X implicit solvation
