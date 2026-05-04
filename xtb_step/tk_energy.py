# -*- coding: utf-8 -*-

"""The graphical part of an xTB Energy step.

This class is also the base class for ``TkOptimization`` and
``TkFrequencies``. It owns the "energy frame", which holds the
energy / Hamiltonian / solvation widgets common to all xTB substeps.
Subclasses inherit ``create_dialog``, ``reset_dialog``, and
``reset_energy_frame`` unchanged, and just add their own frames below
the energy frame -- exactly the MOPAC ``TkEnergy`` / ``TkOptimization``
pattern.

The dialog hides the ``solvent`` widget when ``solvation model`` is
``"none"`` and indents it under the solvation row when shown.
"""

import pprint  # noqa: F401
import tkinter as tk
import tkinter.ttk as ttk

import xtb_step  # noqa: F401, E999
import seamm
from seamm_util import ureg, Q_, units_class  # noqa: F401, E999
import seamm_widgets as sw


class TkEnergy(seamm.TkNode):
    """The graphical part of an Energy step in a flowchart.

    Subclasses (TkOptimization, TkFrequencies, ...) inherit the
    energy-frame layout and the conditional solvent display, and add
    their own frames in their own ``create_dialog`` / ``reset_dialog``.
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

    def create_dialog(self, title="xTB Energy"):
        """Create the dialog and the energy frame.

        Subclasses should call ``super().create_dialog(title=...)`` first
        and then add their own frames into ``self["frame"]``.
        """
        frame = super().create_dialog(title=title)

        # Size the dialog generously so the results tab fits without
        # heavy scrolling. Same pattern as TkxTB.create_dialog.
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        w = int(0.9 * screen_w)
        h = int(0.8 * screen_h)
        x = int(0.05 * screen_w / 2)
        y = int(0.1 * screen_h / 2)
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        # Shortcut for parameters
        P = self.node.parameters

        # Energy frame -- holds method, accuracy, solvation, solvent
        e_frame = self["energy frame"] = ttk.LabelFrame(
            frame,
            borderwidth=4,
            relief="sunken",
            text="Hamiltonian Parameters",
            labelanchor="n",
            padding=10,
        )

        # Create the value widgets (skip non-display ones)
        for key in xtb_step.EnergyParameters.parameters:
            if key in ("results", "extra keywords", "create tables"):
                continue
            self[key] = P[key].widget(e_frame)

        # Bind the solvation-model widget so changes redraw the energy
        # frame layout.
        smodel = self["solvation model"]
        smodel.combobox.bind("<<ComboboxSelected>>", self.reset_energy_frame)
        smodel.combobox.bind("<Return>", self.reset_energy_frame)
        smodel.combobox.bind("<FocusOut>", self.reset_energy_frame)

        # Note: do NOT call self.reset_dialog() here. The seamm framework
        # calls reset_dialog() itself after create_dialog() returns, by
        # which time any subclass create_dialog has already built its own
        # frames. Calling it here triggers MRO-dispatched subclass
        # reset_dialog() before subclass frames exist (KeyError).

        return frame

    def reset_dialog(self, widget=None):
        """Top-level layout. Subclasses override and call ``super()``.

        Returns
        -------
        int
            The next free row in ``self["frame"]``, so subclasses can
            grid their additional frames below the energy frame.
        """
        # Remove any widgets previously packed in the top-level frame
        frame = self["frame"]
        for slave in frame.grid_slaves():
            slave.grid_forget()

        # Place the energy frame at the top
        row = 0
        self["energy frame"].grid(row=row, column=0, sticky=tk.EW)
        row += 1

        # Lay out the energy widgets inside the energy frame, with the
        # conditional solvent visibility.
        self.reset_energy_frame()

        # Setup the results tab if there are any
        have_results = (
            "results" in self.node.metadata and len(self.node.metadata["results"]) > 0
        )
        if have_results and "results" in self.node.parameters:
            self.setup_results()

        return row

    def reset_energy_frame(self, widget=None):
        """Layout the widgets inside the energy frame.

        The ``solvent`` widget is shown only when ``solvation model`` is
        not ``"none"``. To get the indentation right despite the varying
        widths of the main-column labels, we use the Gaussian-step
        pattern: layout column 0 widgets and column 1 (indented)
        widgets separately, ``align_labels`` on each, and then size
        column 0 to ``w1 - w2 + 30`` so the column-1 label starts at
        roughly the position of the column-0 value.
        """
        e_frame = self["energy frame"]
        for slave in e_frame.grid_slaves():
            slave.grid_forget()

        row = 0
        widgets = []
        widgets2 = []

        # Always-visible widgets in column 0
        for key in ("method", "accuracy", "solvation model"):
            self[key].grid(row=row, column=0, columnspan=2, sticky=tk.EW)
            widgets.append(self[key])
            row += 1

        # Conditional: solvent in column 1 (indented) only if solvation != "none"
        smodel = self["solvation model"].get()
        if smodel != "none":
            self["solvent"].grid(row=row, column=1, sticky=tk.EW)
            widgets2.append(self["solvent"])
            row += 1

        w1 = sw.align_labels(widgets, sticky=tk.E)
        if widgets2:
            w2 = sw.align_labels(widgets2, sticky=tk.E)
            e_frame.columnconfigure(0, minsize=w1 - w2 + 30)

        return row

    def right_click(self, event):
        """Right-click context menu."""
        super().right_click(event)
        self.popup_menu.add_command(label="Edit..", command=self.edit)
        self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
