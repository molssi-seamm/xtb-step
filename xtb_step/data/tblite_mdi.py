#!/usr/bin/env python3
"""
tblite_mdi.py -- MDI engine wrapping the tblite tight-binding library.

Supports GFN1-xTB, GFN2-xTB, and IPEA1-xTB via the tblite Python API.
Designed for use with LAMMPS fix mdi/qm as the MD driver.

Usage — TCP mode (two terminals, simplest for initial testing):
    Terminal 1:
        python tblite_mdi.py \\
            -mdi "-role ENGINE -name TBLITE -method TCP -port 8021" \\
            --structure structure.dat --method GFN2-xTB

    Terminal 2:
        mpirun -np 1 lmp -in in.tblite_nvt \\
            -mdi "-role DRIVER -name LAMMPS -method TCP -port 8021"

Usage — MPI mode (one mpirun, both in same universe):
    mpirun --mca mpi_yield_when_idle 1 \\
      -np 1 python tblite_mdi.py \\
             -mdi "-role ENGINE -name TBLITE -method MPI" \\
             --structure structure.dat --elements C O H H --method GFN2-xTB \\
      : -np 1 lmp -in in.tblite_nvt \\
             -mdi "-role DRIVER -name LAMMPS -method MPI"
"""

import argparse
import sys
import numpy as np

# mpi4py must be imported before mdi in MPI mode so that MPI_Init has
# already been called when MDI_Init splits the communicator.
try:
    from mpi4py import MPI  # noqa: F401  (imported for its MPI_Init side effect)

    _mpi_available = True
except ImportError:
    _mpi_available = False

# ---------------------------------------------------------------------------
# Atomic number lookup
# ---------------------------------------------------------------------------
_SYMBOL_TO_Z = {
    "H": 1,
    "He": 2,
    "Li": 3,
    "Be": 4,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "F": 9,
    "Ne": 10,
    "Na": 11,
    "Mg": 12,
    "Al": 13,
    "Si": 14,
    "P": 15,
    "S": 16,
    "Cl": 17,
    "Ar": 18,
    "K": 19,
    "Ca": 20,
    "Sc": 21,
    "Ti": 22,
    "V": 23,
    "Cr": 24,
    "Mn": 25,
    "Fe": 26,
    "Co": 27,
    "Ni": 28,
    "Cu": 29,
    "Zn": 30,
    "Ga": 31,
    "Ge": 32,
    "As": 33,
    "Se": 34,
    "Br": 35,
    "Kr": 36,
    "Rb": 37,
    "Sr": 38,
    "I": 53,
}


def symbol_to_z(sym):
    try:
        return _SYMBOL_TO_Z[sym]
    except KeyError:
        raise ValueError(f"Unknown element symbol: {sym!r}")


# ---------------------------------------------------------------------------
# LAMMPS data-file parser
# ---------------------------------------------------------------------------
# Column index of the atom-type and of the first coordinate in an Atoms row,
# per atom_style. Any image flags (ix iy iz) after z are ignored.
_ATOMS_LAYOUT = {
    "atomic": (1, 2),  # id type x y z
    "charge": (1, 3),  # id type q x y z
    "full": (2, 4),  # id mol type charge x y z
}


