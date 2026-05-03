# -*- coding: utf-8 -*-

"""The graphical part of an xTB Frequencies step.

Inherits from :class:`TkOptimization` to reuse the energy frame and
the optimization frame, since xtb's recommended frequency invocation
is ``--ohess`` (optimize-then-Hessian). Adds its own "frequencies
frame" below for the frequency / thermochemistry-specific parameters.
"""

import pprint  # noqa: F401
import tkinter as tk
import tkinter.ttk as ttk

import xtb_step  # noqa: F401, E999
from .tk_optimization import TkOptimization
from seamm_util import ureg, Q_, units_class  # noqa: F401, E999
import seamm_widgets as sw


class TkFrequencies(TkOptimization):
    """The graphical part of a Frequencies step in a flowchart.

    See Also
    --------
    TkOptimization, TkEnergy, Frequencies, FrequenciesParameters
    """

    def create_dialog(self, title="xTB Frequencies"):
        """Create the dialog: energy + optimization frames from parents,
        plus a frequencies frame.
        """
        # Let parents build the energy and optimization frames.
        frame = super().create_dialog(title=title)

        P = self.node.parameters

        # Frequencies frame
        f_frame = self["frequencies frame"] = ttk.LabelFrame(
            frame,
            borderwidth=4,
            relief="sunken",
            text="Frequencies / Thermochemistry",
            labelanchor="n",
            padding=10,
        )

        # Skip the parents' keys so we only create the frequencies-specific
        # widgets in this frame.
        parent_keys = set(xtb_step.OptimizationParameters.parameters) | set(
            xtb_step.EnergyParameters.parameters
        )
        skip = parent_keys | {"results", "extra keywords", "create tables"}
        for key in xtb_step.FrequenciesParameters.parameters:
            if key in skip:
                continue
            self[key] = P[key].widget(f_frame)

        # Bind 'optimize first' so toggling it can hide the optimization
        # frame in future iterations. For v1 we just trigger reset_dialog
        # so any future logic gets called.
        if "optimize first" in self:
            of = self["optimize first"]
            if hasattr(of, "combobox"):
                of.combobox.bind("<<ComboboxSelected>>", self.reset_dialog)
                of.combobox.bind("<Return>", self.reset_dialog)
                of.combobox.bind("<FocusOut>", self.reset_dialog)

        self.reset_dialog()

        return frame

    def reset_dialog(self, widget=None):
        """Layout: energy frame, optimization frame (parents), then ours."""
        # Parents lay out energy (row 0) and optimization (row 1).
        row = super().reset_dialog()

        # Place our frequencies frame below.
        self["frequencies frame"].grid(row=row, column=0, sticky=tk.EW, pady=5)
        row += 1

        self.reset_frequencies_frame()

        return row

    def reset_frequencies_frame(self, widget=None):
        """Layout the widgets inside the frequencies frame."""
        f_frame = self["frequencies frame"]
        for slave in f_frame.grid_slaves():
            slave.grid_forget()

        row = 0
        widgets = []
        parent_keys = set(xtb_step.OptimizationParameters.parameters) | set(
            xtb_step.EnergyParameters.parameters
        )
        skip = parent_keys | {"results", "extra keywords", "create tables"}
        for key in xtb_step.FrequenciesParameters.parameters:
            if key in skip:
                continue
            self[key].grid(row=row, column=0, sticky=tk.EW)
            widgets.append(self[key])
            row += 1

        sw.align_labels(widgets, sticky=tk.E)

        return row
