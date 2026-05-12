======
Energy
======

The ``Energy`` sub-step runs a single xTB calculation at the current
geometry and reports the total and electronic energies, HOMO and LUMO
energies (when xTB provides them), the HOMO-LUMO gap, the dipole
moment, and the atomic partial charges.

It does not change the geometry.

Dialog
======

Opening the ``Energy`` sub-step shows a single panel labelled
**Hamiltonian Parameters** containing the following controls:

xTB method
    The Hamiltonian or force field to use. Defaults to
    ``GFN2-xTB``. See :doc:`Methods <methods>` for guidance on
    choosing among the GFN family.

Accuracy
    The xTB ``--acc`` multiplier. The default of 1.0 is appropriate
    for most calculations. Smaller values tighten integral and SCC
    convergence; larger values loosen them. Useful range is roughly
    0.0001 to 1000.

Implicit solvation
    The solvation model: ``none`` (default), ``ALPB``, ``GBSA``, or
    ``CPCM-X``. See :doc:`Solvation <solvation>` for details on each
    model and the supported solvents.

Solvent
    The solvent for implicit solvation. Hidden when the solvation
    model is ``none``. Visible (and indented) when a solvation model
    is selected. Defaults to ``H2O``.

Charge and spin multiplicity are read from the current configuration
and do **not** appear in the dialog. They are set when the structure
is built (e.g. in the ``From SMILES`` step).

Output
======

The ``Energy`` sub-step prints a results table to ``step.out`` like
the example below:

.. code-block:: text

                            xTB (GFN2-xTB) Results
        ╭─────────────────────────────────────────────────────┬───────────┬───────╮
        │                      Property                       │   Value   │ Units │
        ├─────────────────────────────────────────────────────┼───────────┼───────┤
        │                  The total energy                   │ -5.069275 │  E_h  │
        │ The electronic energy (excluding nuclear repulsion) │ -5.096007 │  E_h  │
        │                  The HOMO-LUMO gap                  │ 13.1714   │  eV   │
        │        The molecular dipole moment magnitude        │  2.2109   │ debye │
        ╰─────────────────────────────────────────────────────┴───────────┴───────╯

The same quantities are stored as properties of the configuration in
the SEAMM database, under names like
``total energy#xTB#GFN2-xTB`` (the model is substituted at run
time). See :doc:`Results <results>` for the full list.

The work directory for the sub-step also contains the raw xTB files:
``coord.xyz`` (input), ``xtb.out`` (full xTB output), ``xtbout.json``
(structured output), ``xtbtopo.mol`` (topology), and ``xtbrestart``
(restart file).
