===================================
xtb_step Phase I -- File Drop Notes
===================================

Documentation pass for the plug-in as it stands today.  Filled out
the placeholder text in:

* ``README.rst`` -- the **Features** section.  All other content
  (title, badges, license, acknowledgements) preserved verbatim.
* ``docs/index.rst`` -- replaced the "xTB <does what? replace this
  text>" placeholder with a real one-paragraph intro, and fixed
  the "Geometry Analysis Step" typo in the API card.
* ``docs/getting_started/index.rst`` -- replaced the "Replace this!"
  example placeholder with a real "first calculation" walkthrough.
* ``docs/user_guide/index.rst`` -- replaced the commented-out
  placeholder toctree with a real intro plus an explicit toctree
  pointing to the new topic files.

Plus six new files in ``docs/user_guide/`` covering one topic each.


Files in this drop
==================

Replace existing
----------------

``README.rst``
    Features section filled in.  Covers:

    * Single-point, optimization, frequencies for molecular systems
    * GFN0/1/2-xTB and GFN-FF
    * ALPB / GBSA / CPCM-X implicit solvation with the supported
      solvent list
    * Charge and spin read from the configuration (with O\ :sub:`2`
      / O\ :sub:`2`\ :sup:`+` example)
    * Optimization with eight convergence levels and four
      structure-handling modes
    * Frequencies with thermochemistry in kJ/mol and J/mol/K
    * Tabulated step.out results and automatic property-database
      storage
    * Automatic citation tracking (Bannwarth, Ehlert, Caldeweyher,
      Stahn etc.)
    * Automatic installer

``docs/index.rst``
    One-paragraph intro replacing the placeholder.  "API Reference"
    card text corrected.

``docs/getting_started/index.rst``
    "First calculation" section with a From SMILES → xTB → Energy
    walkthrough, a note on charge/spin coming from the configuration,
    and a one-line pointer for implicit solvation.  Installation
    section preserved as-is from the cookiecutter.

``docs/user_guide/index.rst``
    Real intro paragraph describing the container-step /
    subflowchart pattern.  Mentions the three substeps and the two
    cross-cutting topics (Methods, Solvation).  Includes a
    prominent "note on charge and spin" block.  Toctree exposed
    (no longer hidden behind the cookiecutter's ``..`` commented
    block) and pointing at the six topic files.


New files
---------

``docs/user_guide/energy.rst``
    Energy substep: dialog walkthrough, sample results table,
    pointer to the raw xtb files in the work directory.

``docs/user_guide/optimization.rst``
    Two-panel dialog (Hamiltonian + Optimization).  Documents the
    eight optimization levels and the four structure-handling modes.

``docs/user_guide/frequencies.rst``
    Three-panel dialog (Hamiltonian + Optimization + Frequencies).
    Documents optimize-first toggle, temperature/pressure caveats,
    sample results table with thermochemistry, and the imaginary-
    frequency convention.

``docs/user_guide/methods.rst``
    Guidance on choosing among GFN0, GFN1, GFN2, and GFN-FF.
    Comparison table; honest notes on accuracy/speed/use-cases.
    Notes the GFN0 + ALPB/GBSA incompatibility.

``docs/user_guide/solvation.rst``
    The three solvation models with their citations.  Supported
    solvent list with method-specific caveats (DMF/n-hexane GFN2-
    only, benzene GFN1-only).  Notes the dynamic-dialog behavior.

``docs/user_guide/results.rst``
    Two grid tables (energies/orbitals, vibrational/thermo) listing
    every result with its units and SEAMM property name.  Notes on
    the kJ/mol unit conversion and the derived ``entropy`` quantity.
    Description of where data go (step.out, property database,
    variables/tables).


Not touched
===========

``AUTHORS.rst``, ``CONTRIBUTING.rst``, ``HISTORY.rst``,
``docs/api/index.rst``, ``docs/authors.rst``, ``docs/history.rst``,
``docs/developer_guide/`` and everything under it (campaign notes,
contributing.rst, installation.rst, usage.rst) are unchanged.


On the ``docs/developer_guide/campaigns/`` structure
=====================================================

You mentioned wanting to add the campaigns directory structure to
the SEAMM cookiecutter.  For the cookiecutter PR I'd suggest:

* Generate an empty ``campaigns/`` directory under
  ``docs/developer_guide/`` with an ``index.rst`` containing just
  a ``..  toctree:: :glob:`` over ``*/index``.
* Generate a single sample campaign directory like
  ``campaigns/{cookiecutter.first_campaign_date}/`` (with a
  default like ``YYYY-MM-DD``) containing:

  * ``index.rst`` with a one-line title and a ``:glob: *``
    toctree.
  * A skeleton ``scope.rst`` with prompts ("What problem does this
    campaign solve?  What's in scope and what's not?  Key design
    decisions.").
  * A skeleton ``NOTES_A.rst`` to set the file-naming convention
    by example.

* Add the campaigns toctree-include to the cookiecutter's
  ``docs/developer_guide/index.rst`` (you already have that
  pattern in xtb_step's developer_guide/index.rst).

That gets new plug-ins set up with the same shape from day one
without forcing them to fill anything in until they actually run
a campaign.


Open issues with this drop
==========================

1. **No Sphinx build verification.**  I cannot run Sphinx here, so
   while the RST has been hand-checked (balanced backticks, table
   alignment, ``:sub:``/``:sup:`` escapes use single backslashes,
   toctree paths match filenames), the first real ``make docs``
   may surface issues I can't see.  Most likely place for trouble:
   the grid tables in ``results.rst`` (Sphinx is picky about
   their formatting); if any table fails to parse, the fix is
   usually a one-column-width adjustment.

2. **API reference (`docs/api/index.rst`) is unchanged.**  It's
   currently a barebones template; if you want it filled out with
   ``automodule`` directives for ``xtb_step.energy``, etc., that's
   a quick follow-up.

3. **No usage.rst content.**  The cookiecutter-generated
   ``docs/developer_guide/usage.rst`` still says
   "To use the QuickMin Step in a project::".  That should
   probably become a short developer-facing example of
   subclassing ``Substep`` to add a new xTB sub-step (e.g. a
   future MD step).  Out of scope for this drop, but worth
   flagging.

4. **Sample output tables in energy.rst / frequencies.rst** use
   approximate numbers from your earlier water test runs.  They
   are illustrative, not exact, and labeled as such.  If you'd
   prefer to regenerate them from a fresh run and paste in
   exact numbers, that's straightforward.


Code style
==========

All RST files use the convention I read off your existing files:

* Section underlines use ``=`` for top-level and ``-`` for
  sub-sections.
* Code blocks use ``code-block:: text`` for output samples and
  ``code-block:: console`` for shell commands.
* Inline code uses double-backtick.  Italics use single asterisks.
* ``:sub:`` and ``:sup:`` escapes use single-backslash word break
  (``O\ :sub:`2``` not ``O\\ :sub:`2```).  This was the one place
  I had a bug mid-draft and fixed it; spot-check confirms all
  occurrences are now single-backslash.

No line length convention enforced for RST -- the files mostly
wrap at ~70-80 chars where the prose runs naturally.
