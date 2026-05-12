=============================================================
xtb_step Phase C -- xTBParameters Fix Drop -- File Drop Notes
=============================================================

This drop fixes the ``TypeError: 'NoneType' object is not subscriptable``
that you saw when adding the xTB step to a flowchart. The root cause was
that the cookiecutter never created an ``xTBParameters`` class for the
top-level step, and ``xTB.__init__()`` never set ``self.parameters``,
so ``seamm.tk_node.create_dialog`` blew up trying to read
``self.node.parameters["extra keywords"]``.

This is the same pattern that ``fhi_aims_step`` uses: the top-level
step has a (mostly empty) Parameters subclass whose only job is to
satisfy the GUI machinery. The substeps own all the real parameters.


Three small changes
===================

You only need to apply three changes on top of your current installed
tree (which is already Phase A + the Phase B substep work plus the
installer drop):

New file
--------

``xtb_step/xtb_parameters.py``
    Minimal ``xTBParameters(seamm.Parameters)`` subclass with an empty
    parameters dict. Mirrors ``fhi_aims_step/fhi_aims_parameters.py``
    structurally. The ``"extra keywords"`` entry that the dialog code
    reads is supplied automatically by the ``seamm.Parameters`` base
    class -- the subclass does not need to declare it.

One-line change to ``xtb_step/xtb.py``
--------------------------------------

In ``xTB.__init__()``, immediately after the ``super().__init__(...)``
call (which ends with ``)  # yapf: disable``), add:

::

    self.parameters = xtb_step.xTBParameters()

so that block looks like::

    super().__init__(
        flowchart=flowchart,
        title="xTB",
        extension=extension,
        module=__name__,
        logger=logger,
    )  # yapf: disable

    self.parameters = xtb_step.xTBParameters()
    self._metadata = xtb_step.metadata

(I'm including a full Phase-A-compatible ``xtb.py`` in this drop too,
in case it's easier to overwrite than patch -- but the only change
relative to Phase A is the one new line.)

One-line change to ``xtb_step/__init__.py``
-------------------------------------------

Add an import for ``xTBParameters`` right after the existing
``xTBStep`` import. The change is a single new line::

    from .xtb import xTB  # noqa: F401, E501
    from .xtb_step import xTBStep  # noqa: F401, E501
    from .xtb_parameters import xTBParameters  # noqa: F401     <-- new
    from .tk_xtb import TkxTB  # noqa: F401, E501

(Again, the full updated ``__init__.py`` is included in this drop for
copy-and-replace convenience.)


What this should fix
====================

After the change, opening the edit dialog on the top-level xTB step
in a flowchart should produce a (mostly empty) parameter dialog
instead of a stack trace. The dialog will be empty because the
top-level step genuinely has no parameters of its own -- all the
real parameters live on the Energy / Optimization / Frequencies
substeps inside the subflowchart, exactly like FHI-aims.


Why didn't this come up in Phase A?
===================================

Phase A's testing was "does the plug-in install and does the test
suite pass?". Both of those operate without ever calling
``tk_node.create_dialog`` on the top-level step (the test harness
constructs nodes but doesn't open Tk dialogs, and ``make install``
doesn't touch Tk at all). The bug only surfaced when you actually
clicked on the step in the flowchart GUI -- which is the first time
``create_dialog`` runs on the top-level step.

Lesson: the cookiecutter has a small gap for the subflowchart variant
where it generates substep parameter classes but not a top-level one.
Worth flagging for the SEAMM cookiecutter maintainers (you, presumably).


Code style
==========

All files compile cleanly. The new ``xtb_parameters.py`` follows the
same docstring/header pattern as the other parameter files in the
plug-in. All lines are <= 88 characters.
