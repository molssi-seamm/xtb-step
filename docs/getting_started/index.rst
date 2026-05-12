***************
Getting Started
***************

Installation
============

The xTB step is probably already installed in your SEAMM
environment, but if not, or if you wish to check, follow the
directions for the `SEAMM Installer`_. The graphical installer is
the easiest to use. In the SEAMM conda environment, simply type::

    seamm-installer

or use the shortcut if you installed one. Switch to the second tab,
``Components``, and check for ``xtb-step``. If it is not installed,
or can be updated, check the box next to it and click
``Install selected`` or ``Update selected`` as appropriate.

The non-graphical installer is also straightforward::

    seamm-installer install --update xtb-step

will ensure both that the SEAMM plug-in itself and the underlying
``xtb`` executable are installed and up-to-date. By default the
installer creates a dedicated ``seamm-xtb`` conda environment from
``conda-forge`` containing ``xtb``; on first use the plug-in writes
the environment location into ``~/SEAMM/xtb.ini`` so subsequent
runs can find it.

.. _SEAMM Installer: https://molssi-seamm.github.io/installation/index.html


A first calculation
===================

The simplest useful flowchart is **From SMILES → xTB → Energy**:

1. Add a ``From SMILES`` step and set the SMILES string to
   ``O`` (water) or any other small molecule.
2. Add an ``xTB`` step from the ``Simulations`` menu.
3. Open the ``xTB`` step (double-click) and inside the
   subflowchart add an ``Energy`` sub-step from the
   ``Calculations`` menu.
4. Submit the flowchart. After a moment you should see the
   energy in ``step.out`` for the Energy sub-step as a
   ``Property | Value | Units`` table.

To do a geometry optimization, replace ``Energy`` with
``Optimization`` (or chain the two: ``Energy`` then
``Optimization`` if you want to see the change in total energy on
relaxation). For vibrational frequencies and thermochemistry, use
``Frequencies``, which by default optimizes the geometry first.

Charge and spin
---------------

Net charge and spin multiplicity are properties of the
configuration, not parameters of the xTB step. Set them when you
build the structure -- in ``From SMILES``, ``From Structure``, or
``Read Structure``. The xTB step reads them automatically. This is
what makes loops over systems with different charge/spin states
trivial:

* O\ :sub:`2` (charge 0, multiplicity 3 -- triplet ground state)
* O\ :sub:`2`\ :sup:`+` (charge +1, multiplicity 2 -- doublet)
* O\ :sub:`2`\ :sup:`-` (charge -1, multiplicity 2 -- doublet)

are three different *configurations*; one xTB step can process all
three in a loop without any per-system parameter editing.

Implicit solvation
------------------

To run any of the sub-steps with implicit solvation, open the
sub-step's dialog, set ``Implicit solvation`` to ``ALPB`` (the
current xTB-recommended default) or ``CPCM-X`` (broader solvent
list), and choose a solvent. ``GFN2-xTB`` + ``ALPB`` + ``H2O`` is
the standard starting point for aqueous work.

That should be enough to get started. For more detail about the
functionality in this plug-in, see the :ref:`User Guide
<user-guide>`.
