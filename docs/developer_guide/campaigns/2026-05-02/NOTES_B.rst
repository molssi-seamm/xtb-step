==================================
xtb_step Phase B -- File Drop Notes
==================================

This drop fills in the actual xTB-running functionality. After installing
this on top of Phase A, the three substeps should produce real results
when added to a flowchart and given a molecule.

Everything here is meant to overwrite the corresponding files in your
local ``xtb_step`` working tree. ``__init__.py``, ``setup.py``,
``setup.cfg``, the three ``*_step.py`` helper classes, and the four
``tk_*.py`` GUI classes are unchanged from Phase A and do not need to
be touched. The data files (``data/properties.csv``,
``data/references.bib``, ``data/seamm-xtb.yml``, ``data/xtb.ini``) are
also unchanged from Phase A.


Files in this drop
==================

Replace existing
----------------

``xtb_step/substep.py``
    Big upgrade. Adds module-level constants for the method <-> CLI flag
    map (``METHODS``, ``METHOD_TO_CLI``), solvation-model and solvent
    lists (``SOLVATION_MODELS``, ``SOLVENTS_GBSA_ALPB``,
    ``SOLVENTS_CPCMX``), and a CLI builder ``base_xtb_args(P,
    configuration)`` that all substeps share. Adds ``parse_thermo_block()``
    for the Hessian thermochemistry table. Phase A's
    ``check_periodicity()``, ``write_coord_xyz()``, ``run_xtb()``, and
    ``read_xtbout_json()`` are unchanged.

``xtb_step/metadata.py``
    Replaces the cookiecutter placeholder. Defines
    ``metadata["computational models"]`` (GFN0/1/2/FF, all flagged
    ``periodic: False``) and ``metadata["results"]`` with 17 entries
    covering total/electronic energy, gap, HOMO/LUMO, dipole (vector +
    magnitude), partial charges, gradients, frequencies, IR
    intensities, reduced masses, and the thermochemistry quantities.
    Property names use the ``<name>#xTB#{model}`` convention; ``{model}``
    is filled in at storage time by SEAMM's ``store_results()``.

``xtb_step/energy_parameters.py``
    Replaces the placeholder ``time`` parameter with the real ones:
    ``method`` (enum: GFN2-xTB default), ``charge``, ``multiplicity``,
    ``accuracy``, ``solvation model``, ``solvent``, plus the standard
    ``results`` dictionary. Used as the base class for
    ``OptimizationParameters`` and (via ``OptimizationParameters``)
    ``FrequenciesParameters``.

``xtb_step/optimization_parameters.py``
    Inherits from ``EnergyParameters``. Adds ``optimization level``
    (crude/sloppy/loose/lax/normal/tight/vtight/extreme),
    ``max iterations``, and ``structure handling`` (overwrite / new
    config / new system / discard).

``xtb_step/frequencies_parameters.py``
    Inherits from ``OptimizationParameters``. Adds ``optimize first``
    (yes/no -- selects ``--ohess`` vs ``--hess``), ``temperature``,
    ``pressure``.

``xtb_step/energy.py``
    Now inherits from ``Substep``. ``run()`` writes ``coord.xyz``, calls
    ``check_periodicity()``, builds the xtb command line via
    ``base_xtb_args()``, calls ``run_xtb()``, parses ``xtbout.json``,
    populates a results dict matching ``metadata["results"]``, and calls
    ``store_results()``. Citations are added to the references handler
    based on which method and solvation model were chosen. Defensive
    parsing -- missing JSON keys are skipped, not errors.

``xtb_step/optimization.py``
    Inherits from ``Energy``. ``run()`` injects ``--opt LEVEL`` and
    delegates to ``Energy.run()``. Post-run, picks up ``xtbopt.xyz`` and
    applies it according to the user's ``structure handling`` choice.

``xtb_step/frequencies.py``
    Inherits from ``Optimization``. ``run()`` injects ``--ohess LEVEL``
    or ``--hess`` (depending on ``optimize first``), bypasses
    ``Optimization.run()`` to avoid double ``--opt`` insertion, and
    calls ``Energy.run()`` directly. Post-run, parses the ``::
    THERMODYNAMIC ::`` block from ``xtb.out`` and the JSON / vibspectrum
    frequencies.


Not changed since Phase A
-------------------------

``xtb_step/__init__.py``, ``xtb_step/xtb.py``,
``xtb_step/xtb_step.py``, ``xtb_step/energy_step.py``,
``xtb_step/optimization_step.py``, ``xtb_step/frequencies_step.py``,
``xtb_step/tk_*.py``, all of ``xtb_step/data/``.


What to test after copying
==========================

1. ``make lint && make install && make test`` -- should still pass.
   Imports change but the public API (the four classes exported from
   ``__init__``) does not.

2. Open SEAMM, build a flowchart with FromSMILES -> xTB. Inside the
   xTB step add an Energy substep. Edit Energy: you should see the
   real parameters (method, charge, multiplicity, accuracy, solvation
   model, solvent), with sensible defaults.

3. Run the flowchart on something simple (water, methane). On a
   working ``conda install -c conda-forge xtb``, you should get
   ``xtb.out``, ``xtbout.json``, and a populated SEAMM properties
   database with at least ``total energy#xTB#GFN2-xTB`` and
   ``band gap#xTB#GFN2-xTB``.

