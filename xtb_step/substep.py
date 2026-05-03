# -*- coding: utf-8 -*-

"""A base class for substeps of the xTB plug-in.

All substeps (Energy, Optimization, Frequencies, and any future substeps such
as MD or metadynamics) inherit from ``Substep``. This base class holds the
machinery that is genuinely common across substeps:

* Module-level constants for method <-> CLI flag mapping and the supported
  solvent list per solvation model.
* A periodicity check that refuses periodic input with a clear message.
* A writer for the ``coord.xyz`` input file consumed by xtb.
* A builder for the common parts of the xtb command line (method, charge,
  multiplicity, accuracy, solvation, JSON output).
* A wrapper around the SEAMM executor for invoking the xtb binary.
* A JSON-output parser for ``xtbout.json``.
* A text parser for the few quantities not exposed in the JSON
  (notably the thermochemistry block from Hessian runs).

It deliberately does NOT bake in any assumption that a substep is
energy-related, so an MD substep, for example, can inherit directly from
``Substep`` without going through ``Energy``.
"""

import configparser
import importlib.resources
import json
import logging
from pathlib import Path
import pprint  # noqa: F401
import re
import shutil

import seamm
from seamm_util import ureg, Q_  # noqa: F401
import seamm_util.printing as printing

logger = logging.getLogger(__name__)
job = printing.getPrinter()
printer = printing.getPrinter("xTB")


# ---------------------------------------------------------------------------
# Method / model mapping
# ---------------------------------------------------------------------------

#: User-facing method label -> list of xtb CLI arguments.
METHOD_TO_CLI = {
    "GFN2-xTB": ["--gfn", "2"],
    "GFN1-xTB": ["--gfn", "1"],
    "GFN0-xTB": ["--gfn", "0"],
    "GFN-FF": ["--gfnff"],
}

#: All methods we expose. Used as the parameter enumeration.
METHODS = tuple(METHOD_TO_CLI)

# ---------------------------------------------------------------------------
# Solvation
# ---------------------------------------------------------------------------

#: Solvation model labels -> CLI flag.
SOLVATION_MODEL_TO_FLAG = {
    "none": None,
    "ALPB": "--alpb",
    "GBSA": "--gbsa",
    "CPCM-X": "--cpcmx",
}

#: Solvation models we expose. ``"none"`` means no implicit solvation.
SOLVATION_MODELS = tuple(SOLVATION_MODEL_TO_FLAG)

# ALPB and GBSA share the same parametrized solvent list. The list below is
# from the xTB documentation as of v6.7. Some solvents are method-specific:
# DMF and n-hexane are GFN2-only; benzene is GFN1-only. We expose the union
# here and let xtb itself reject mismatches with a clear error.
SOLVENTS_GBSA_ALPB = (
    "acetone",
    "acetonitrile",
    "benzene",  # GFN1 only
    "CH2Cl2",
    "CHCl3",
    "CS2",
    "DMF",  # GFN2 only
    "DMSO",
    "ether",
    "H2O",
    "methanol",
    "n-hexane",  # GFN2 only
    "THF",
    "toluene",
)

# CPCM-X uses the much larger Minnesota Solvation Database. The most common
# entries are listed; users can also pass arbitrary strings via the variable
# mechanism (the parameter enumeration is not strictly enforced).
SOLVENTS_CPCMX = (
    "acetone",
    "acetonitrile",
    "aniline",
    "benzaldehyde",
    "benzene",
    "CH2Cl2",
    "CHCl3",
    "CS2",
    "dioxane",
    "DMF",
    "DMSO",
    "ether",
    "ethylacetate",
    "furane",
    "hexadecane",
    "hexane",
    "methanol",
    "nitromethane",
    "octanol",
    "phenol",
    "thf",
    "toluene",
    "water",
    "octanol(wet)",
)


def solvent_choices_for(model):
    """Return the supported solvent enumeration for a solvation model.

    Parameters
    ----------
    model : str
        The solvation-model label (one of :data:`SOLVATION_MODELS`).

    Returns
    -------
    tuple of str
        The list of solvent names we expose to the user. Empty for "none".
    """
    if model == "ALPB" or model == "GBSA":
        return SOLVENTS_GBSA_ALPB
    if model == "CPCM-X":
        return SOLVENTS_CPCMX
    return ()