def parse_lammps_data(path, atom_style="full"):
    """
    Parse a LAMMPS data file's Atoms section for the given ``atom_style``.

    SEAMM writes ``atom_style atomic`` for the MDI/QM path (the molecule id is
    carried separately via ``fix property/atom``), so the Atoms columns are
    ``id type x y z`` -- not the ``id mol type charge x y z`` of ``full``. The
    column layout is selected from ``atom_style`` (``atomic`` / ``charge`` /
    ``full``); unknown styles fall back to ``full``.

    Returns
    -------
    natoms      : int
    atom_types  : np.ndarray(natoms, int)   1-indexed LAMMPS type per atom
    positions   : np.ndarray((natoms,3))     Angstroms, sorted by atom-ID
    cell        : np.ndarray((3,3))          Angstroms, diagonal for ortho box
    is_periodic : bool
    """
    type_col, x_col = _ATOMS_LAYOUT.get(atom_style, _ATOMS_LAYOUT["full"])
    min_cols = x_col + 3

    natoms = 0
    cell = np.zeros((3, 3))
    is_periodic = False
    atom_rows = {}  # atom_id -> (type, x, y, z)

    with open(path) as fh:
        in_atoms = False
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                in_atoms = False if line.startswith("#") else in_atoms
                continue

            # Header integer counts
            if not in_atoms:
                toks = line.split()
                if len(toks) >= 2 and toks[0].isdigit():
                    # Match "102 atoms" exactly (not "4 atom types")
                    if toks[1] == "atoms":
                        natoms = int(toks[0])

                # Orthogonal box dimensions
                if "xlo xhi" in line:
                    lo, hi = float(toks[0]), float(toks[1])
                    cell[0, 0] = hi - lo
                    is_periodic = True
                elif "ylo yhi" in line:
                    lo, hi = float(toks[0]), float(toks[1])
                    cell[1, 1] = hi - lo
                elif "zlo zhi" in line:
                    lo, hi = float(toks[0]), float(toks[1])
                    cell[2, 2] = hi - lo

                # Atoms section trigger
                if line.startswith("Atoms"):
                    in_atoms = True
                    continue

            else:
                toks = line.split()
                if len(toks) >= min_cols and toks[0].isdigit():
                    aid = int(toks[0])
                    atype = int(toks[type_col])
                    x, y, z = (
                        float(toks[x_col]),
                        float(toks[x_col + 1]),
                        float(toks[x_col + 2]),
                    )
                    atom_rows[aid] = (atype, x, y, z)

    # Build sorted arrays (atom-IDs may not be contiguous in file order)
    atom_types = np.zeros(natoms, dtype=int)
    positions = np.zeros((natoms, 3))
    for aid in sorted(atom_rows):
        idx = aid - 1
        atype, x, y, z = atom_rows[aid]
        atom_types[idx] = atype
        positions[idx] = [x, y, z]

    # Catch a column-layout mismatch loudly rather than as a later KeyError.
    if natoms and (atom_types == 0).any():
        n0 = int((atom_types == 0).sum())
        raise ValueError(
            f"{n0} of {natoms} atoms in {path!r} had no type parsed with "
            f"atom_style={atom_style!r}; the Atoms-section columns do not match "
            "that style. Check the LAMMPS atom_style or pass --atom-style."
        )

    return natoms, atom_types, positions, cell, is_periodic


# ---------------------------------------------------------------------------
# Type -> element map from the LAMMPS input deck
# ---------------------------------------------------------------------------
def elements_from_input(path):
    """Read the per-type element symbols from a LAMMPS input deck.

    Finds the ``fix ... mdi/qm ... elements <sym> <sym> ...`` line (the same
    line the LAMMPS step writes) and returns the symbols after the ``elements``
    keyword, in type order. This lets the engine self-derive the type->element
    map instead of being told it on the command line.

    Returns
    -------
    list of str

    Raises
    ------
    ValueError
        If no ``mdi/qm`` fix with an ``elements`` keyword is found.
    """
    with open(path) as fh:
        for raw in fh:
            toks = raw.split()
            if "mdi/qm" in toks and "elements" in toks:
                i = toks.index("elements")
                syms = toks[i + 1 :]
                if syms:
                    return syms
    raise ValueError(
        f"Could not find a 'fix ... mdi/qm ... elements ...' line in {path!r}; "
        "pass --elements explicitly."
    )


