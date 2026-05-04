# -*- coding: utf-8 -*-

"""Non-graphical part of the Frequencies step in an xTB flowchart."""

import importlib.resources
import logging
from pathlib import Path
import pprint  # noqa: F401
import re

import xtb_step
from .optimization import Optimization
from .energy import Energy
import molsystem
import seamm
from seamm_util import ureg, Q_  # noqa: F401
import seamm_util.printing as printing

logger = logging.getLogger(__name__)
job = printing.getPrinter()
printer = printing.getPrinter("xTB")

# Add this module's properties to the standard properties
path = importlib.resources.files("xtb_step") / "data"
csv_file = path / "properties.csv"
if path.exists():
    molsystem.add_properties_from_file(csv_file)


class Frequencies(Optimization):
    """Run an xTB Hessian / vibrational frequency calculation.

    By default this uses ``--ohess <level>`` (optimize-then-Hessian), which
    is what xtb's documentation recommends since Hessians on unoptimized
    geometries are not physically meaningful. The user can disable the
    initial optimization, in which case ``--hess`` is used and the input
    geometry is assumed to be at a stationary point.

    See Also
    --------
    Optimization, Energy, Substep, FrequenciesParameters, TkFrequencies
    """

    def __init__(
        self, flowchart=None, title="Frequencies", extension=None, logger=logger
    ):
        """A substep for an xTB Hessian / frequency calculation."""
        # Skip Optimization's and Energy's __init__ (which set their own
        # parameter sets); call Substep directly.
        super(Energy, self).__init__(
            flowchart=flowchart,
            title=title,
            extension=extension,
            module=__name__,
            logger=logger,
        )

        self._calculation = "Frequencies"
        self._model = None
        self._metadata = xtb_step.metadata
        self.parameters = xtb_step.FrequenciesParameters()

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------

    def description_text(self, P=None, calculation_type=None):
        """Override with frequency-specific text."""
        if not P:
            P = self.parameters.values_to_dict()
        opt_first = P.get("optimize first", "yes") == "yes"
        if opt_first:
            level = P.get("optimization level", "normal")
            ctype = (
                f"geometry optimization (--opt {level}) followed by a "
                "Hessian and harmonic vibrational analysis"
            )
        else:
            ctype = "Hessian and harmonic vibrational analysis"
        # Skip Optimization's description (which always mentions optimization);
        # use Energy's.
        text = Energy.description_text(self, P=P, calculation_type=ctype)
        T = P.get("temperature", 298.15)
        try:
            T_val = float(T)
        except (TypeError, ValueError):
            T_val = 298.15
        text += f"\n    Thermochemistry at T = {T_val:.2f} K."
        return text

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self, extra_args=None):
        """Run the Frequencies step.

        We bypass Optimization.run() (which always inserts ``--opt``) and
        go straight to Energy.run() with the appropriate Hessian flag.
        """
        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )

        opt_first = P.get("optimize first", "yes") == "yes"
        if opt_first:
            level = P.get("optimization level", "normal")
            hess_args = ["--ohess", level]
        else:
            hess_args = ["--hess"]

        # Temperature: xtb uses the $thermo block in xcontrol for non-default
        # temperatures. v1 only supports the default 298.15 K and warns if
        # something else is requested.
        try:
            T_req = float(P.get("temperature", 298.15))
        except (TypeError, ValueError):
            T_req = 298.15
        if abs(T_req - 298.15) > 1e-6:
            printer.important(
                f"    Note: requested thermochemistry T = {T_req} K. "
                "v1 of xtb_step uses xtb's default 298.15 K thermochemistry; "
                "non-default temperatures will be supported in a future "
                "release via xcontrol's $thermo block."
            )

        if extra_args:
            hess_args = list(extra_args) + hess_args

        # Call Energy.run() (the grandparent) with the hessian args. This
        # writes coord.xyz, invokes xtb, parses xtbout.json, calls
        # store_results(), and calls self.analyze() (which dispatches to
        # Frequencies.analyze() because of the inheritance chain -- so we
        # build the thermo + freq additions there).
        next_node = Energy.run(self, extra_args=hess_args)

        # If we did an optimize-first, also pick up the optimized geometry.
        directory = Path(self.directory)
        if opt_first:
            self._handle_optimized_structure(directory, P)

        return next_node

    # ------------------------------------------------------------------
    # Analysis: extend the Energy table with thermo + freq rows
    # ------------------------------------------------------------------

    def analyze(self, indent="", data=None, table=None, P=None):
        """Augment the data dict with thermo / freq results, then defer to
        Energy.analyze() which formats the table.

        Energy.run() calls ``self.analyze(data=..., P=...)`` BEFORE we
        have parsed the thermo block from xtb.out. We re-parse here so
        the thermo rows are available when the table is built.
        """
        if data is None:
            data = {}

        directory = Path(self.directory)

        # JSON frequencies / IR intensities (newer xtb versions)
        json_data = self.read_xtbout_json(directory)
        if json_data:
            for key in (
                "vibrational frequencies/cm-1",
                "frequencies/cm-1",
                "vibrational frequencies / cm-1",
            ):
                if key in json_data:
                    data["frequencies"] = [float(f) for f in json_data[key]]
                    break
            for key in (
                "IR intensities",
                "ir intensities",
                "IR intensities/(km/mol)",
            ):
                if key in json_data:
                    data["ir_intensities"] = [float(v) for v in json_data[key]]
                    break
            for key in ("reduced masses/amu", "reduced masses"):
                if key in json_data:
                    data["reduced_masses"] = [float(v) for v in json_data[key]]
                    break

        # Fallback: vibspectrum file (Turbomole format)
        if "frequencies" not in data:
            vib_freqs, vib_int = self._parse_vibspectrum(directory / "vibspectrum")
            if vib_freqs:
                data["frequencies"] = vib_freqs
            if vib_int:
                data["ir_intensities"] = vib_int

        # Thermo block from xtb.out
        out_path = directory / "xtb.out"
        if out_path.exists():
            try:
                stdout = out_path.read_text()
            except OSError as exc:
                logger.warning(f"Could not read {out_path}: {exc}")
                stdout = ""
            thermo = self.parse_thermo_block(stdout) if stdout else {}
            data.update(thermo)

        # Persist the new fields we picked up here. (Energy.run() already
        # called store_results once with the JSON data; this second call
        # adds the freq / thermo entries.)
        if "frequencies" in data or "zero_point_energy" in data:
            _, configuration = self.get_system_configuration(None)
            self.store_results(configuration=configuration, data=data)

        # Build a fresh table; add freq summary rows BEFORE Energy's
        # standard rows.
        if table is None:
            table = {"Property": [], "Value": [], "Units": []}

        if "frequencies" in data:
            freqs = data["frequencies"]
            n_imag = sum(1 for f in freqs if f < 0)
            table["Property"].append("Number of frequencies")
            table["Value"].append(f"{len(freqs):d}")
            table["Units"].append("")
            table["Property"].append("Imaginary frequencies")
            table["Value"].append(f"{n_imag:d}")
            table["Units"].append("")

        # Now defer to Energy.analyze() which appends the standard
        # energy/HOMO/LUMO/dipole rows AND the post-energy rows we add
        # below by extending the metadata-driven loop. To keep the order
        # "energies first, thermo after", we let Energy.analyze run and
        # then add a tail. Easier: build everything ourselves.

        # Append thermo rows AFTER the energy rows. We do this by
        # patching the Energy.analyze flow: call Energy.analyze with the
        # current table (which includes our freq prefix) and have it
        # append its rows; then we add our thermo rows; then print.
        #
        # But Energy.analyze() prints the table itself. To avoid double
        # printing, we replicate the pattern here directly.

        metadata = xtb_step.metadata.get("results", {})

        # Energy block (same set as Energy.analyze)
        for key in (
            "total_energy",
            "electronic_energy",
            "homo_energy",
            "lumo_energy",
            "homo_lumo_gap",
            "dipole_moment",
        ):
            if key not in data:
                continue
            mdata = metadata.get(key, {})
            label = mdata.get("description", key)
            fmt = mdata.get("format", ".4f")
            units = mdata.get("units", "")
            try:
                value_str = f"{float(data[key]):{fmt}}"
            except (TypeError, ValueError):
                value_str = str(data[key])
            table["Property"].append(label)
            table["Value"].append(value_str)
            table["Units"].append(units)

        # Thermo block
        for key in (
            "zero_point_energy",
            "enthalpy",
            "entropy_term",
            "entropy",
            "gibbs_free_energy",
            "total_free_energy",
            "temperature",
        ):
            if key not in data:
                continue
            mdata = metadata.get(key, {})
            label = mdata.get("description", key)
            fmt = mdata.get("format", ".4f")
            units = mdata.get("units", "")
            try:
                value_str = f"{float(data[key]):{fmt}}"
            except (TypeError, ValueError):
                value_str = str(data[key])
            table["Property"].append(label)
            table["Value"].append(value_str)
            table["Units"].append(units)

        # Print the assembled table directly (do NOT call super().analyze,
        # which would re-add the energy rows we already appended).
        if not table["Property"]:
            return

        from tabulate import tabulate
        import textwrap

        tmp = tabulate(
            table,
            headers="keys",
            tablefmt="rounded_outline",
            colalign=("center", "decimal", "left"),
            disable_numparse=True,
        )
        length = len(tmp.splitlines()[0])
        text_lines = []
        title = "xTB Results"
        if self._model:
            title = f"xTB ({self._model}) Frequencies / Thermochemistry"
        text_lines.append(title.center(length))
        text_lines.append(tmp)
        text = textwrap.indent("\n".join(text_lines), self.indent + 4 * " ")
        printer.normal("")
        printer.normal(text)
        printer.normal("")

    # ------------------------------------------------------------------
    # vibspectrum parser
    # ------------------------------------------------------------------

    def _parse_vibspectrum(self, path):
        """Parse Turbomole-format ``vibspectrum`` if JSON freqs missing.

        Returns (frequencies, intensities) lists. Empty lists on failure.
        """
        if not path.exists():
            return [], []
        try:
            text = path.read_text()
        except OSError:
            return [], []

        freqs = []
        ints = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("$"):
                continue
            num = r"-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?"
            m = re.match(
                rf"^\d+\s+(?:[A-Za-z][A-Za-z0-9'\"]*\s+)?({num})\s+({num})", line
            )
            if m:
                try:
                    freqs.append(float(m.group(1)))
                    ints.append(float(m.group(2)))
                except ValueError:
                    pass

        return freqs, ints
