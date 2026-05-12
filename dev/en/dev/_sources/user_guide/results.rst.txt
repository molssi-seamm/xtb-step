=======
Results
=======

This page lists every result the plug-in extracts from an xTB run,
its units, the calculation types that produce it, and the SEAMM
database property name (where applicable).

All scalar property names follow the SEAMM convention
``<name>#xTB#{model}``, where ``{model}`` is the active xTB
Hamiltonian (e.g. ``GFN2-xTB``). For example, the GFN2-xTB total
energy is stored under ``total energy#xTB#GFN2-xTB``.

Energies and orbital quantities
===============================

Produced by **Energy**, **Optimization**, and **Frequencies**.

+----------------------------+------------------+---------------------------------------+
| Quantity                   | Units            | Property name                         |
+============================+==================+=======================================+
| Total energy               | E\ :sub:`h`      | ``total energy#xTB#{model}``          |
+----------------------------+------------------+---------------------------------------+
| Electronic energy          | E\ :sub:`h`      | ``electronic energy#xTB#{model}``     |
+----------------------------+------------------+---------------------------------------+
| HOMO energy [#orb]_        | eV               | ``HOMO energy#xTB#{model}``           |
+----------------------------+------------------+---------------------------------------+
| LUMO energy [#orb]_        | eV               | ``LUMO energy#xTB#{model}``           |
+----------------------------+------------------+---------------------------------------+
| HOMO-LUMO gap              | eV               | ``band gap#xTB#{model}``              |
+----------------------------+------------------+---------------------------------------+
| Dipole moment (magnitude)  | debye            | ``dipole moment#xTB#{model}``         |
+----------------------------+------------------+---------------------------------------+
| Dipole vector              | debye            | *(in variables/tables, not in db)*    |
+----------------------------+------------------+---------------------------------------+
| Partial charges            | e                | *(in variables/tables, not in db)*    |
+----------------------------+------------------+---------------------------------------+
| Gradients                  | E\ :sub:`h`/Å    | ``gradients#xTB#{model}``             |
+----------------------------+------------------+---------------------------------------+

.. [#orb] xTB reports the HOMO/LUMO orbital eigenvalues only for
   self-consistent methods (GFN1, GFN2). For GFN0 and GFN-FF these
   may be absent.

Vibrational and thermochemistry quantities
==========================================

Produced by **Frequencies** only.

+----------------------------+------------------+---------------------------------------+
| Quantity                   | Units            | Property name                         |
+============================+==================+=======================================+
| Vibrational frequencies    | cm\ :sup:`-1`    | *(in variables/tables)*               |
+----------------------------+------------------+---------------------------------------+
| IR intensities             | km/mol           | *(in variables/tables)*               |
+----------------------------+------------------+---------------------------------------+
| Reduced masses             | amu              | *(in variables/tables)*               |
+----------------------------+------------------+---------------------------------------+
| Force constants (Hessian)  | E\ :sub:`h`/Å²   | ``force constants#xTB#{model}``       |
+----------------------------+------------------+---------------------------------------+
| Zero-point energy          | kJ/mol           | ``zero point energy#xTB#{model}``     |
+----------------------------+------------------+---------------------------------------+
| Thermal enthalpy H(T)      | kJ/mol           | *(in variables/tables)*               |
+----------------------------+------------------+---------------------------------------+
| Entropic contribution T·S  | kJ/mol           | *(in variables/tables)*               |
+----------------------------+------------------+---------------------------------------+
| Entropy S                  | J/mol/K          | ``entropy#xTB#{model}``               |
+----------------------------+------------------+---------------------------------------+
| Gibbs free energy G(T)     | kJ/mol           | ``Gibbs free energy#xTB#{model}``     |
+----------------------------+------------------+---------------------------------------+
| Total free energy          | kJ/mol           | *(in variables/tables)*               |
+----------------------------+------------------+---------------------------------------+
| Temperature                | K                | *(in variables/tables)*               |
+----------------------------+------------------+---------------------------------------+

The thermochemistry block in xTB's output is reported natively in
E\ :sub:`h`. The plug-in converts ZPE, H, T·S, G, and the total
free energy to **kJ/mol** at parse time, which matches the
convention used in chemistry papers, in the standalone
``thermochemistry_step``, and in the ``gaussian_step`` /
``psi4_step`` analysis.

The entropy S is computed by the plug-in as T·S × 1000 / T (i.e.
divide xTB's T·S in kJ/mol by T and convert to J/mol/K). The
standard tabulated form S in J/mol/K is what you almost always want.

Where the data go
=================

For every property listed above:

1. The numeric value is shown in the results table printed to
   ``step.out`` for that sub-step.
2. The value is stored as a property of the current
   ``Configuration`` in the SEAMM database (for entries with a
   property name).
3. If you enabled "results" handling on the sub-step (the
   ``results`` tab in the edit dialog), the value is also
   accessible as a variable for downstream flowchart steps, or
   appended to a SEAMM table.

The raw xTB files are also preserved in the sub-step's work
directory: ``xtb.out``, ``xtbout.json``, ``coord.xyz``,
``xtbtopo.mol``, and (for Optimization) ``xtbopt.xyz`` /
``xtbopt.log``, and (for Frequencies) ``vibspectrum`` / ``hessian``
/ ``g98.out``.
