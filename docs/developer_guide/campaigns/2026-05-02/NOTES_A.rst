==================================
xtb_step Phase A -- File Drop Notes
==================================

This drop fixes the two cookiecutter-template issues identified in the
review and bootstraps the ``data/`` directory.  No real plug-in
functionality yet -- that is Phase B.

Everything here is meant to be copied into your local ``xtb_step``
working tree at the same relative paths.  After copying:

::

    make lint
    make install
    make test

should all still pass -- this drop does not break anything and does
not add functionality, only foundation.


File-by-file
============

Modified files (replace existing)
---------------------------------

``xtb_step/xtb.py``
    Two changes only:

    1. ``pkg_resources`` import and ``Path(pkg_resources.resource_filename(...))``
       replaced with ``importlib.resources.files("xtb_step") / "data"``.
       ``from pathlib import Path`` was used only for that one wrapping
       and has been removed.
    2. The ``run()`` method body has been replaced.  The cookiecutter
       generated the LAMMPS/MOPAC-style "build a single ``molssi.dat``
       from ``node.get_input()`` and run the binary once" template,
       which is wrong for xtb -- xtb does one task per invocation.
       The new ``run()`` follows the FHI-aims pattern: iterate the
       subflowchart and let each substep call its own ``run()``.

    Everything else (``description_text``, ``analyze``, ``set_id``,
    docstrings, namespace, group) is unchanged from the cookiecutter.

``xtb_step/energy.py``, ``xtb_step/optimization.py``, ``xtb_step/frequencies.py``
    One change only in each: ``pkg_resources`` -> ``importlib.resources``
    in the property-loader at the top of the file.  Class bodies,
    placeholder ``time`` parameter, and the cookiecutter-generated
    ``run()`` and ``analyze()`` are all left alone.  These three files
    will get their real content in Phase B.


New files
---------

``xtb_step/substep.py``
    Base class for all substeps (Energy, Optimization, Frequencies, and
    any future MD/metadynamics/etc. substep).  Holds the genuinely
    common machinery:

    * ``check_periodicity(configuration)`` -- prints a clear message
      via the step printer and raises ``RuntimeError`` for periodic
      input.
    * ``write_coord_xyz(directory, configuration)`` -- writes the
      ``coord.xyz`` file consumed by xtb.
    * ``run_xtb(args, return_files, env)`` -- invokes xtb via the SEAMM
      executor, reading the per-plug-in ``xtb.ini`` from the SEAMM root
      directory and falling back to the bundled ``data/xtb.ini``
      template if the user's does not yet exist.
    * ``read_xtbout_json(directory, filename)`` -- best-effort parse of
      the JSON output produced by ``--json``.

    Phase B will switch ``Energy``, ``Optimization``, and ``Frequencies``
    over to inherit from ``Substep``.  The class is not imported in
    ``__init__.py`` since users do not instantiate it directly.

``xtb_step/data/seamm-xtb.yml``
    Conda environment file for the auto-installer.  Pulls Python and
    xtb from conda-forge.  *Verify before using:* the conda-forge xtb
    package name -- check with ``conda search -c conda-forge xtb``.

``xtb_step/data/xtb.ini``
    Default ini configuration template, modeled on ``dftbplus.ini``
    since DFTB+ is also conda-default from conda-forge.  Sections:
    ``[docker]`` and ``[local]``, with ``installation = conda`` and
    ``conda-environment = seamm-xtb`` as the defaults.  The seamm
    installer would normally copy this file (or write a customized
    version) into the user's SEAMM root directory.

``xtb_step/data/properties.csv``
    Replaces the empty stub.  Thirteen v1 seed properties using the
    ``<name>#xTB#{model}`` naming convention from ``mopac_step``.
    ``{model}`` is filled in with the active method (e.g. ``GFN2-xTB``)
    at runtime.

``xtb_step/data/references.bib``
    Extends the cookiecutter stub.  The auto-generated self-cite has
    its title fixed to ``xTB plug-in for SEAMM`` (was ``Xtb``) and a
    realistic organization/address.  Six new BibTex entries for the
    xTB method family:

    * ``Bannwarth2021`` -- general xTB review (cite at level 1 always)
    * ``Bannwarth2019`` -- GFN2-xTB
    * ``Grimme2017``    -- GFN1-xTB
    * ``Pracht2019``    -- GFN0-xTB (ChemRxiv preprint -- no journal paper as of v1)
    * ``Spicher2020``   -- GFN-FF
    * ``Ehlert2021``    -- ALPB / GBSA solvation


Not changed
===========

``setup.py``, ``setup.cfg``, ``__init__.py``, the three ``*_step.py``
helper classes for stevedore, the three ``tk_*.py`` GUI classes,
``metadata.py``, and the three ``*_parameters.py`` files are unchanged.
The entry points in ``setup.py`` are already correctly wired for all
four classes.

``metadata.py`` will be filled in during Phase B (it currently has
example commented-out blocks but no live ``metadata["results"]``
dictionary).


What to expect after copying
============================

After ``make install`` the package will import cleanly with no
``DeprecationWarning`` from ``pkg_resources``, the ``data/`` directory
will be on disk for ``importlib.resources`` to find, and the top-level
``xTB`` step's ``run()`` will iterate substeps correctly.  But the
substeps themselves still do nothing useful -- each one prints its
parameters and calls a placeholder ``analyze()``.  That is what
Phase B fixes.
