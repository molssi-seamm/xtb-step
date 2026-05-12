.. _user-guide:

**********
User Guide
**********

The xTB plug-in lets a SEAMM flowchart drive the `xTB
<https://github.com/grimme-lab/xtb>`_ family of extended tight-binding
methods from the Grimme group. It is a fast, robust route to
single-point energies, geometry optimizations, and harmonic
vibrational frequencies for molecular (non-periodic) systems, with
optional implicit solvation.

The plug-in is a *container step* with a subflowchart of *sub-steps*.
You add the top-level ``xTB`` step to your flowchart, then open it
and add one or more sub-steps inside it. Three sub-steps are
available in this release:

* :doc:`Energy <energy>` -- a single-point energy at a fixed geometry.
* :doc:`Optimization <optimization>` -- minimize the geometry with
  xTB's ANC (approximate normal coordinate) optimizer.
* :doc:`Frequencies <frequencies>` -- compute the analytic Hessian
  (optionally after a geometry optimization) and report harmonic
  vibrational frequencies, IR intensities, and thermochemistry.

The Hamiltonian, accuracy, and solvation settings are common to all
three sub-steps and are described in:

* :doc:`Methods <methods>` -- choosing between GFN0-xTB, GFN1-xTB,
  GFN2-xTB (the default), and GFN-FF.
* :doc:`Solvation <solvation>` -- using ALPB, GBSA, or CPCM-X implicit
  solvation, and the supported solvent list.

A summary of the properties produced and where they end up:

* :doc:`Results <results>` -- the table of energies, orbital energies,
  dipole moment, vibrational data, and thermochemistry quantities,
  with their units and how they are stored in the SEAMM property
  database.

A note on charge and spin
-------------------------

Net charge and spin multiplicity are **not** parameters of the
sub-steps. They are properties of the *configuration* (the SEAMM
data model treats O\ :sub:`2`, triplet O\ :sub:`2`, and
O\ :sub:`2`\ :sup:`+` as different chemical species).  Set them
when you build the structure -- e.g. in ``From SMILES`` or
``From Structure`` -- and every downstream xTB step will pick them up
automatically.  This is what makes loops over systems with different
charge/spin states trivial.

Contents
========

.. toctree::
   :maxdepth: 2
   :titlesonly:

   energy
   optimization
   frequencies
   methods
   solvation
   results

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
