#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `xtb_step` package."""

import pytest  # noqa: F401
import xtb_step  # noqa: F401


def test_construction():
    """Just create an object and test its type."""
    result = xtb_step.xTB()
    assert str(type(result)) == "<class 'xtb_step.xtb.xTB'>"
