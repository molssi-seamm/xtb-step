#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Guard tests keeping the xTB MDI method sets consistent across two files.

The xTB methods reachable through the MDI engine are declared in two places:

* ``xtb_step/xtb_step.py``         -- ``xTBStep._MDI_CAPABLE_METHODS``
* ``xtb_step/data/tblite_mdi.py``  -- the argparse ``--method`` ``choices``

Unlike MOPAC (where the two sets are equal), the tblite engine *accepts more*
than xtb_step advertises: tblite also supports ``IPEA1-xTB``, which xtb_step
does not list in its metadata, so it is not offered as a model chemistry. The
invariant is therefore a **subset**: every method xtb_step advertises as
MDI-capable must be one the engine actually accepts.

``tblite_mdi.py`` is read as text and parsed with :mod:`ast` rather than
imported: it lives in ``data/`` (not an importable module) and is written to
run under the ``seamm-xtb`` environment, so importing it here could fail on
``tblite`` / ``mdi`` that are not installed in the test environment.
"""

import ast
import importlib.resources

from xtb_step.xtb_step import xTBStep


def _engine_method_choices():
    """Return the ``--method`` ``choices`` list from ``data/tblite_mdi.py``.

    Walks the AST for an ``add_argument('--method', ..., choices=[...])`` call
    and returns the literal string choices, without importing the engine.
    """
    source = (
        importlib.resources.files("xtb_step") / "data" / "tblite_mdi.py"
    ).read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_argument"):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if not (isinstance(first, ast.Constant) and first.value == "--method"):
            continue
        for kw in node.keywords:
            if kw.arg == "choices":
                return [
                    elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)
                ]
        raise AssertionError(
            "Found the --method argument in data/tblite_mdi.py but it has no "
            "choices=[...] keyword."
        )

    raise AssertionError(
        "Could not find an add_argument('--method', ..., choices=[...]) call "
        "in data/tblite_mdi.py."
    )


def test_capable_methods_are_accepted_by_engine():
    """Every advertised MDI-capable method must be a valid engine ``--method``.

    (The engine may accept *more* than this -- e.g. IPEA1-xTB -- which is fine;
    xtb_step simply does not advertise those.)
    """
    engine_choices = set(_engine_method_choices())
    advertised = set(xTBStep._MDI_CAPABLE_METHODS)

    missing_in_engine = advertised - engine_choices
    assert not missing_in_engine, (
        "xTBStep._MDI_CAPABLE_METHODS advertises methods the tblite engine "
        f"does not accept via --method: {sorted(missing_in_engine)}. Either add "
        "them to tblite_mdi.py's --method choices or remove them from "
        "_MDI_CAPABLE_METHODS."
    )


def test_periodic_validated_is_subset_of_capable():
    """Every periodic-validated method must also be MDI-capable."""
    capable = set(xTBStep._MDI_CAPABLE_METHODS)
    periodic = set(xTBStep._MDI_PERIODIC_VALIDATED)

    extra = periodic - capable
    assert not extra, (
        "_MDI_PERIODIC_VALIDATED contains methods absent from "
        f"_MDI_CAPABLE_METHODS: {sorted(extra)}"
    )
