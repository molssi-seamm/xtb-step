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
from seamm_util.printing import FormattedText as __

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

        # Temperature passes through xtb's --etemp? No -- --etemp is the
        # electronic temperature. Thermo temperature is set via xcontrol's
        # $thermo block. For v1, we leave xtb's default (298.15 K) and
        # warn if the user requests something different.
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
        # writes coord.xyz, invokes xtb, parses xtbout.json, and calls
        # store_results() / analyze().
        next_node = Energy.run(self, extra_args=hess_args)

        # If we did an optimize-first, also pick up the optimized geometry.
        directory = Path(self.directory)
        if opt_first:
            self._handle_optimized_structure(directory, P)

        # Augment data with thermo block from stdout, and frequencies from
        # JSON / vibspectrum if not already present.
        self._post_run_thermo_and_freqs(directory)

        return next_node

    # ------------------------------------------------------------------
    # Post-processing: thermo block and frequencies
    # ------------------------------------------------------------------

    def _post_run_thermo_and_freqs(self, directory):
        """Re-read xtb outputs to extract Hessian-specific quantities.

        Energy._collect_results() captured the JSON-based scalars. Here we
        add: vibrational frequencies (from JSON if present, else
        ``vibspectrum``), thermochemistry quantities (from ``xtb.out``),
        and the model has already been set in Energy.run().
        """
        data = {}

        # Frequencies and intensities from JSON if available
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
            for key in ("IR intensities", "ir intensities", "IR intensities/(km/mol)"):
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

        if data:
            _, configuration = self.get_system_configuration(None)
            self.store_results(configuration=configuration, data=data)

            # Brief printout
            lines = []
            if "frequencies" in data:
                freqs = data["frequencies"]
                n_imag = sum(1 for f in freqs if f < 0)
                lines.append(f"Number of frequencies:   {len(freqs)}")
                lines.append(f"Imaginary frequencies:   {n_imag}")
            if "zero_point_energy" in data:
                lines.append(
                    f"Zero-point energy:       {data['zero_point_energy']:.6f} E_h"
                )
            if "gibbs_free_energy" in data:
                lines.append(
                    f"Gibbs free energy G(T):  {data['gibbs_free_energy']:.6f} E_h"
                )
            if "total_free_energy" in data:
                lines.append(
                    f"Total free energy:       {data['total_free_energy']:.6f} E_h"
                )
            if lines:
                printer.normal(
                    __(
                        "\n".join(lines),
                        indent=4 * " ",
                        wrap=False,
                        dedent=False,
                    )
                )

    # ------------------------------------------------------------------
    # vibspectrum parser
    # ------------------------------------------------------------------

    def _parse_vibspectrum(self, path):
        """Parse Turbomole-format ``vibspectrum`` if JSON freqs missing.

        The format is::

           $vibrational spectrum
           #  mode    symmetry  wavenumber   IR intensity   selection rules
           #                       cm**(-1)      km/mol         IR    Raman
              1                       0.00      0.00000       -      -
              2                       0.00      0.00000       -      -
              ...
              7        a              40.69     0.16700       YES    NO
           ...
           $end

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
            # Mode index, optional symmetry label, frequency, intensity
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
