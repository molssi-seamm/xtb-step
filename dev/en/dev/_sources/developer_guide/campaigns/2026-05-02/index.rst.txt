2026-05-02 Initial development campaign
=======================================

Goal of v1
----------

Produce a SEAMM plug-in that lets a flowchart run xTB single-point energies, geometry optimizations, and vibrational frequencies (with the thermochemistry table that xTB prints alongside a Hessian run), for molecular systems, with optional implicit solvation, using xTB’s GFN0/GFN1/GFN2/GFN-FF methods. The plug-in installs xTB automatically via conda (seamm-xtb environment from conda-forge), integrates with the SEAMM property database, and fails gracefully on periodic input.

It is not intended to be production-grade or to expose every xTB option; subsequent releases will add MD, metadynamics, reaction-path, mode-following, and electronic-property workflows.

Contents:

.. toctree::
   :glob:
   :maxdepth: 2

   *scope*
   NOTES_*
