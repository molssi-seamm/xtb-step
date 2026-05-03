# -*- coding: utf-8 -*-

"""The graphical part of an xTB Energy step."""

import pprint  # noqa: F401
import tkinter as tk

import xtb_step  # noqa: F401, E999
import seamm
from seamm_util import ureg, Q_, units_class  # noqa: F401, E999
import seamm_widgets as sw


class TkEnergy(seamm.TkNode):
    """The graphical part of an Energy step in a flowchart.

    The dialog dynamically hides the ``solvent`` widget when the
    ``solvation model`` is ``"none"``, and indents it under the
    solvation-model label when shown -- a common SEAMM pattern.

    See Also
    --------
    Energy, EnergyParameters
    """

    def __init__(
        self,
        tk_flowchart=None,
        node=None,
        canvas=None,
        x=None,
        y=None,
        w=200,
        h=50,
    ):
        """Initialize a graphical node."""
        self.dialog = None

        super().__init__(
            tk_flowchart=tk_flowchart,
            node=node,
            canvas=canvas,
            x=x,
            y=y,
            w=w,
            h=h,
        )

    def create_dialog(self):
        """Create the dialog."""
        frame = super().create_dialog(title="xTB Energy")

        # Shortcut for parameters
        P = self.node.parameters

        # Create all the value widgets (skip non-display ones)
        for key in P:
            if key[0] != "_" and key not in (
                "results",
                "extra keywords",
                "create tables",
            ):
                self[key] = P[key].widget(frame)

        # Bind the solvation-model widget so changes redraw the layout.
        # We bind to the underlying combobox for enum-type parameters.
        smodel = self["solvation model"]
        smodel.combobox.bind("<<ComboboxSelected>>", self.reset_energy_frame)
        smodel.combobox.bind("<Return>", self.reset_energy_frame)
        smodel.combobox.bind("<FocusOut>", self.reset_energy_frame)

        # Lay them out for the first time.
        self.reset_dialog()

    def reset_dialog(self, widget=None):
        """Top-level layout entry. Delegates to ``reset_energy_frame``."""
        # Remove any widgets previously packed
        frame = self["frame"]
        for slave in frame.grid_slaves():
            slave.grid_forget()

        # Lay out the energy widgets, with conditional visibility.
        self.reset_energy_frame()

        # Setup results tab if there are any
        have_results = (
            "results" in self.node.metadata and len(self.node.metadata["results"]) > 0
        )
        if have_results and "results" in self.node.parameters:
            self.setup_results()

    def reset_energy_frame(self, widget=None):
        """Layout the energy parameters, hiding/indenting solvent.

        Two-column layout: column 0 holds left-aligned labels for the
        always-visible parameters; column 1 holds the indented
        ``solvent`` widget when it is shown. ``sw.align_labels`` is
        called separately on each column's widget list so the labels
        line up nicely within their groups.
        """
        frame = self["frame"]
        for slave in frame.grid_slaves():
            slave.grid_forget()

        row = 0
        widgets_main = []
        widgets_indented = []

        # Always-visible widgets, full width
        for key in ("method", "accuracy", "solvation model"):
            self[key].grid(row=row, column=0, columnspan=2, sticky=tk.EW)
            widgets_main.append(self[key])
            row += 1

        # Conditional: solvent visible only if solvation != "none"
        smodel = self["solvation model"].get()
        if smodel != "none":
            self["solvent"].grid(row=row, column=1, sticky=tk.EW)
            widgets_indented.append(self["solvent"])
            row += 1

        sw.align_labels(widgets_main, sticky=tk.E)
        if widgets_indented:
            sw.align_labels(widgets_indented, sticky=tk.E)

        return row

    def right_click(self, event):
        """Right-click context menu."""
        super().right_click(event)
        self.popup_menu.add_command(label="Edit..", command=self.edit)
        self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
