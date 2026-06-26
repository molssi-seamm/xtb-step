#!/usr/bin/env python3
"""
tblite_mdi.py -- MDI engine wrapping the tblite tight-binding library.

Supports GFN1-xTB, GFN2-xTB, and IPEA1-xTB via the tblite Python API, for use
with LAMMPS fix mdi/qm as the MD driver.

Like mopac_mdi.py, this needs **no input file**: the atom count, atomic
numbers, coordinates, and (for periodic systems) the cell all arrive over the
MDI handshake from the driver -- LAMMPS sends >NATOMS, >ELEMENTS (the
``elements`` keyword on the fix mdi/qm line makes it send atomic numbers),
>COORDS and >CELL. The tblite Calculator is built lazily on the first
energy/force request, once those have been received; on later steps the
geometry (and cell, for NPT) is pushed in with calc.update().

Usage -- TCP mode (two terminals, simplest for testing):
    Terminal 1:
        python tblite_mdi.py \\
            -mdi "-role ENGINE -name TBLITE -method TCP -port 8021" \\
            --method GFN2-xTB
    Terminal 2:
        mpirun -np 1 lmp -in in.tblite_nvt \\
            -mdi "-role DRIVER -name LAMMPS -method TCP -port 8021"

Units: MDI and tblite.interface both use Bohr / Hartree, so coordinates,
lattice, energy, gradient and virial pass through without conversion.

Threads: honors OMP_NUM_THREADS / MKL_NUM_THREADS from the environment (the
LAMMPS step sets these from the [xtb-step] seamm.ini config).

Logging: --log-level INFO (default) is terse -- lifecycle plus one energy line
per step; DEBUG adds every MDI command. tblite's own output is controlled
separately by --verbosity (default silent).
"""

import argparse
import logging
import sys
import numpy as np

# mpi4py must be imported before mdi in MPI mode so that MPI_Init has
# already been called when MDI_Init splits the communicator.
try:
    from mpi4py import MPI  # noqa: F401  (imported for its MPI_Init side effect)

    _mpi_available = True
except ImportError:
    _mpi_available = False

