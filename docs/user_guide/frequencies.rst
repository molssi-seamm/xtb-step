===========
Frequencies
===========

The ``Frequencies`` sub-step computes the analytic Hessian and reports
harmonic vibrational frequencies, IR intensities, and
thermochemistry quantities. By default it first optimizes the
geometry (xTB's ``--ohess`` workflow), since Hessians on
non-stationary geometries are not physically meaningful.

Dialog
======

The dialog has three panels.

Hamiltonian Parameters
----------------------

The same panel as in :doc:`Energy <energy>` and
:doc:`Optimization <optimization>`.

Optimization
------------

The same panel as in :doc:`Optimization <optimization>`. The
optimization-level and structure-handling settings are used when
**Optimize first** is set to ``yes``; they are ignored when it is
set to ``no``.

Frequencies / Thermochemistry
-----------------------------

Optimize first
    Whether to optimize the geometry before computing the Hessian.

    * **yes** (default) -- uses ``--ohess``, the recommended xTB
      workflow.
    * **no** -- uses ``--hess`` and assumes the input geometry is
      already a stationary point. Use this only if you have
      *just* run an Optimization sub-step or are confident the
      geometry is converged tightly enough.

Temperature
    Temperature for the thermochemistry table. Defaults to 298.15 K
    (standard conditions). Note that v1 of the plug-in only uses
    xTB's default temperature; non-default values will be supported
    in a future release via xTB's ``xcontrol`` file. If you request
    a non-default temperature, a warning is printed.

Pressure
    Pressure for the thermochemistry table. Defaults to 1 atm.
    xTB's thermo treatment uses the ideal-gas approximation;
    pressure enters only through the standard-state correction.

Output
======

The results table augments the energy table with frequency-count
and thermochemistry rows:

.. code-block:: text

                xTB (GFN2-xTB) Frequencies / Thermochemistry
        ╭─────────────────────────────────────────────────────┬─────────────┬────────────╮
        │                      Property                       │      Value  │   Units    │
        ├─────────────────────────────────────────────────────┼─────────────┼────────────┤
        │                Number of frequencies                │      9      │            │
        │                Imaginary frequencies                │      0      │            │
        │                  The total energy                   │   -5.070544 │   E_h      │
        │ The electronic energy (excluding nuclear repulsion) │   -5.096007 │   E_h      │
        │                  The HOMO-LUMO gap                  │   14.3730   │   eV       │
        │        The molecular dipole moment magnitude        │    2.2109   │   debye    │
        │          The zero-point vibrational energy          │   52.78     │   kJ/mol   │
        │              The thermal enthalpy H(T)              │   62.71     │   kJ/mol   │
        │            The entropic contribution T*S            │   56.18     │   kJ/mol   │
        │                    The entropy S                    │  188.4      │  J/mol/K   │
        │             The Gibbs free energy G(T)              │    6.52     │   kJ/mol   │
        │    The total free energy (electronic + G(RRHO))     │ -13311.78   │   kJ/mol   │
        │       The temperature for the thermochemistry       │  298.15     │   K        │
        ╰─────────────────────────────────────────────────────┴─────────────┴────────────╯

Frequencies, IR intensities, and reduced masses are also stored as
arrays in the property database (one entry per mode).

Number of imaginary frequencies
-------------------------------

For a true minimum, **Imaginary frequencies** should be 0. For a
genuine transition state it should be 1. Larger values indicate
the geometry is on a higher-order saddle or that the optimizer
failed to converge tightly enough -- tighten the
``optimization level`` and rerun.

Note that xTB conventionally reports imaginary frequencies as
**negative** values in its output (i.e. -150 cm\ :sup:`-1`
instead of 150i). The ``Imaginary frequencies`` count here is just
the number of entries with a negative value.

The work directory contains, in addition to the Energy and
Optimization files, ``vibspectrum`` (Turbomole-format IR
spectrum), ``hessian`` (the Hessian matrix), and ``g98.out``
(Gaussian-98-format file readable by many visualization tools).
