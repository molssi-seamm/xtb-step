# -*- coding: utf-8 -*-

"""Non-graphical part of the Optimization step in an xTB flowchart."""

import importlib.resources
import logging
from pathlib import Path
import pprint  # noqa: F401

import xtb_step
from .energy import Energy
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


class Optimization(Energy):
    """Run an xTB geometry optimization (ANCopt).

    Inherits from :class:`Energy`; reuses the parameter set, the executor
    invocation, the JSON parsing, and the citation logic. Adds the
    ``--opt LEVEL`` flag and post-processing of the optimized geometry.

    See Also
    --------
    Energy, Substep, OptimizationParameters, TkOptimization
    """

    def __init__(
        self, flowchart=None, title="Optimization", extension=None, logger=logger
    ):
        """A substep for an xTB geometry optimization."""
        # Skip Energy's __init__ (it sets parameters/calculation labels we
        # need to override) and call Substep.__init__ directly via the
        # grandparent.
        super(Energy, self).__init__(
            flowchart=flowchart,
            title=title,
            extension=extension,
            module=__name__,
            logger=logger,
        )

        self._calculation = "Optimization"
        self._model = None
        self._metadata = xtb_step.metadata
        self.parameters = xtb_step.OptimizationParameters()

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------

    def description_text(self, P=None, calculation_type=None):
        """Override Energy's description with optimization-specific text."""
        if not P:
            P = self.parameters.values_to_dict()
        level = P.get("optimization level", "normal")
        ctype = calculation_type or f"geometry optimization (--opt {level})"
        text = super().description_text(P=P, calculation_type=ctype)

        handling = P.get("structure handling", "Overwrite the current configuration")
        text += f"\n    Structure handling: {handling}."
        return text

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self, extra_args=None):
        """Run the Optimization step."""
        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )

        # Build the --opt flag
        level = P.get("optimization level", "normal")
        opt_args = ["--opt", level]

        # Allow further appending by Frequencies.run().
        if extra_args:
            opt_args = list(extra_args) + opt_args

        # Delegate the heavy lifting to Energy.run(), which will write
        # coord.xyz, invoke xtb, parse JSON, store results, and call
        # self.analyze().
        next_node = super().run(extra_args=opt_args)

        # Post-process: pick up the optimized geometry from xtbopt.xyz.
        directory = Path(self.directory)
        self._handle_optimized_structure(directory, P)

        return next_node

    # ------------------------------------------------------------------
    # Geometry post-processing
    # ------------------------------------------------------------------

    def _handle_optimized_structure(self, directory, P):
        """Read xtbopt.xyz and apply the user-selected structure handling.

        xtb writes the optimized geometry to ``xtbopt.xyz`` (XMOL format)
        when invoked with ``--opt``. The trajectory is in ``xtbopt.log``.
        """
        opt_path = directory / "xtbopt.xyz"
        if not opt_path.exists():
            logger.warning(f"xtbopt.xyz not found at {opt_path}")
            return

        handling = P.get("structure handling", "Overwrite the current configuration")
        if handling == "Discard the optimized structure":
            return

        try:
            xyz_text = opt_path.read_text()
        except OSError as exc:
            logger.warning(f"Could not read {opt_path}: {exc}")
            return

        # Choose the destination configuration per the user's request.
        if handling == "Overwrite the current configuration":
            _, configuration = self.get_system_configuration(None)
        elif handling == "Add a new configuration":
            _, configuration = self.get_system_configuration(
                P={"structure handling": "Create a new configuration"},
                same_as="current",
            )
        elif handling == "Add a new system":
            _, configuration = self.get_system_configuration(
                P={"structure handling": "Create a new system and configuration"},
                same_as="current",
            )
        else:
            logger.warning(f"Unknown structure-handling mode: {handling!r}")
            return

        # Update the configuration's coordinates from the XYZ text.
        if hasattr(configuration, "from_xyz_text"):
            try:
                configuration.from_xyz_text(xyz_text)
            except Exception as exc:
                logger.warning(f"Could not apply optimized geometry: {exc}")
                return
        else:
            # Fallback: parse the XMOL XYZ ourselves (atom count + 1 comment
            # + N lines of "symbol x y z").
            lines = xyz_text.strip().splitlines()
            try:
                n = int(lines[0].split()[0])
            except (IndexError, ValueError):
                logger.warning("Malformed xtbopt.xyz")
                return
            atoms = lines[2 : 2 + n]
            new_xyz = []
            for line in atoms:
                parts = line.split()
                if len(parts) < 4:
                    continue
                new_xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
            try:
                configuration.atoms.set_coordinates(new_xyz, fractionals=False)
            except Exception as exc:
                logger.warning(f"Could not update coordinates: {exc}")

        printer.normal(
            __(
                f"Updated structure from {opt_path.name}.",
                indent=4 * " ",
                wrap=False,
                dedent=False,
            )
        )
