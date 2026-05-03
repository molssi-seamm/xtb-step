# -*- coding: utf-8 -*-

"""The graphical part of an xTB Optimization step.

Inherits from :class:`TkEnergy` to reuse the energy frame and the
dynamic solvation/solvent visibility. Adds its own "optimization frame"
below the energy frame, holding the optimizer-specific parameters.
"""

import pprint  # noqa: F401
import tkinter as tk
import tkinter.ttk as ttk

import xtb_step  # noqa: F401, E999
from .tk_energy import TkEnergy
from seamm_util import ureg, Q_, units_class  # noqa: F401, E999
import seamm_widgets as sw


class TkOptimization(TkEnergy):
    """The graphical part of an Optimization step in a flowchart.

    See Also
    --------
    TkEnergy, Optimization, OptimizationParameters
    """

    def create_dialog(self, title="xTB Optimization"):
        """Create the dialog: energy frame from parent, plus opt frame."""
        # Let TkEnergy build the energy frame and bind its widgets.
        frame = super().create_dialog(title=title)

        P = self.node.parameters

        # Optimization frame
        o_frame = self["optimization frame"] = ttk.LabelFrame(
            frame,
            borderwidth=4,
            relief="sunken",
            text="Optimization",
            labelanchor="n",
            padding=10,
        )

        # Create the optimization-specific widgets (skip the parent's keys
        # so we don't redraw them in this frame).
        parent_keys = set(xtb_step.EnergyParameters.parameters)
        skip = parent_keys | {"results", "extra keywords", "create tables"}
        for key in xtb_step.OptimizationParameters.parameters:
            if key in skip:
                continue
            self[key] = P[key].widget(o_frame)

        # Re-layout now that we have the second frame.
        self.reset_dialog()

        return frame

    def reset_dialog(self, widget=None):
        """Layout the energy frame (parent) then the optimization frame."""
        # Parent lays out the energy frame at row 0 and returns the next row.
        row = super().reset_dialog()

        # Place our optimization frame below it.
        self["optimization frame"].grid(row=row, column=0, sticky=tk.EW, pady=5)
        row += 1

        # Lay out the widgets inside our frame.
        self.reset_optimization_frame()

        return row

    def reset_optimization_frame(self, widget=None):
        """Layout the widgets inside the optimization frame."""
        o_frame = self["optimization frame"]
        for slave in o_frame.grid_slaves():
            slave.grid_forget()

        row = 0
        widgets = []
        # Walk the OptimizationParameters keys, in their declared order,
        # picking only the keys we actually created in this frame.
        parent_keys = set(xtb_step.EnergyParameters.parameters)
        skip = parent_keys | {"results", "extra keywords", "create tables"}
        for key in xtb_step.OptimizationParameters.parameters:
            if key in skip:
                continue
            self[key].grid(row=row, column=0, sticky=tk.EW)
            widgets.append(self[key])
            row += 1

        sw.align_labels(widgets, sticky=tk.E)

        return row
