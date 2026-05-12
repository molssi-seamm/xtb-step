=======
Methods
=======

The plug-in exposes four Hamiltonians / force fields from the
xTB family. The ``xTB method`` parameter is shared by all
sub-steps.

Choosing among the GFN family
=============================

GFN2-xTB (default)
------------------

The recommended general-purpose method. Self-consistent with
multipole electrostatics (up to quadrupoles on each atom) and a
density-dependent dispersion correction (D4 family). Parametrized
for Z = 1-86.

GFN2-xTB is the right starting point for almost everything: organic,
inorganic, organometallic, and main-group systems. It is the most
accurate of the GFN methods for structures, conformer energies, and
non-covalent interactions, and is well-tested across a broad range
of benchmark sets.

Citation: Bannwarth, Ehlert, Grimme,
*J. Chem. Theory Comput.* **2019**, *15*, 1652.

GFN1-xTB
--------

The earlier self-consistent xTB Hamiltonian. Uses only
monopole-monopole electrostatics and a less elaborate dispersion
correction. Parametrized for Z = 1-86.

GFN1-xTB is typically less accurate than GFN2 for thermochemistry
but is sometimes more robust for difficult electronic-structure
cases (heavily strained systems, unusual oxidation states).
Useful when GFN2 fails to converge or gives implausible geometries.

Citation: Grimme, Bannwarth, Shushkov,
*J. Chem. Theory Comput.* **2017**, *13*, 1989.

GFN0-xTB
--------

A non-self-consistent (single-shot) method. Faster than GFN1/GFN2,
and very robust as a starting-point method or for very large
systems. Parametrized for Z = 1-86.

Best uses: rough screening of large libraries; getting a
reasonable starting geometry for a higher-level method; cases
where SCC convergence is unreliable.

Note that **GFN0-xTB is not parametrized for ALPB or GBSA
implicit solvation**. If you need implicit solvation with GFN0,
use CPCM-X. The plug-in will pass the combination to xtb regardless;
xtb itself will emit a warning or refuse to run.

Citation: Pracht, Caldeweyher, Ehlert, Grimme,
*ChemRxiv* **2019**, DOI 10.26434/chemrxiv.8326202.v1. (As of the
plug-in v1 release this paper has only a preprint; a peer-reviewed
version may appear later.)

GFN-FF
------

A generic, non-quantum force field automatically parametrized by
xTB from the structure. No SCC, no Hessian build-up of polarization
response.

GFN-FF is by far the fastest of the four and is intended for very
large systems (thousands of atoms) where even GFN0 is too slow,
and for MD or conformational sampling where a force field is
sufficient. Accuracy is markedly lower than the SCC GFN methods --
do not use GFN-FF for energy differences where you care about
precision under a kcal/mol.

Citation: Spicher, Grimme,
*Angew. Chem. Int. Ed.* **2020**, *59*, 15665.

Quick comparison
================

==============  ===========  ==========  ============================
Method          Type         Speed       Best for
==============  ===========  ==========  ============================
GFN-FF          Force field  Fastest     Very large systems, MD
GFN0-xTB        Non-SCC      Fast        Screening, starting point
GFN1-xTB        SCC          Moderate    Backup when GFN2 struggles
GFN2-xTB        SCC + D4     Moderate    General-purpose default
==============  ===========  ==========  ============================


Accuracy parameter
==================

The ``Accuracy`` field maps to xTB's ``--acc`` flag. Lower values
tighten the integral cutoffs and SCC convergence thresholds; higher
values loosen them. The default of 1.0 is appropriate for almost
all calculations. A typical usable range is roughly 0.0001 (very
tight) to 1000 (very loose, only for crude screening).

You generally do not need to change this. The main case where
tightening it helps is when you are about to do a
:doc:`Frequencies <frequencies>` calculation and want a tightly
converged starting geometry; the ``tight``/``vtight``/``extreme``
optimization levels already arrange for this.