def atom_style_from_input(path):
    """Return the ``atom_style`` declared in a LAMMPS input deck, or None.

    Lets the engine parse ``structure.dat`` with the right columns without
    being told the style on the command line. Returns None if the file is
    missing or declares no atom_style.
    """
    try:
        with open(path) as fh:
            for raw in fh:
                toks = raw.split()
                if len(toks) >= 2 and toks[0] == "atom_style":
                    return toks[1]
    except OSError:
        pass
    return None


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
        "--structure",
        required=True,
        metavar="FILE",
        help="LAMMPS data file (atom_style full) for initial system setup",
    )
    p.add_argument(
        "--input",
        default="input.dat",
        metavar="FILE",
        help="LAMMPS input deck to read the type->element map and atom_style "
        'from (the "fix ... mdi/qm ... elements ..." and "atom_style" lines; '
        "default: input.dat). Used when --elements / --atom-style are absent.",
    )
    p.add_argument(
        "--atom-style",
        default=None,
        metavar="STYLE",
        help="LAMMPS atom_style of --structure (atomic/charge/full). If "
        "omitted, read from --input, else assumed 'full'.",
    )
    p.add_argument(
        "--elements",
        nargs="+",
        metavar="SYM",
        default=None,
        help="Element symbol for each LAMMPS atom type in order "
        "(e.g. --elements C O H H  maps type1->C, type2->O, type3->H, "
        "type4->H). Optional: if omitted, the symbols are read from the "
        '"elements" keyword on the fix mdi/qm line in --input.',
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
        "--uhf", type=int, default=0, help="Number of unpaired electrons (default: 0)"
    )
    p.add_argument(
        "--verbosity",
        type=int,
        default=0,
        help="tblite output verbosity: 0=silent, 1=minimal, 2=full (default: 0)",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Internal: run tblite singlepoint and cache result
# ---------------------------------------------------------------------------
def _run_singlepoint(
    calc, coords_bohr, cell_flat, is_periodic, verbosity, prev_result=None
):
    """Update geometry and run tblite singlepoint. Returns result object.

    Pass prev_result to warm-start the SCF from the previous step's
    converged electron density. On the first call leave it as None and
    tblite will build a SAD (superposition of atomic densities) guess.
    """
    pos = coords_bohr.reshape(-1, 3)
    lat = cell_flat.reshape(3, 3) if is_periodic else None
    calc.update(positions=pos, lattice=lat)
    # res=prev_result: restart from previous density (None → cold SAD start)
    # copy=False:      update result in-place rather than allocating a copy
    result = calc.singlepoint(res=prev_result, copy=False)
    if verbosity >= 0:
        print(f"[tblite-mdi]   energy = {result.get('energy'):.10f} Ha", flush=True)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()

    # Per-type element symbols: from --elements if given, otherwise read the
    # fix mdi/qm "elements" line out of the LAMMPS input deck.
    elements = args.elements
    if elements is None:
        elements = elements_from_input(args.input)
        print(
            f"[tblite-mdi] elements from {args.input}: {' '.join(elements)}", flush=True
        )

    # Build LAMMPS-type → atomic-number map
    type_to_z = {i + 1: symbol_to_z(sym) for i, sym in enumerate(elements)}

    # atom_style of structure.dat: explicit --atom-style, else read it from the
    # input deck (SEAMM writes "atom_style atomic"), else assume "full".
    atom_style = args.atom_style or atom_style_from_input(args.input) or "full"

    # Parse structure file
    print(
        f"[tblite-mdi] Reading structure: {args.structure} (atom_style={atom_style})",
        flush=True,
    )
    natoms, atom_types_arr, positions_ang, cell_ang, is_periodic = parse_lammps_data(
        args.structure, atom_style
    )
    print(f"[tblite-mdi] {natoms} atoms, periodic={is_periodic}", flush=True)

    # Per-atom atomic numbers (from LAMMPS type → element symbol → Z)
    atomic_numbers = np.array([type_to_z[t] for t in atom_types_arr], dtype=int)

    # Conversion: tblite.interface uses Bohr, MDI uses Bohr → no conversion
    # for coordinates/lattice. MDI energy in Hartree, tblite in Hartree → same.
    ANG_TO_BOHR = 1.0 / 0.529177210903

    positions_bohr = positions_ang * ANG_TO_BOHR
    cell_bohr = cell_ang * ANG_TO_BOHR

    # ----------------------------------------------------------------
    # Import mdi and tblite (deferred so --help works without them)
    # ----------------------------------------------------------------
    try:
        import mdi
    except ImportError:
        sys.exit(
            "[tblite-mdi] ERROR: mdi not found. " "conda install -c conda-forge pymdi"
        )
    try:
        from tblite.interface import Calculator
    except ImportError:
        sys.exit(
            "[tblite-mdi] ERROR: tblite not found. "
            "conda install -c conda-forge tblite-python"
        )

    # ----------------------------------------------------------------
    # MDI initialisation
    # ----------------------------------------------------------------
    mdi.MDI_Init(args.mdi)
    comm = mdi.MDI_Accept_Communicator()

    # Register @DEFAULT node and all commands we support so that LAMMPS
    # can discover our capabilities via MDI_Check_command before sending.
    # Without registration, LAMMPS gets "node not found" and aborts.
    # Registering <NATOMS (engine sends count) makes LAMMPS prefer that
    # path over >NATOMS (driver sends count), matching MOPAC's behaviour.
    mdi.MDI_Register_node("@DEFAULT")
    for _cmd in [
        "<NATOMS",  # engine sends natoms to driver (preferred path)
        ">NATOMS",  # driver sends natoms to engine (fallback path)
        "<NAME",  # engine sends its name
        ">ELEMENTS",  # driver sends atomic numbers
        ">COORDS",  # driver sends coordinates (Bohr)
        ">CELL",  # driver sends cell matrix (Bohr)
        "SCF",  # driver triggers energy+force calculation
        "<ENERGY",  # driver requests energy (Hartree)
        "<FORCES",  # driver requests forces (Hartree/Bohr)
        "<STRESS",  # driver requests stress tensor (Hartree/Bohr³)
        "EXIT",  # driver signals end of simulation
    ]:
        mdi.MDI_Register_command("@DEFAULT", _cmd)

    print(
        f"[tblite-mdi] MDI connection established. "
        f"method={args.method}, natoms={natoms}",
        flush=True,
    )

    # ----------------------------------------------------------------
    # Create tblite Calculator
    # tblite.interface units throughout:
    #   positions / lattice : Bohr
    #   energy              : Hartree
    #   gradient            : Hartree/Bohr  (= dE/dx; force = -gradient)
    #   virial              : Hartree        (extensive, 3×3)
    # ----------------------------------------------------------------
    calc = Calculator(
        method=args.method,
        numbers=atomic_numbers,
        positions=positions_bohr,
        lattice=cell_bohr if is_periodic else None,
        periodic=np.array([True, True, True]) if is_periodic else None,
        charge=float(args.charge),
        uhf=args.uhf,
    )
    calc.set("verbosity", args.verbosity)

    # Working arrays updated in the event loop
    coords_bohr = positions_bohr.copy().ravel()  # (3*natoms,)  Bohr
    cell_flat = cell_bohr.ravel().copy()  # (9,)         Bohr
    result = None
    recompute = True

    # ----------------------------------------------------------------
    # MDI event loop
    # ----------------------------------------------------------------
    print("[tblite-mdi] Entering MDI event loop ...", flush=True)

    while True:
        command = mdi.MDI_Recv_Command(comm)
        print(f"[tblite-mdi] command: {command!r}", flush=True)

        # ---- Metadata -----------------------------------------------
        if command == "<NATOMS":
            # LAMMPS requests natoms FROM engine; engine responds.
            # This is the preferred path when <NATOMS is registered.
            mdi.MDI_Send(natoms, 1, mdi.MDI_INT, comm)

        elif command == ">NATOMS":
            # Fallback: LAMMPS sends its natoms TO engine for verification.
            # Used if <NATOMS is not registered. We must read the payload
            # or the socket state is corrupted for all subsequent commands.
            raw = mdi.MDI_Recv(1, mdi.MDI_INT, comm)
            lammps_natoms = int(np.asarray(raw).flat[0])
            if lammps_natoms != natoms:
                raise RuntimeError(
                    f">NATOMS mismatch: LAMMPS has {lammps_natoms} atoms, "
                    f"engine has {natoms} atoms"
                )
            print(f"[tblite-mdi]   >NATOMS verified: {lammps_natoms}", flush=True)

        elif command == "<NAME":
            mdi.MDI_Send("TBLITE", mdi.MDI_NAME_LENGTH, mdi.MDI_CHAR, comm)

        # ---- Coordinate and cell updates from LAMMPS ----------------
        elif command == ">COORDS":
            # LAMMPS sends 3*natoms doubles in Bohr, row-major (x1 y1 z1 ...)
            raw = mdi.MDI_Recv(3 * natoms, mdi.MDI_DOUBLE, comm)
            coords_bohr[:] = np.asarray(raw)
            recompute = True

        elif command == ">CELL":
            # LAMMPS sends 9 doubles (3×3 cell row-major) in Bohr
            raw = mdi.MDI_Recv(9, mdi.MDI_DOUBLE, comm)
            cell_flat[:] = np.asarray(raw)
            recompute = True

        elif command == ">ELEMENTS":
            # LAMMPS may send one int per atom (atomic number) for
            # verification; receive and discard (we already have from file)
            mdi.MDI_Recv(natoms, mdi.MDI_INT, comm)
            print(
                "[tblite-mdi]   >ELEMENTS received (using file-based elements)",
                flush=True,
            )

        # ---- SCF trigger --------------------------------------------
        elif command == "SCF":
            # Explicit SCF trigger from LAMMPS.  Run if geometry changed.
            if recompute:
                result = _run_singlepoint(
                    calc,
                    coords_bohr,
                    cell_flat,
                    is_periodic,
                    args.verbosity,
                    prev_result=result,
                )
                recompute = False

        # ---- Property requests from LAMMPS --------------------------
        elif command == "<ENERGY":
            # Run lazily if LAMMPS did not send an explicit SCF command
            if recompute:
                result = _run_singlepoint(
                    calc,
                    coords_bohr,
                    cell_flat,
                    is_periodic,
                    args.verbosity,
                    prev_result=result,
                )
                recompute = False
            # tblite returns energy in Hartree → MDI expects Hartree: no conversion
            mdi.MDI_Send(result.get("energy"), 1, mdi.MDI_DOUBLE, comm)

        elif command == "<FORCES":
            if result is None:
                raise RuntimeError("<FORCES requested before any SCF")
            # tblite returns gradient (dE/dx) in Hartree/Bohr
            # MDI <FORCES convention: force = -dE/dx  → negate
            forces = -result.get("gradient").ravel()  # (3*natoms,) Ha/Bohr
            mdi.MDI_Send(forces, 3 * natoms, mdi.MDI_DOUBLE, comm)

        elif command == "<STRESS":
            if result is None:
                raise RuntimeError("<STRESS requested before any SCF")
            # tblite virial tensor W (Hartree, 3×3, extensive).
            # Intensive Cauchy stress σ = -W / V  (tensile positive, Ha/Bohr³).
            # Sign vs MDI/LAMMPS convention: empirically verified by the
            # compress/expand test (see in.tblite_stress_check).
            # If compressed box gives *lower* press than expanded box, flip sign
            # here: change  -virial  →  +virial.
            virial = result.get("virial")  # (3,3) Hartree
            volume = abs(np.linalg.det(cell_flat.reshape(3, 3)))  # Bohr³
            stress = -virial / volume  # Ha/Bohr³  (tensile+)
            # Debug: uncomment to cross-check magnitude during stress test
            # print(f"[tblite-mdi]   virial diag (Ha): "
            #       f"{virial[0,0]:.6f} {virial[1,1]:.6f} {virial[2,2]:.6f}",
            #       flush=True)
            # print(f"[tblite-mdi]   stress diag (Ha/Bohr³): "
            #       f"{stress[0,0]:.6e} {stress[1,1]:.6e} {stress[2,2]:.6e}",
            #       flush=True)
            mdi.MDI_Send(stress.ravel(), 9, mdi.MDI_DOUBLE, comm)

        # ---- Shutdown -----------------------------------------------
        elif command == "EXIT":
            print("[tblite-mdi] EXIT — shutting down.", flush=True)
            break

        else:
            print(f"[tblite-mdi] WARNING: unrecognised command {command!r}", flush=True)

    print("[tblite-mdi] Done.", flush=True)


if __name__ == "__main__":
    main()
