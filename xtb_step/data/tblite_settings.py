# -*- coding: utf-8 -*-

"""The settings of the tblite MDI engine's calculations, for their fingerprints.

Used by the engine (``tblite_mdi.py``, in the seamm-xtb environment, which has no
SEAMM packages) to report what it computed, and by ``xtb_step`` to predict it, so
both describe a calculation with the same text. The engine reports the record
without the hash; the driver's side completes it with
``seamm_util.fingerprint.calculation_record``, so that every code hashes the same
way.

What changes the energy at a geometry: the method, tblite's numerical accuracy
and tblite's version (its defaults, such as the electronic temperature, come with
it). The charge and the number of unpaired electrons belong to the species, as for
every code, and the SCF retries do not change the converged energy. This module
imports nothing outside the standard library.
"""

PROGRAM = "tblite"
SETTINGS_FILE = "tblite settings"


def settings_text(method, accuracy=1.0):
    """The text hashed for a calculation with ``method`` at ``accuracy``."""
    return f"method {method}\naccuracy {float(accuracy)!r}\n"


def tblite_version():
    """tblite's version, e.g. "0.5.0", or "unknown"."""
    try:
        from importlib.metadata import version

        return version("tblite")
    except Exception:
        return "unknown"


def settings_record(method, accuracy=1.0, version=None):
    """The engine's record of a calculation, without the fingerprint, which the
    driver's side adds (seamm_mdi completes records that have none)."""
    return {
        "program": PROGRAM,
        "version": tblite_version() if version is None else version,
        "files": {SETTINGS_FILE: settings_text(method, accuracy)},
    }
