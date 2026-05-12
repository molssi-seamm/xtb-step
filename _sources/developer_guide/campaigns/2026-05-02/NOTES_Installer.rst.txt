==========================================
xtb_step Installer Drop -- File Drop Notes
==========================================

This drop adds the two files needed for ``seamm-installer`` to find,
install, and version-check xtb. Both files go directly inside
``xtb_step/`` (not in ``data/``).


Files
=====

``xtb_step/installer.py``
    The ``Installer`` class. Subclasses
    ``seamm_installer.InstallerBase`` and overrides:

    * ``__init__`` -- sets the environment name (``seamm-xtb``), the
      ini section (``xtb-step``), the executables to look for
      (``["xtb"]``), and points at ``data/seamm-xtb.yml`` for the
      conda environment definition.
    * ``exe_version(config)`` -- runs ``conda run -n <env> xtb --version``
      and parses the output to extract the xtb version. Returns the
      ``("xTB", "<version>")`` tuple expected by the installer base
      class.

    Modeled directly on ``mopac_step/installer.py``. The only
    nontrivial difference is the version-line parser: MOPAC takes the
    third whitespace-separated token of the first non-empty line, but
    ``xtb --version`` prints a multi-line ASCII banner before the
    version line, so we anchor a regex on the literal ``"xtb version"``
    instead. Tested against the canonical formats documented in the
    xtb manual:

    * ``* xtb version 6.2.1 (bf8695d) compiled by ...`` -> ``6.2.1``
    * ``xtb version 6.7.0`` -> ``6.7.0``
    * ``* XTB Version 6.4.1 (abc1234)`` -> ``6.4.1`` (case-insensitive)

``xtb_step/__main__.py``
    Tiny shim: imports the ``Installer`` class and provides ``run()``
    so that ``python -m xtb_step`` invokes the installer. Identical
    structure to ``mopac_step/__main__.py`` and ``psi4_step/__main__.py``.


What this enables
=================

Once these are in place, the ``seamm-installer`` machinery can:

1. Detect that ``xtb-step`` is installed but xtb itself isn't.
2. Offer to create the ``seamm-xtb`` conda environment from
   ``data/seamm-xtb.yml`` (which is already in place from Phase A).
3. After installation, query ``xtb --version`` to confirm the
   executable works and record the version in the SEAMM dashboard.
4. Update ``~/SEAMM/xtb.ini`` so ``substep.run_xtb()`` can find the
   conda environment (the ``[local]`` section's ``conda`` and
   ``conda-environment`` keys).


Not changed
===========

``setup.py``, ``setup.cfg``, ``__init__.py``, all the substep modules
from Phase B, and all data files from Phase A are untouched. The
installer is discovered by ``seamm-installer`` simply by being a
module called ``installer`` inside ``xtb_step``; no setup.py entry
point is required.


Testing it
==========

After ``make install``:

::

    python -m xtb_step

This should run the installer interactively. From a fresh checkout
without an existing ``seamm-xtb`` environment, it should offer to
create one. After successful install, re-running it should report the
version (e.g. ``xTB 6.7.1``).

If you have ``xtb`` already on your ``$PATH`` (e.g. from a previous
manual install), the installer should detect it and prompt to register
that location in ``xtb.ini`` instead of building a fresh conda env.


Risk register for this drop
===========================

1. **Conda invocation portability.** The ``conda run --live-stream``
   pattern is what mopac_step uses, so should work the same on
   macOS/Linux/Windows wherever mopac_step works. ``--live-stream``
   was added in conda 4.9; older conda versions will choke. Worth a
   line in the user-facing release notes.

2. **Version regex robustness.** I tested against three documented
   formats. If a future xtb release changes the banner layout, the
   regex will fall through to ``"unknown"`` -- the installer will
   still work, just won't display a version. Easy to fix.

3. **Conda-forge xtb package name.** The ``data/seamm-xtb.yml`` from
   Phase A specifies ``- xtb`` from ``conda-forge``. I haven't
   independently verified the package is named exactly ``xtb`` on
   conda-forge (vs. e.g. ``xtb-python``). Easy to confirm with
   ``conda search -c conda-forge xtb`` before first real install.
