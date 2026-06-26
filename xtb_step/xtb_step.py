# -*- coding: utf-8 -*-

import configparser
import importlib.resources
import os
from pathlib import Path
import shutil

import xtb_step


class xTBStep(object):
    """Helper class needed for the stevedore integration.

    This must provide a `description()` method that returns a dict containing a
    description of this node, and `create_node()` and `create_tk_node()` methods
    for creating the graphical and non-graphical nodes.

    The dictionary for the description is the class variable just below these
    comments. The felds are as follows:

        my_description : {str, str}
            A human-readable description of this step. It can be
            several lines long, and needs to be clear to non-expert users.
            It contains the following keys: description, group, name.

        my_description["description"] : tuple
            A description of the xTB step. It must be
            clear to non-experts.

        my_description["group"] : str
            Which group in the menus to put this step. If the group does
            not exist it will be created. Common groups are "Building",
            "Control", "Custom", "Data", and "Simulations".

        my_description["name"] : str
            The name of this step, to be displayed in the menus.
    """

    my_description = {
        "description": "An interface for xTB",
        "group": "Simulations",
        "name": "xTB",
    }

    # ----------------------------------------------------------------------
    # Model-chemistry / MDI engine contract (mirrors MOPACStep).
    #
    # The xTB methods drivable as an MDI engine. The engine is the tblite
    # library (data/tblite_mdi.py), whose Python API covers GFN1-xTB,
    # GFN2-xTB (and IPEA1-xTB); GFN0-xTB and GFN-FF are reachable only through
    # the ordinary xtb-binary path, not via MDI. Both MDI-capable methods are
    # validated for periodic systems (tblite returns the virial -> stress).
    # ----------------------------------------------------------------------
    _MDI_CAPABLE_METHODS = {"GFN1-xTB", "GFN2-xTB"}
    _MDI_PERIODIC_VALIDATED = {"GFN1-xTB", "GFN2-xTB"}

    @classmethod
    def get_model_chemistry_options(cls, periodic_only=False, mdi_only=False):
        """Return the model chemistries (level specs) xTB can provide.

        Advertises bare ``[owner:]type@method`` level specs (the consumer
        supplies the driver and task), keyed by bare method name, exactly as
        ``MOPACStep`` does. xTB is semiempirical QM, so the type is ``SQM`` and
        the owner is ``xTB`` -- e.g. ``xTB:SQM@GFN2-xTB``.

        Parameters
        ----------
        periodic_only : bool
            Only return methods validated for periodic systems via MDI.
        mdi_only : bool
            Only return methods launchable via the tblite MDI engine.

        Returns
        -------
        dict
            Keyed by bare method name (e.g. ``"GFN2-xTB"``); see the field set
            below. ``periodic_native`` is the method's own metadata flag (the
            xtb-binary path refuses periodic input in v1); ``periodic_mdi`` is
            whether it is validated periodic through the tblite MDI engine.
        """
        options = {}
        for theory_class, class_data in xtb_step.metadata[
            "computational models"
        ].items():
            for family, family_data in class_data["models"].items():
                for name, param in family_data["parameterizations"].items():
                    mdi_capable = name in cls._MDI_CAPABLE_METHODS
                    periodic_mdi = name in cls._MDI_PERIODIC_VALIDATED

                    if periodic_only and not periodic_mdi:
                        continue
                    if mdi_only and not mdi_capable:
                        continue

                    options[name] = {
                        "model_chemistry": f"xTB:SQM@{name}",
                        "type": "SQM",
                        "description": param.get("description", name),
                        "periodic_native": param.get("periodic", False),
                        "periodic_mdi": periodic_mdi,
                        "elements": param.get("elements", ""),
                        "mdi_capable": mdi_capable,
                        "mdi_method_arg": name if mdi_capable else None,
                    }
        return options

    @classmethod
    def get_executor_config(cls, executor, seamm_options):
        """Return how to launch the xTB MDI engine on this machine.

        Reads the per-plug-in ``xtb.ini`` for the current executor type, so the
        tblite MDI engine runs in the same conda environment (``seamm-xtb``) as
        ordinary xTB jobs, and adds ``mdi_script`` -- the absolute path to the
        bundled ``data/tblite_mdi.py`` engine (Option C: shipped in the wheel,
        refreshed by ``pip install -U xtb-step``).

        ``tblite_mdi.py`` imports only packages present in ``seamm-xtb``
        (``tblite``, ``pymdi``/``mdi``, ``numpy``) and nothing from ``xtb_step``
        or ``seamm``, so it runs under that environment's Python even though the
        file lives in the ``seamm`` environment's site-packages.

        Parameters
        ----------
        executor : seamm.ExecutorBase
            The flowchart executor (``self.flowchart.executor`` in the driver);
            ``executor.name`` selects the ini section.
        seamm_options : dict
            The global SEAMM options (``self.global_options``);
            ``seamm_options["root"]`` locates the ini.

        Returns
        -------
        dict
            The ini section for the current executor, plus ``version`` (the
            plug-in version) and ``mdi_script`` (absolute path to
            data/tblite_mdi.py).
        """
        executor_type = executor.name
        ini_dir = Path(seamm_options["root"]).expanduser()
        ini_path = ini_dir / "xtb.ini"
        resources = importlib.resources.files("xtb_step") / "data"

        # Bootstrap a default xtb.ini if the user has none yet, defaulting the
        # [local] section to the seamm-xtb conda environment.
        if not ini_path.exists():
            boot = configparser.ConfigParser()
            boot.read_string((resources / "xtb.ini").read_text())
            if "local" not in boot:
                boot.add_section("local")
            boot["local"]["installation"] = "conda"
            boot["local"]["conda"] = os.environ["CONDA_EXE"]
            boot["local"]["conda-environment"] = "seamm-xtb"
            with ini_path.open("w") as fd:
                boot.write(fd)

        full_config = configparser.ConfigParser()
        full_config.read(ini_path)

        # Last-ditch: fall back to an xtb executable on $PATH (a local install).
        if executor_type not in full_config:
            path = shutil.which("xtb")
            if path is None:
                raise RuntimeError(
                    f"No section for '{executor_type}' in the xTB ini file "
                    f"({ini_path}), nor in the defaults, nor on $PATH."
                )
            full_config.add_section(executor_type)
            full_config.set(executor_type, "installation", "local")
            full_config.set(executor_type, "code", str(path))
            with ini_path.open("w") as fd:
                full_config.write(fd)

        config = dict(full_config.items(executor_type))
        config["version"] = xtb_step.__version__
        config["mdi_script"] = str(resources / "tblite_mdi.py")
        return config

    @classmethod
    def get_mdi_engine_command(
        cls,
        executor,
        seamm_options,
        *,
        method,
        port,
        hostname="localhost",
        charge=0,
        multiplicity=1,
        n_atoms=None,
        engine_name="TBLITE",
        extra_args=None,
    ):
        """Build the argv that launches the tblite MDI *engine* over TCP.

        The driver (e.g. lammps_step) owns the rendezvous (TCP, ``port``,
        ``hostname``) and passes it in; everything xTB-specific -- the conda
        environment, the bundled ``tblite_mdi.py`` path, the engine's MDI name,
        and the method / charge / spin flags -- is supplied here, so the driver
        hardwires no xTB knowledge.

        The engine bootstraps its structure from ``structure.dat`` (the LAMMPS
        data file the driver writes) and derives the per-type element symbols
        from the ``fix ... mdi/qm ... elements`` line in ``input.dat`` itself,
        so no element list need be threaded through this contract.

        Parameters
        ----------
        executor, seamm_options
            Passed straight to ``get_executor_config``.
        method : str
            xTB Hamiltonian, e.g. "GFN2-xTB"; must be in
            ``cls._MDI_CAPABLE_METHODS``.
        port : int
            TCP port the engine binds; chosen by the driver.
        hostname : str
            Host the engine binds / the driver connects to.
        charge, multiplicity : int
            Total charge and 2S+1 multiplicity (from the configuration object).
            tblite counts *unpaired electrons*, so ``--uhf`` = multiplicity - 1.
        n_atoms : int, optional
            Number of atoms, used to size the engine's OpenMP/MKL threads from
            the ``[xtb-step]`` section of ``seamm.ini`` (atoms-per-core /
            ncores). If given, ``OMP_NUM_THREADS`` / ``MKL_NUM_THREADS`` are set
            on the engine's command line, overriding any inherited cap.
        engine_name : str
            The MDI ``-name`` for the engine (default "TBLITE").
        extra_args : list of str, optional
            Extra engine flags appended verbatim.

        Returns
        -------
        list of str
            A ready-to-run argv; render into the launch script with
            ``shlex.join(argv)``.
        """
        if method not in cls._MDI_CAPABLE_METHODS:
            raise ValueError(
                f"'{method}' is not an MDI-capable xTB method; expected "
                f"one of {sorted(cls._MDI_CAPABLE_METHODS)}."
            )

        config = cls.get_executor_config(executor, seamm_options)

        installation = config.get("installation", "conda")
        if installation != "conda":
            raise NotImplementedError(
                "The tblite MDI engine is currently wired up only for a conda "
                f"installation; xtb.ini selects '{installation}'. "
                "TODO: local / modules / docker launches."
            )

        mdi_init = (
            f"-role ENGINE -name {engine_name} -method TCP "
            f"-port {port} -hostname {hostname}"
        )
        # tblite uses the number of unpaired electrons, not 2S+1.
        uhf = multiplicity - 1

        argv = [
            config["conda"],
            "run",
            "--live-stream",
            "-n",
            config["conda-environment"],
            "python",
            config["mdi_script"],
            "-mdi",
            mdi_init,
            "--structure",
            "structure.dat",
            "--method",
            method,
            "--charge",
            str(charge),
            "--uhf",
            str(uhf),
        ]
        if extra_args:
            argv.extend(extra_args)

        # Size the engine's OpenMP/MKL threads from the [xtb-step] config and
        # set them on the engine's command line (an env-var prefix), overriding
        # any cap the launch script inherits (the driver pins OMP=1 for itself).
        if n_atoms is not None:
            from .substep import xtb_thread_count

            n = xtb_thread_count(n_atoms)
            argv = [f"OMP_NUM_THREADS={n}", f"MKL_NUM_THREADS={n}", *argv]

        return argv

    def __init__(self, flowchart=None, gui=None):
        """Initialize this helper class, which is used by
        the application via stevedore to get information about
        and create node objects for the flowchart
        """
        pass

    def create_node(self, flowchart=None, **kwargs):
        """Create and return the new node object.

        Parameters
        ----------
        flowchart: seamm.Node
            A non-graphical SEAMM node

        **kwargs : keyword arguments
            Various keyword arguments such as title, namespace or
            extension representing the title displayed in the flowchart,
            the namespace for the plugins of a subflowchart and
            the extension, respectively.

        Returns
        -------
        xTB
        """

        return xtb_step.xTB(flowchart=flowchart, **kwargs)

    def create_tk_node(self, canvas=None, **kwargs):
        """Create and return the graphical Tk node object.

        Parameters
        ----------
        canvas : tk.Canvas
            The Tk Canvas widget

        **kwargs : keyword arguments
            Various keyword arguments such as tk_flowchart, node, x, y, w, h
            representing a graphical flowchart object, a non-graphical node for
            a step, and dimensions of the graphical node.

        Returns
        -------
        TkxTB
        """

        return xtb_step.TkxTB(canvas=canvas, **kwargs)

    def description(self):
        """Return a description of what this step does.

        Returns
        -------
        description : dict(str, str)
        """
        return xTBStep.my_description