logger = logging.getLogger("tblite-mdi")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="tblite MDI engine for LAMMPS fix mdi/qm")
    p.add_argument(
        "-mdi",
        required=True,
        help="MDI initialization string passed directly to MDI_Init",
    )
    p.add_argument(
        "--method",
        default="GFN2-xTB",
        choices=["GFN1-xTB", "GFN2-xTB", "IPEA1-xTB"],
        help="xTB Hamiltonian (default: GFN2-xTB)",
    )
    p.add_argument(
        "--charge",
        type=float,
        default=0.0,
        help="Total charge of the system (default: 0)",
    )
    p.add_argument(
        "--uhf",
        type=int,
        default=0,
        help="Number of unpaired electrons (default: 0)",
    )
    p.add_argument(
        "--verbosity",
        type=int,
        default=0,
        help="tblite's own internal output verbosity: 0=silent, 1=minimal, "
        "2=full (default: 0). Separate from --log-level below.",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Engine logging. INFO (default): lifecycle + one energy line per "
        "step (terse). DEBUG: every MDI command. WARNING: quietest.",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    try:
        import mdi
    except ImportError:
        sys.exit("ERROR: mdi not found. conda install -c conda-forge pymdi")
    try:
        from tblite.interface import Calculator
    except ImportError:
        sys.exit("ERROR: tblite not found. conda install -c conda-forge tblite-python")

    mdi.MDI_Init(args.mdi)
    comm = mdi.MDI_Accept_Communicator()

    mdi.MDI_Register_node("@DEFAULT")
    for _cmd in [
        "<NATOMS",  # engine sends natoms (fix mdi/qm normally sends >NATOMS)
        ">NATOMS",  # driver sends natoms to engine
        "<NAME",  # engine sends its name
        ">ELEMENTS",  # driver sends atomic numbers
        ">COORDS",  # driver sends coordinates (Bohr)
        ">CELL",  # driver sends cell matrix (Bohr)
        "SCF",  # driver triggers the calculation
        "<ENERGY",  # driver requests energy (Hartree)
        "<FORCES",  # driver requests forces (Hartree/Bohr)
        "<STRESS",  # driver requests stress (Hartree/Bohr^3)
        "EXIT",  # driver signals end of simulation
    ]:
        mdi.MDI_Register_command("@DEFAULT", _cmd)

    logger.info("MDI connection established. method=%s", args.method)

    # ----------------------------------------------------------------
    # State accumulated from the MDI handshake -- no input file.
    # ----------------------------------------------------------------
    natoms = None
    atomic_numbers = None
    coords_bohr = None  # (3*natoms,) Bohr
    cell_flat = None  # (9,) Bohr
    is_periodic = False
    have_elements = False
    have_coords = False

    calc = None
    result = None
    recompute = True

    def build_calculator():
        """Construct the tblite Calculator from the handshake data (once)."""
        nonlocal calc
        lattice = cell_flat.reshape(3, 3) if is_periodic else None
        periodic = np.array([True, True, True]) if is_periodic else None
        calc = Calculator(
            method=args.method,
            numbers=atomic_numbers,
            positions=coords_bohr.reshape(-1, 3),
            lattice=lattice,
            periodic=periodic,
            charge=float(args.charge),
            uhf=args.uhf,
        )
        calc.set("verbosity", args.verbosity)
        logger.info(
            "tblite Calculator built: natoms=%d, periodic=%s", natoms, is_periodic
        )

    def compute():
        """Build the calculator if needed, push the current geometry, run SCF."""
        nonlocal result
        if not (have_elements and have_coords):
            raise RuntimeError(
                "energy/forces requested before >ELEMENTS and >COORDS were "
                "received over MDI -- check the LAMMPS fix mdi/qm line includes "
                "the 'elements' keyword so the driver sends atomic numbers."
            )
        if calc is None:
            build_calculator()
        else:
            lattice = cell_flat.reshape(3, 3) if is_periodic else None
            calc.update(positions=coords_bohr.reshape(-1, 3), lattice=lattice)
        # res=result warm-starts the SCF from the previous step's density;
        # copy=False updates the result in place.
        result = calc.singlepoint(res=result, copy=False)
        logger.info("energy = %.10f Ha", result.get("energy"))

    # ----------------------------------------------------------------
    # MDI event loop
    # ----------------------------------------------------------------
    logger.info("Entering MDI event loop ...")

    while True:
        command = mdi.MDI_Recv_Command(comm)
        logger.debug("command: %r", command)

        if command == "<NATOMS":
            mdi.MDI_Send(natoms, 1, mdi.MDI_INT, comm)

        elif command == ">NATOMS":
            raw = mdi.MDI_Recv(1, mdi.MDI_INT, comm)
            natoms = int(np.asarray(raw).flat[0])
            atomic_numbers = np.zeros(natoms, dtype=int)
            coords_bohr = np.zeros(3 * natoms)
            logger.debug(">NATOMS: %d", natoms)

        elif command == "<NAME":
            mdi.MDI_Send("TBLITE", mdi.MDI_NAME_LENGTH, mdi.MDI_CHAR, comm)

        elif command == ">ELEMENTS":
            # Driver sends one atomic number per atom -- this is our element map.
            raw = mdi.MDI_Recv(natoms, mdi.MDI_INT, comm)
            atomic_numbers[:] = np.asarray(raw)
            have_elements = True
            calc = None  # element set fixed at construction; (re)build with it
            recompute = True

        elif command == ">COORDS":
            raw = mdi.MDI_Recv(3 * natoms, mdi.MDI_DOUBLE, comm)
            coords_bohr[:] = np.asarray(raw)
            have_coords = True
            recompute = True

        elif command == ">CELL":
            raw = mdi.MDI_Recv(9, mdi.MDI_DOUBLE, comm)
            cell_flat = np.asarray(raw, dtype=float)
            is_periodic = True
            recompute = True

        elif command in ("SCF", "<ENERGY", "<FORCES", "<STRESS"):
            if recompute or calc is None:
                compute()
                recompute = False

            if command == "<ENERGY":
                # tblite Hartree -> MDI Hartree: no conversion
                mdi.MDI_Send(result.get("energy"), 1, mdi.MDI_DOUBLE, comm)
            elif command == "<FORCES":
                # gradient (dE/dx, Hartree/Bohr); MDI force = -dE/dx -> negate
                forces = -result.get("gradient").ravel()
                mdi.MDI_Send(forces, 3 * natoms, mdi.MDI_DOUBLE, comm)
            elif command == "<STRESS":
                if not is_periodic:
                    raise RuntimeError("<STRESS requested for a non-periodic system")
                # virial W (Hartree, 3x3); intensive Cauchy stress sigma = -W/V
                # (tensile positive, Ha/Bohr^3). Sign verified empirically via
                # the compress/expand test.
                virial = result.get("virial")
                volume = abs(np.linalg.det(cell_flat.reshape(3, 3)))  # Bohr^3
                stress = -virial / volume
                mdi.MDI_Send(stress.ravel(), 9, mdi.MDI_DOUBLE, comm)

        elif command == "EXIT":
            logger.info("EXIT -- shutting down.")
            break

        else:
            logger.warning("unrecognised command %r", command)

    logger.info("Done.")


if __name__ == "__main__":
    main()
