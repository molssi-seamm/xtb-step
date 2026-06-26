.. _notes-xtb-mdi-engine:

==========================================================
xTB MDI engine -- drive LAMMPS MD with tblite over MDI
==========================================================

:Author: Paul Saxe (with Claude)
:Date: 2026-06-25
:Status: Implemented -- guard tests pass; end-to-end run pending
:Campaign: LAMMPS + MOPAC/xTB QM-MD via MDI

.. contents:: Contents
   :depth: 2
   :local:


Scope
=====

This is the **xTB side** of the QM-MD-over-MDI campaign -- the engine-side
mirror of MOPAC's Phase A. It lets a driver (``lammps_step``) run MD with
energies and forces from xTB (via the **tblite** library) over MDI, with **no
xTB-specific knowledge in the driver**.

The model-chemistry grammar and the LAMMPS consumer (Phase C) are
program-agnostic -- LAMMPS resolves the owning step from the stored
``_model_chemistry`` and calls ``get_mdi_engine_command`` on it -- so **nothing
in those needed to change**. xTB slots in purely by exposing the same contract
MOPAC does and shipping an engine script.

Delivered:

* ``xTBStep`` (the Stevedore entry-point helper) gains the MDI contract,
  mirroring ``MOPACStep``: ``_MDI_CAPABLE_METHODS``,
  ``_MDI_PERIODIC_VALIDATED``, ``get_model_chemistry_options``,
  ``get_executor_config``, ``get_mdi_engine_command``.
* ``data/tblite_mdi.py`` -- the engine, wrapping ``tblite.interface.Calculator``
  (shipped in the wheel, Option C, like ``mopac_mdi.py``).
* ``data/seamm-xtb.yml`` gains ``tblite-python`` + ``pymdi``.
* A method-set guard test (``tests/test_mdi_methods.py``).


What xTB advertises
===================

``xTBStep.get_model_chemistry_options()`` returns **level specs** keyed by bare
method name, e.g. ``xTB:SQM@GFN2-xTB`` (xTB is semiempirical QM -> type
``SQM``; owner ``xTB``). The MDI-drivable subset:

* ``_MDI_CAPABLE_METHODS = {GFN1-xTB, GFN2-xTB}``
* ``_MDI_PERIODIC_VALIDATED = {GFN1-xTB, GFN2-xTB}`` (both run periodic --
  tblite returns the virial, from which the engine forms the stress).

``GFN0-xTB`` and ``GFN-FF`` remain reachable only through the ordinary
xtb-binary path, not via MDI (the tblite Python ``Calculator`` does not cover
them). The composed result label a LAMMPS MD run records is therefore
``LAMMPS:MD|xTB:SQM@GFN2-xTB``.


How it differs from the MOPAC engine
====================================

The contract is identical, but the tblite engine differs from ``mopac_mdi.py``
in a few concrete ways, all handled here:

.. list-table::
   :header-rows: 1
   :widths: 16 40 44

   * - Aspect
     - MOPAC (mopac_mdi.py)
     - xTB (tblite_mdi.py)
   * - Bootstrap
     - no input file; structure comes entirely from the MDI handshake
     - reads ``structure.dat`` (the LAMMPS data file) up front to build the
       Calculator
   * - Element map
     - ``>ELEMENTS`` over MDI (or ``--elements`` fallback)
     - from the ``fix ... mdi/qm ... elements`` line in ``input.dat``
   * - Spin input
     - ``--multiplicity`` (2S+1)
     - ``--uhf`` (unpaired electrons = multiplicity - 1)
   * - Units
     - kcal/mol, Angstrom -> convert
     - Bohr / Hartree natively = MDI units; no conversion
   * - Method set
     - engine == advertised set
     - engine also accepts ``IPEA1-xTB`` (not advertised)

**Why a structure file.** tblite's ``Calculator`` needs the atomic numbers and
initial geometry at construction, before the MDI loop. Rather than defer
construction until the handshake (as MOPAC does), the engine reads the
``structure.dat`` the driver already writes, and derives the per-type element
symbols from the ``elements`` keyword on the ``fix mdi/qm`` line in
``input.dat``. Both files already exist in the run directory, so **no element
list is threaded through** ``get_mdi_engine_command`` -- keeping the contract
identical to MOPAC's and avoiding any ripple into ``mopac_step`` or Phase C.
(A future refactor could defer Calculator construction and drop the file
dependence entirely, matching MOPAC; not needed for the thin line.)


Engine launch
=============

``get_mdi_engine_command`` builds (rendered into the driver's launch script
with ``shlex.join``)::

    <conda> run --live-stream -n seamm-xtb python <abs>/tblite_mdi.py
        -mdi "-role ENGINE -name TBLITE -method TCP -port <port> -hostname <host>"
        --structure structure.dat --method GFN2-xTB --charge <q> --uhf <2S>
        --verbosity 1

The engine runs in **seamm-xtb** (``tblite-python`` + ``pymdi`` added to
``seamm-xtb.yml``); ``conda run`` keeps it in its own environment while the
LAMMPS driver stays in seamm-lammps, meeting over TCP -- exactly the MOPAC
split. Non-conda installations raise ``NotImplementedError`` for now.


Open / to verify
================

* **End-to-end run** through the SEAMM GUI (Model Chemistry -> LAMMPS) once
  ``seamm-xtb`` has ``tblite-python``/``pymdi`` installed; the standalone engine
  is already validated (NVT/NPT/stress decks in ``~/Work/tblite-mdi``).
* **Package name** ``tblite-python`` is what provides ``from tblite.interface
  import Calculator`` on conda-forge; adjust if your channel differs.
* **IPEA1-xTB** could be advertised too (add it to ``metadata.py`` and
  ``_MDI_CAPABLE_METHODS``); left out for now as it is not in xtb_step's
  computational-models metadata.


References
==========

* MOPAC engine (the template): ``mopac_step/data/mopac_mdi.py`` and
  ``mopac_step.py`` (``get_mdi_engine_command`` etc.).
* Model-chemistry grammar / naming: ``molssi-seamm.github.io`` ::
  ``background/model_chemistry_naming.rst``.
* LAMMPS consumer (Phase C): ``lammps_step`` ::
  ``campaigns/2026-06-22/NOTES_C.rst``.
* Working standalone engine + test decks: ``~/Work/tblite-mdi/``.