# ---------------------------------------------------------------------------
# Substep base class
# ---------------------------------------------------------------------------


class Substep(seamm.Node):
    """Common base class for substeps of the xTB plug-in.

    Subclasses are expected to:

    * Set ``self._calculation`` to a short identifier (e.g. ``"Energy"``).
    * Set ``self._model`` once the active xTB Hamiltonian is known
      (e.g. ``"GFN2-xTB"``).
    * Provide their own ``parameters``, ``description_text``, ``run``,
      and ``analyze`` methods.

    The helpers below are available to all subclasses:

    * :meth:`check_periodicity` -- raise on periodic input.
    * :meth:`write_coord_xyz` -- write the molecule to ``coord.xyz``.
    * :meth:`base_xtb_args` -- build the common part of the xtb CLI.
    * :meth:`run_xtb` -- invoke xtb via the SEAMM executor.
    * :meth:`read_xtbout_json` -- parse ``xtbout.json``.
    * :meth:`parse_thermo_block` -- pull the thermochemistry table from the
      text output.
    """

    def __init__(
        self,
        flowchart=None,
        title="no title",
        extension=None,
        logger=logger,
        module=__name__,
    ):
        """Initialize the Substep base class.

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
        module : str
            The module name, used by the SEAMM Node base.
        """
        self._input_only = False
        self._calculation = None
        self._model = None

        super().__init__(
            flowchart=flowchart,
            title=title,
            extension=extension,
            logger=logger,
        )

    @property
    def header(self):
        """A printable header for this section of output."""
        return "Step {}: {}".format(".".join(str(e) for e in self._id), self.title)

    @property
    def input_only(self):
        """Whether to write the input only, not run xtb."""
        return self._input_only

    @input_only.setter
    def input_only(self, value):
        self._input_only = value

    @property
    def is_runable(self):
        """Indicate whether this substep runs xtb or just adds input."""
        return True

    @property
    def global_options(self):
        """Pass-through to the parent (top-level xTB step)'s global options."""
        return self.parent.global_options

    @property
    def options(self):
        """Pass-through to the parent (top-level xTB step)'s options."""
        return self.parent.options

    # ------------------------------------------------------------------
    # Periodicity refusal
    # ------------------------------------------------------------------

    def check_periodicity(self, configuration):
        """Refuse periodic input with a clear, user-visible message.

        xTB's PBC support is limited and is out of scope for v1 of this
        plug-in. If the configuration is periodic, this method prints a
        message via the step printer and raises ``RuntimeError`` so the
        flowchart stops cleanly.
        """
        if configuration.periodicity != 0:
            msg = (
                "The xtb_step plug-in does not currently support periodic "
                "systems. The configuration has periodicity "
                f"{configuration.periodicity}. Please use a molecular "
                "(non-periodic) configuration, or use a different plug-in "
                "(e.g. dftbplus_step) for periodic xTB-family calculations."
            )
            printer.important(msg)
            raise RuntimeError(msg)

    # ------------------------------------------------------------------
    # Coordinate writer
    # ------------------------------------------------------------------

    def write_coord_xyz(self, directory, configuration, filename="coord.xyz"):
        """Write the configuration to a standard XYZ file for xtb."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename

        if hasattr(configuration, "to_xyz_text"):
            path.write_text(configuration.to_xyz_text())
        else:
            symbols = configuration.atoms.symbols
            coords = configuration.atoms.get_coordinates(fractionals=False)
            lines = [str(len(symbols)), ""]
            for sym, (x, y, z) in zip(symbols, coords):
                lines.append(f"{sym:<3s} {x:18.10f} {y:18.10f} {z:18.10f}")
            path.write_text("\n".join(lines) + "\n")

        return path

    # ------------------------------------------------------------------
    # CLI builders
    # ------------------------------------------------------------------

    def base_xtb_args(self, P, configuration):
        """Build the parts of the xtb CLI common to all substeps.

        Parameters
        ----------
        P : dict
            The current parameter values (from
            ``parameters.current_values_to_dict()``). Expected keys include
            ``method``, ``charge``, ``multiplicity``, ``accuracy``,
            ``solvation model``, ``solvent``.
        configuration : molsystem.Configuration
            Used only to provide a default total spin if the user has not
            specified one.

        Returns
        -------
        list of str
            The argument list to prepend to the substep-specific arguments.
            Always begins with the coordinate filename (``coord.xyz``).
        """
        args = ["coord.xyz"]
        args += METHOD_TO_CLI[P["method"]]
        args += ["--json"]

        # Charge
        charge = int(P.get("charge", 0))
        args += ["--chrg", str(charge)]

        # Multiplicity / unpaired electrons. xtb takes --uhf with the number
        # of UNPAIRED electrons (M - 1 for spin multiplicity M).
        mult = int(P.get("multiplicity", 1))
        n_unpaired = max(mult - 1, 0)
        args += ["--uhf", str(n_unpaired)]

        # Accuracy
        if "accuracy" in P:
            try:
                acc = float(P["accuracy"])
            except (TypeError, ValueError):
                acc = 1.0
            if acc != 1.0:
                args += ["--acc", f"{acc:g}"]

        # Solvation
        smodel = P.get("solvation model", "none")
        if smodel != "none":
            flag = SOLVATION_MODEL_TO_FLAG[smodel]
            solvent = P.get("solvent", "H2O")
            args += [flag, str(solvent)]
            if smodel != "CPCM-X" and P["method"] == "GFN0-xTB":
                # ALPB/GBSA are not parametrized for GFN0-xTB.
                logger.warning(
                    "Solvation models ALPB/GBSA are not parametrized for "
                    "GFN0-xTB. xtb may emit a warning or refuse to run."
                )

        return args

    # ------------------------------------------------------------------
    # Executor wrapper
    # ------------------------------------------------------------------

    def run_xtb(self, args, return_files=None, env=None):
        """Run xtb via the SEAMM executor.

        Reads the per-plug-in ``xtb.ini`` from the SEAMM root directory,
        falling back to the bundled ``data/xtb.ini`` template if the user
        does not yet have one. Then dispatches the run through the
        flowchart's executor (which handles conda/local/modules/docker
        transparently).
        """
        if return_files is None:
            return_files = []
        if env is None:
            env = {"OMP_NUM_THREADS": "1"}

        executor = self.parent.flowchart.executor
        executor_type = executor.name

        # Locate / bootstrap the xtb.ini configuration
        seamm_options = self.global_options
        ini_dir = Path(seamm_options["root"]).expanduser()
        ini_path = ini_dir / "xtb.ini"

        if not ini_path.exists():
            resources = importlib.resources.files("xtb_step") / "data"
            ini_text = (resources / "xtb.ini").read_text()
            ini_path.write_text(ini_text)
            logger.info(f"Bootstrapped default xtb.ini at {ini_path}")

        full_config = configparser.ConfigParser()
        full_config.read(ini_path)

        if executor_type not in full_config:
            path = shutil.which("xtb")
            if path is None:
                raise RuntimeError(
                    f"No section for '{executor_type}' in the xtb.ini "
                    f"({ini_path}), no defaults provided, and no 'xtb' "
                    "executable found on $PATH. Please install xtb (e.g. "
                    "via 'conda install -c conda-forge xtb') or edit "
                    f"{ini_path} to point at an xtb installation."
                )
            full_config.add_section(executor_type)
            full_config.set(executor_type, "installation", "local")
            full_config.set(executor_type, "code", str(path))
            with ini_path.open("w") as fd:
                full_config.write(fd)
            logger.info(
                f"Added a '{executor_type}' section to {ini_path} pointing "
                f"at {path}"
            )

        config = dict(full_config.items(executor_type))

        code = config.get("code", "xtb")
        cmd = [code, *args]

        result = executor.run(
            cmd=cmd,
            config=config,
            directory=self.directory,
            files={},
            return_files=return_files,
            in_situ=True,
            shell=True,
            env=env,
        )

        if not result:
            self.logger.error("There was an error running xtb")
            return None

        logger.debug("xtb run result:\n" + pprint.pformat(result))

        return result

    # ------------------------------------------------------------------
    # JSON parser
    # ------------------------------------------------------------------

    def read_xtbout_json(self, directory=None, filename="xtbout.json"):
        """Read the xtb JSON output produced by ``--json``.

        xTB writes ``xtbout.json`` in the working directory when invoked with
        ``--json``. The schema includes (at least, in recent releases):
        ``"total energy"``, ``"HOMO-LUMO gap / eV"``, ``"electronic
        energy"``, ``"dipole / a.u."``, ``"partial charges"``, plus
        method-specific fields. The exact set varies between xtb versions;
        callers should treat the returned dict as best-effort.

        Parameters
        ----------
        directory : pathlib.Path, optional
            The directory containing the file. Defaults to ``self.directory``.
        filename : str
            The JSON filename to read. Defaults to ``xtbout.json``.

        Returns
        -------
        dict
            The parsed JSON data, or an empty dict if the file is missing
            or unreadable.
        """
        if directory is None:
            directory = self.directory
        path = Path(directory) / filename

        if not path.exists():
            logger.warning(f"xtb JSON output not found: {path}")
            return {}

        try:
            with path.open() as fd:
                return json.load(fd)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"Could not parse xtb JSON output {path}: {exc}")
            return {}

    # ------------------------------------------------------------------
    # Text-output parsers
    # ------------------------------------------------------------------

    def parse_thermo_block(self, stdout):
        """Pull thermochemistry quantities from xtb stdout.

        xtb's Hessian runs print a ``:: THERMODYNAMIC ::`` summary block
        and a per-temperature table. We extract the key scalars at a single
        temperature here. The format is::

            :: total free energy   -41.971849822766 Eh ::
            :: total energy        -42.153937303642 Eh ::
            :: zero point energy     0.182087480876 Eh ::
            :: G(RRHO) w/o ZPVE      0.000000000000 Eh ::
            :: G(RRHO) contrib.      0.182087480876 Eh ::

        and a temperature line like::

           T/K   H(0)-H(T)+PV   H(T)/Eh   T*S/Eh   G(T)/Eh
           298.15  ...   ...   ...   ...

        Parameters
        ----------
        stdout : str
            The captured stdout (or contents of an ``xtb.out`` file) from a
            Hessian run.

        Returns
        -------
        dict
            Possibly containing keys: ``total_free_energy``,
            ``zero_point_energy``, ``temperature``, ``enthalpy``,
            ``entropy_term``, ``gibbs_free_energy``. All energies in E_h,
            temperature in K. Missing entries indicate parsing failed for
            that quantity; callers should handle absence gracefully.
        """
        out = {}

        # Scalar lines from the THERMODYNAMIC summary block.
        scalar_patterns = {
            "total_free_energy": r":: total free energy\s+(-?\d+\.\d+)\s*Eh",
            "zero_point_energy": r":: zero point energy\s+(-?\d+\.\d+)\s*Eh",
        }
        for key, pat in scalar_patterns.items():
            m = re.search(pat, stdout)
            if m:
                try:
                    out[key] = float(m.group(1))
                except ValueError:
                    pass

        # The per-temperature table: take the first data row after the
        # T/K header line.
        # Header looks roughly like:
        #   T/K     H(0)-H(T)+PV   H(T)/Eh    T*S/Eh    G(T)/Eh
        thermo_header = re.search(
            r"T/K\s+H\(0\)-H\(T\)\+PV\s+H\(T\)/Eh\s+T\*S/Eh\s+G\(T\)/Eh",
            stdout,
        )
        if thermo_header:
            tail = stdout[thermo_header.end() :]
            # Skip dash-separator lines, find first numeric row of 5 floats.
            for line in tail.splitlines():
                line = line.strip()
                if not line or set(line) <= {"-"}:
                    continue
                # Numbers may be in 0.123E+02 or plain decimal notation.
                num = r"-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?"
                m = re.match(rf"({num})\s+({num})\s+({num})\s+({num})\s+({num})", line)
                if m:
                    try:
                        out["temperature"] = float(m.group(1))
                        out["enthalpy"] = float(m.group(3))
                        out["entropy_term"] = float(m.group(4))
                        out["gibbs_free_energy"] = float(m.group(5))
                    except ValueError:
                        pass
                    break

        return out
