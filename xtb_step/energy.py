# -*- coding: utf-8 -*-

"""Non-graphical part of the Energy step in an xTB flowchart."""

import importlib.resources
import logging
import math
from pathlib import Path
import pprint  # noqa: F401
import textwrap

from tabulate import tabulate

import xtb_step
from .substep import Substep
import molsystem
import seamm
from seamm_util import ureg, Q_  # noqa: F401
import seamm_util.printing as printing
from seamm_util.printing import FormattedText as __

logger = logging.getLogger(__name__)
job = printing.getPrinter()
printer = printing.getPrinter("xTB")

# Add this module's properties to the standard properties
path = importlib.resources.files("xtb_step") / "data"
csv_file = path / "properties.csv"
if path.exists():
    molsystem.add_properties_from_file(csv_file)

# Conversion factor: xtb reports dipole in atomic units (e * Bohr).
#                   1 a.u. (dipole) = 2.541746229 D (CODATA via Pint).
# We compute it from Pint to stay consistent with the rest of SEAMM.
_AU_DIPOLE_TO_DEBYE = (
    (1.0 * ureg.elementary_charge * ureg.bohr).to(ureg.debye).magnitude
)


class Energy(Substep):
    """Run an xTB single-point energy.

    See Also
    --------
    Substep, EnergyParameters, TkEnergy
    """

    def __init__(self, flowchart=None, title="Energy", extension=None, logger=logger):
        """A substep for an xTB single-point energy.

        Parameters
        ----------
        flowchart : seamm.Flowchart
            The non-graphical flowchart that contains this step.
        title : str
            The name displayed in the flowchart.
        extension : None
            Not yet implemented.
        logger : Logger
            The logger to use and pass to parent classes.
        """
        logger.debug(f"Creating Energy {self}")

        super().__init__(
            flowchart=flowchart,
            title=title,
            extension=extension,
            module=__name__,
            logger=logger,
        )

        self._calculation = "Energy"
        self._model = None
        self._metadata = xtb_step.metadata
        self.parameters = xtb_step.EnergyParameters()

    @property
    def version(self):
        """The semantic version of this module."""
        return xtb_step.__version__

    @property
    def git_revision(self):
        """The git version of this module."""
        return xtb_step.__git_revision__

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------

    def description_text(self, P=None, calculation_type="single-point energy"):
        """Create the text description of what this step will do.

        Note: charge and spin multiplicity are NOT mentioned here. They
        are properties of the system, not of the calculation, and the
        SEAMM convention is to not echo them at the step level.
        """
        if not P:
            P = self.parameters.values_to_dict()

        method = P["method"]
        text = (
            f"An xTB {calculation_type} calculation using the {method} " "Hamiltonian"
        )

        # Solvation
        smodel = P.get("solvation model", "none")
        if smodel != "none":
            text += f" with implicit solvation in {P['solvent']} ({smodel})"
        text += "."

        # Accuracy
        try:
            acc = float(P.get("accuracy", 1.0))
        except (TypeError, ValueError):
            acc = 1.0
        if acc != 1.0:
            text += f" SCC accuracy multiplier set to {acc:g}."

        return self.header + "\n" + __(text, **P, indent=4 * " ").__str__()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self, extra_args=None):
        """Run the Energy step.

        Parameters
        ----------
        extra_args : list of str, optional
            Additional xtb command-line arguments to append after the base
            arguments. Used by Optimization and Frequencies subclasses to
            inject ``--opt`` / ``--ohess`` flags. Defaults to none.

        Returns
        -------
        seamm.Node
            The next node object in the flowchart.
        """
        next_node = super().run(printer)

        # Resolve parameter values (dereferences any flowchart variables)
        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )

        # Print what we are doing
        printer.important(__(self.description_text(P), indent=self.indent))

        directory = Path(self.directory)
        directory.mkdir(parents=True, exist_ok=True)

        # Get the current configuration; refuse periodic input.
        # Charge and spin multiplicity come from the configuration, not P.
        _, configuration = self.get_system_configuration(None)
        self.check_periodicity(configuration)

        # Lock in the active model so store_results() formats property names
        # correctly.
        self._model = P["method"]

        # Cite the xTB references appropriate for this calculation.
        self._cite_references(P["method"], P.get("solvation model", "none"))

        # Write coord.xyz
        self.write_coord_xyz(directory, configuration)

        # Build the command line. base_xtb_args() reads charge and
        # multiplicity from the configuration.
        args = self.base_xtb_args(P, configuration)
        if extra_args:
            args += list(extra_args)

        # Allow user-specified extra keywords to be appended.
        extra_kw = P.get("extra keywords", []) or []
        if isinstance(extra_kw, str):
            extra_kw = extra_kw.split()
        args += [str(k) for k in extra_kw]

        # Default returned files. Subclasses may extend.
        return_files = ["xtbout.json", "xtbrestart"]

        result = self.run_xtb(args, return_files=return_files)

        # Persist stdout/stderr for the user
        if result is not None:
            (directory / "xtb.out").write_text(result.get("stdout", ""))
            stderr = result.get("stderr", "")
            if stderr:
                (directory / "xtb.err").write_text(stderr)

        # Harvest results
        data = self._collect_results(directory, configuration, result)

        # Store in the SEAMM property database / variables / tables
        self.store_results(configuration=configuration, data=data)

        # Print a brief summary into step.out as a table
        self.analyze(data=data, P=P)

        return next_node

    # ------------------------------------------------------------------
    # Result collection
    # ------------------------------------------------------------------

    def _collect_results(self, directory, configuration, run_result):
        """Pull values from xtbout.json (and stdout if needed) into a dict.

        Keys here must match the keys in ``metadata["results"]``.
        """
        data = {}

        json_data = self.read_xtbout_json(directory)
        if json_data:
            self._harvest_json(json_data, data, configuration)

        return data

    def _harvest_json(self, json_data, data, configuration):
        """Populate ``data`` from the xtbout.json contents.

        The schema as documented by xTB uses these top-level keys, with
        mild version-to-version drift:

        * ``"total energy"`` (E_h)
        * ``"electronic energy"`` (E_h)
        * ``"HOMO-LUMO gap / eV"``
        * ``"dipole / a.u."`` (3-vector)
        * ``"partial charges"``

        Defensive: a missing key just means that result does not get
        stored, not that the run failed.
        """
        if "total energy" in json_data:
            data["total_energy"] = float(json_data["total energy"])
        if "electronic energy" in json_data:
            data["electronic_energy"] = float(json_data["electronic energy"])

        # Gap
        for key in ("HOMO-LUMO gap / eV", "HOMO-LUMO gap/eV"):
            if key in json_data:
                data["homo_lumo_gap"] = float(json_data[key])
                break

        # Orbital energies if present (some xtb versions include them)
        for key in ("HOMO orbital eigenvalue / eV", "HOMO/eV"):
            if key in json_data:
                data["homo_energy"] = float(json_data[key])
                break
        for key in ("LUMO orbital eigenvalue / eV", "LUMO/eV"):
            if key in json_data:
                data["lumo_energy"] = float(json_data[key])
                break

        # Dipole. xtb gives the vector in a.u.; we store both vector and
        # magnitude, converted to debye.
        dipole_au = None
        for key in ("dipole / a.u.", "dipole/a.u."):
            if key in json_data:
                dipole_au = json_data[key]
                break
        if dipole_au is not None and len(dipole_au) >= 3:
            dx, dy, dz = (float(c) for c in dipole_au[:3])
            mag_au = math.sqrt(dx * dx + dy * dy + dz * dz)
            data["dipole_vector"] = [
                dx * _AU_DIPOLE_TO_DEBYE,
                dy * _AU_DIPOLE_TO_DEBYE,
                dz * _AU_DIPOLE_TO_DEBYE,
            ]
            data["dipole_moment"] = mag_au * _AU_DIPOLE_TO_DEBYE

        if "partial charges" in json_data:
            data["partial_charges"] = [float(q) for q in json_data["partial charges"]]

    # ------------------------------------------------------------------
    # Citations
    # ------------------------------------------------------------------

    def _cite_references(self, method, solvation_model):
        """Add the appropriate citations to the references handler."""
        if self.references is None:
            return

        # The general xTB review is always relevant.
        try:
            self.references.cite(
                raw=self._bibliography["Bannwarth2021"],
                alias="xtb",
                module="xtb_step",
                level=1,
                note="The principle xTB program citation.",
            )
        except KeyError:
            logger.debug("Bannwarth2021 missing from bibliography")

        # Method-specific citation
        method_to_bib = {
            "GFN2-xTB": "Bannwarth2019",
            "GFN1-xTB": "Grimme2017",
            "GFN0-xTB": "Pracht2019",
            "GFN-FF": "Spicher2020",
        }
        bib_key = method_to_bib.get(method)
        if bib_key:
            try:
                self.references.cite(
                    raw=self._bibliography[bib_key],
                    alias=method,
                    module="xtb_step",
                    level=1,
                    note=f"Citation for the {method} method.",
                )
            except KeyError:
                logger.debug(f"{bib_key} missing from bibliography")

        # Solvation citation
        if solvation_model in ("ALPB", "GBSA"):
            try:
                self.references.cite(
                    raw=self._bibliography["Ehlert2021"],
                    alias="alpb",
                    module="xtb_step",
                    level=1,
                    note=f"Citation for the {solvation_model} solvation model.",
                )
            except KeyError:
                logger.debug("Ehlert2021 missing from bibliography")

    # ------------------------------------------------------------------
    # Analysis / printing -- table-based
    # ------------------------------------------------------------------

    def analyze(self, indent="", data=None, table=None, P=None):
        """Print the results as a tabulated summary in step.out.

        Follows the Gaussian step pattern: subclasses build up a single
        ``table`` dict and pass it to ``super().analyze()``. The base
        Energy class adds the basic energy/HOMO/LUMO/dipole rows and
        prints the table at the end. This way, an Optimization or
        Frequencies substep can prepend its own rows (e.g. converged-
        energy, ZPE) in a single, ordered table.

        Parameters
        ----------
        indent : str
            Extra indentation (currently unused; ``self.indent`` controls
            the final wrap indent).
        data : dict
            Results from ``_collect_results`` and any subclass extensions.
        table : dict, optional
            A dict with three lists -- ``"Property"``, ``"Value"``,
            ``"Units"`` -- that subclasses have already populated. If
            None, a fresh empty table is created here.
        P : dict, optional
            The current parameter values. Not directly used in this
            base implementation but accepted so subclasses can pass it.
        """
        if data is None:
            data = {}

        if table is None:
            table = {"Property": [], "Value": [], "Units": []}

        metadata = xtb_step.metadata.get("results", {})

        # Standard energy / orbital / dipole rows. Order matters for
        # readability.
        keys = (
            "total_energy",
            "electronic_energy",
            "homo_energy",
            "lumo_energy",
            "homo_lumo_gap",
            "dipole_moment",
        )
        for key in keys:
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

        if not table["Property"]:
            printer.normal(
                __(
                    "No results were collected for this xTB step. Check "
                    "xtb.out and xtb.err for errors.",
                    indent=4 * " ",
                    wrap=True,
                    dedent=False,
                )
            )
            return

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
            title = f"xTB ({self._model}) Results"
        text_lines.append(title.center(length))
        text_lines.append(tmp)
        text = textwrap.indent("\n".join(text_lines), self.indent + 4 * " ")
        printer.normal("")
        printer.normal(text)
        printer.normal("")
