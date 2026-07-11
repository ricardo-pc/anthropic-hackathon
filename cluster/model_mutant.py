#!/usr/bin/env python3
"""
Model a point-mutant structure from the wild-type by side-chain substitution.

Given a prepared wild-type receptor and a point mutation (e.g. "G719S"), swap residue 719's side
chain to serine and write the mutant PDB. This is the "any point mutation" step: it lets the tool
dock a genotype we have no crystal structure for. A side-chain swap is a fast, standard approximation
(what a bench scientist does for a quick model) — NOT a crystal structure, so the tool labels any
result built on it as "modeled structure, lower confidence".

Runs inside the GPU docking image (alongside DiffDock + gnina), where PyMOL is installed. Uses the
PyMOL mutagenesis wizard (picks the most common rotamer). Verifies the wild-type residue identity
first, so a typo'd mutation fails loudly instead of silently modeling the wrong thing.

CLI:  python cluster/model_mutant.py <wt.pdb> <mutation> <out.pdb>   e.g.  ... 3POZ_receptor.pdb G719S mut.pdb
"""
import re
import sys

AA3 = {"A": "ALA", "R": "ARG", "N": "ASN", "D": "ASP", "C": "CYS", "E": "GLU", "Q": "GLN",
       "G": "GLY", "H": "HIS", "I": "ILE", "L": "LEU", "K": "LYS", "M": "MET", "F": "PHE",
       "P": "PRO", "S": "SER", "T": "THR", "W": "TRP", "Y": "TYR", "V": "VAL"}


def parse_mutation(mut):
    """'G719S' -> ('G', 719, 'S'). Raises on anything that isn't a single-residue substitution."""
    m = re.fullmatch(r"([A-Z])(\d+)([A-Z])", mut.strip().upper())
    if not m or m.group(1) not in AA3 or m.group(3) not in AA3:
        raise ValueError(f"{mut!r} is not a valid point mutation like 'G719S'")
    return m.group(1), int(m.group(2)), m.group(3)


def model_mutant(wt_pdb, mutation, out_pdb, chain="A"):
    """Write a mutant PDB with residue <pos> changed to <to> via PyMOL's mutagenesis wizard."""
    try:
        import pymol2
    except ImportError:
        raise RuntimeError(
            "PyMOL not available. This step runs in the GPU docking image; install it there with "
            "`conda install -c conda-forge pymol-open-source` (or `pip install pymol-open-source`).")
    frm, pos, to = parse_mutation(mutation)
    with pymol2.PyMOL() as p:
        cmd = p.cmd
        cmd.load(wt_pdb, "wt")
        got = cmd.get_model(f"chain {chain} and resi {pos} and name CA").atom
        if not got:
            raise ValueError(f"no residue {pos} in chain {chain} of {wt_pdb}")
        have = got[0].resn
        if have != AA3[frm]:
            raise ValueError(f"wild-type residue {pos} is {have}, not {AA3[frm]} — mutation {mutation} "
                             f"doesn't match this structure (wrong isoform/numbering?)")
        cmd.wizard("mutagenesis")
        cmd.refresh_wizard()
        cmd.get_wizard().set_mode(AA3[to])
        cmd.get_wizard().do_select(f"chain {chain} and resi {pos}")
        cmd.get_wizard().apply()
        cmd.set_wizard()
        cmd.save(out_pdb, "wt")
    return out_pdb


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    out = model_mutant(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"wrote {out}")