4. Optimization on the same molecule should additionally produce
   ``xtbopt.xyz`` and update the configuration's coordinates.

5. Frequencies should additionally produce ``vibspectrum``, ``hessian``,
   ``g98.out``, plus thermo quantities in the database.


Known unknowns and likely failure points
========================================

I have NOT been able to test any of this against a running xtb or a
running SEAMM, so the following are my best guesses based on the docs
and the FHI-aims / MOPAC analogs. Things most likely to need fixing:

1. **Executor invocation.** ``substep.py:run_xtb()`` mirrors the
   FHI-aims pattern (``self.parent.flowchart.executor``,
   ``self.global_options``, ``executor.run(cmd=..., config=..., ...)``)
   but I haven't run it. If it fails with an ``AttributeError`` on
   ``executor`` or ``global_options``, that is the place to look.
   The likely culprit is whether the executor accepts ``files={}`` or
   wants the input files written by us into ``self.directory`` first
   (which the code does -- ``write_coord_xyz()`` writes ``coord.xyz``
   directly into ``self.directory`` before the call).

2. **xtbout.json key names.** The xTB docs show keys like
   ``"HOMO-LUMO gap / eV"`` (with spaces around the ``/``), but I have
   seen alternative spellings in older versions (``"HOMO-LUMO gap/eV"``,
   no spaces). The parser tries both. If your installed xtb uses yet
   another spelling for some quantity, expect that quantity to be
   missing from the results dict and add the alias to
   ``Energy._harvest_json``.

3. **Dipole-vector storage.** I'm storing both the 3-component
   ``dipole_vector`` and the scalar ``dipole_moment`` (magnitude) in
   the data dict. ``metadata["results"]`` declares ``dipole_vector``
   as ``[3]`` dimensional but does NOT give it a property name (so it
   is variable/table only, not stored as a database property).
   ``dipole_moment`` IS stored as a property. If you'd rather only one
   or the other, drop the unwanted entry from both ``metadata.py`` and
   ``Energy._harvest_json``.

4. **Configuration XYZ I/O.** ``write_coord_xyz()`` checks for
   ``configuration.to_xyz_text()`` and falls back to a hand-built XYZ.
   ``Optimization._handle_optimized_structure()`` checks for
   ``configuration.from_xyz_text()`` and falls back to manual parsing.
   I'm not 100% certain those methods exist in the molsystem version
   you're using; the fallback paths should work either way.

5. **Multiple-method runs and ``self._model``.** ``self._model`` is set
   inside ``Energy.run()`` from ``P["method"]`` before
   ``store_results()`` is called. SEAMM's ``store_results()`` uses
   ``self.model`` (which is exposed by ``seamm.Node``) to format
   property names like ``"total energy#xTB#{model}"``. I'm assuming the
   ``self._model = ...`` assignment is what ``self.model`` reads. The
   FHI-aims code does the same thing. If property names come out as
   ``"...#xTB#"`` (empty model) or ``"...#xTB#{model}"`` (literal
   ``{model}``), the assignment isn't being picked up and we'll need
   to add a property override.

6. **Inheritance trick in ``Optimization`` and ``Frequencies``
   ``__init__``.** Because ``Energy.__init__`` sets
   ``self.parameters = xtb_step.EnergyParameters()`` and we want
   ``OptimizationParameters`` instead, the subclasses use ``super(Energy,
   self).__init__(...)`` to skip Energy and call Substep directly. This
   is correct Python but if it confuses ``seamm.Node`` (which expects
   to be initialized through a particular path), we may need to
   refactor. The cleanest alternative is to keep
   ``Energy.__init__`` parameter-agnostic and have each subclass
   instantiate its own parameters after calling ``super().__init__()``.

7. **Thermochemistry temperature.** v1 only supports xtb's default
   298.15 K. The parameter is exposed (``temperature``) and a warning
   is printed if a different value is requested, but xcontrol's
   ``$thermo`` block is not yet wired up. This is a known limitation
   to fix in v1.x.

8. **Solvent list completeness.** Pulled from the xTB docs at
   implementation time. May be missing solvents added in newer xtb
   releases; xtb itself will report unknown solvents at run time, and
   the user can also type a solvent name into the GUI as a free string
   (the parameter is an enumeration, but SEAMM enumerations don't
   strictly enforce membership).

9. **GFN-FF + solvation.** GFN-FF is force-field-based; ALPB is
   parametrized for it (per Spicher & Grimme 2020), but GBSA may not
   be. ``base_xtb_args()`` does not currently refuse GFN-FF + GBSA;
   xtb will error out with a clear message if it is unsupported.

10. **Where ``self.references`` is populated.** ``Energy._cite_references()``
    does ``self._bibliography["Bannwarth2021"]`` etc. The bibliography
    is loaded by ``seamm.Node`` from ``data/references.bib`` (Phase A),
    keyed by the BibTex citation key on the first line of each entry.
    The keys we use are ``Bannwarth2021``, ``Bannwarth2019``,
    ``Grimme2017``, ``Pracht2019``, ``Spicher2020``, ``Ehlert2021``,
    matching exactly what is in Phase A's ``references.bib``.


Code style
==========

All files compile cleanly. All lines are <= 88 characters (your
``setup.cfg``'s flake8 max-line-length). I have NOT been able to run
``black --check`` here, so there may be small whitespace adjustments
when you do ``make format`` for the first time -- those should be one
pass and then stable.
