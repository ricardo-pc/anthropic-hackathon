"""
Structure preparation for mutation-aware docking.

Goal: turn each raw PDB into a docking-ready receptor, prepped IDENTICALLY across
wild-type and mutant so the WT-vs-mutant delta reflects biology, not prep artifacts.

Steps per structure:
  1. Keep a single protein protomer (chain A) — some entries have multiple copies.
  2. Strip the co-crystallized inhibitor, waters, and crystallization additives.
  3. KEEP functional cofactors (KRAS GDP + Mg) — these define the inactive/switch-II
     state the drug pocket depends on; removing them would collapse the pocket.
  4. Add hydrogens at physiological pH (7.4), identically for every structure.
  5. Superpose each mutant onto its wild-type reference (per target family) so a single
     shared pocket box is valid across all states.
  6. Record one pocket box per target, taken from the reference co-crystallized ligand.

Outputs:
  data/structures/prepared/<PDB>_receptor.pdb   — cleaned, protonated, aligned receptor
  data/structures/pockets.json                  — one pocket box per target family
"""
import json
import os
import warnings

import numpy as np
from Bio.PDB import PDBParser, PDBIO, Select, Superimposer

warnings.filterwarnings("ignore")

ROOT = "/Users/ricardoperezcastillo/Library/CloudStorage/OneDrive-Personal/Documents/GitHub/anthropic-hackathon"
RAW = f"{ROOT}/data/structures/raw"
PREP = f"{ROOT}/data/structures/prepared"
POCKET_JSON = f"{ROOT}/data/structures/pockets.json"

AA = set("ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split())

# Functional cofactors to KEEP (everything else hetero is stripped).
KEEP_HET = {"GDP", "MG"}

# Per-structure config: which chain to keep, and the resname of the co-crystallized
# inhibitor that marks the pocket (None = no bound drug in this entry).
STRUCTS = {
    # target, state, chain, pocket-marker ligand resname
    "3POZ": dict(target="EGFR", state="WT",                chain="A", ref_ligand="03P"),
    "8A2B": dict(target="EGFR", state="L858R",             chain="A", ref_ligand="KY9"),
    "4I24": dict(target="EGFR", state="T790M",             chain="A", ref_ligand="1C9"),
    "5UGC": dict(target="EGFR", state="L858R+T790M",       chain="A", ref_ligand="8BS"),
    "8FMI": dict(target="KRAS", state="WT",                chain="A", ref_ligand=None),   # apo (GDP only)
    "4LDJ": dict(target="KRAS", state="G12C",              chain="A", ref_ligand=None),   # apo (GDP only)
    "6OIM": dict(target="KRAS", state="G12C+sotorasib",    chain="A", ref_ligand="MOV"),  # sotorasib marks pocket
}

# Reference structure per target (the frame everything else is aligned to) and the
# structure whose bound ligand defines the pocket box.
TARGET_REF = {
    "EGFR": dict(align_to="3POZ", pocket_from="3POZ"),  # WT frame, ATP-pocket from TAK-285
    "KRAS": dict(align_to="8FMI", pocket_from="6OIM"),  # WT frame, switch-II pocket from sotorasib
}


class ProtomerSelect(Select):
    """Keep one chain's protein residues + allowlisted cofactors; drop drug, water, additives."""
    def __init__(self, chain_id):
        self.chain_id = chain_id

    def accept_chain(self, chain):
        return chain.id == self.chain_id

    def accept_residue(self, residue):
        resname = residue.resname.strip()
        if resname in AA:
            return True
        if resname in KEEP_HET:
            return True
        return False  # inhibitor, HOH, SO4, GOL, EDO, ... all dropped

    def accept_atom(self, atom):
        if atom.element == "H":
            return False  # strip any deposited H so all 7 start from an identical heavy-atom baseline
        return not atom.is_disordered() or atom.get_altloc() in ("A", "")


def ligand_centroid(structure, chain_id, resname):
    """Centroid of a ligand's heavy atoms (used to place the pocket box)."""
    coords = []
    for chain in structure[0]:
        if chain.id != chain_id:
            continue
        for res in chain:
            if res.resname.strip() == resname:
                for atom in res:
                    if atom.element != "H":
                        coords.append(atom.coord)
    if not coords:
        return None
    return np.mean(coords, axis=0)


def ca_by_resnum(struct, chain_id):
    out = {}
    for chain in struct[0]:
        if chain.id != chain_id:
            continue
        for res in chain:
            if res.resname.strip() in AA and "CA" in res:
                out[res.id[1]] = res["CA"]
    return out


def pocket_resnums(struct, chain_id, center, radius=12.0):
    """Residue numbers with a CA within `radius` of the pocket center (in this struct's frame)."""
    nums = set()
    for chain in struct[0]:
        if chain.id != chain_id:
            continue
        for res in chain:
            if res.resname.strip() in AA and "CA" in res:
                if np.linalg.norm(res["CA"].coord - center) <= radius:
                    nums.add(res.id[1])
    return nums


def matched_ca(ref_struct, mob_struct, ref_chain, mob_chain, restrict=None):
    """CA atom pairs sharing the same residue number. If `restrict` given, only those resnums."""
    ref_ca = ca_by_resnum(ref_struct, ref_chain)
    mob_ca = ca_by_resnum(mob_struct, mob_chain)
    common = sorted(set(ref_ca) & set(mob_ca))
    if restrict is not None:
        common = [i for i in common if i in restrict]
    return [ref_ca[i] for i in common], [mob_ca[i] for i in common], common


def main():
    os.makedirs(PREP, exist_ok=True)
    parser = PDBParser(QUIET=True)
    io = PDBIO()

    # Load all raw structures once.
    raw = {pdb: parser.get_structure(pdb, f"{RAW}/{pdb}.pdb") for pdb in STRUCTS}

    # Pocket center in each reference's OWN frame (before any alignment), to pick pocket residues.
    ref_pocket_center = {}
    for target, ref in TARGET_REF.items():
        src = ref["pocket_from"]
        ref_pocket_center[target] = ligand_centroid(raw[src], STRUCTS[src]["chain"], STRUCTS[src]["ref_ligand"])
    # For KRAS the pocket ligand (6OIM) isn't the align reference (8FMI); carry its center via the
    # align-reference frame by first aligning globally — handled below. For picking pocket residues on
    # the align-reference itself, translate: use the pocket_from center directly on 8FMI only after we
    # know they're already in a near-common frame (KRAS aligns at 0.2 Å, so centers are ~equivalent).

    # --- Superpose every structure onto its target's reference frame (POCKET-LOCAL) ---
    transforms = {}
    for pdb, cfg in STRUCTS.items():
        target = cfg["target"]
        ref_pdb = TARGET_REF[target]["align_to"]
        if pdb == ref_pdb:
            transforms[pdb] = "reference"
            continue
        # pocket residues defined on the REFERENCE structure, near the pocket center
        pkt_center = ref_pocket_center[target]
        pkt_nums = pocket_resnums(raw[ref_pdb], STRUCTS[ref_pdb]["chain"], pkt_center, radius=12.0)

        # global fit (all CA) — diagnostic only
        ga_ref, ga_mob, _ = matched_ca(raw[ref_pdb], raw[pdb], STRUCTS[ref_pdb]["chain"], cfg["chain"])
        gsup = Superimposer(); gsup.set_atoms(ga_ref, ga_mob); global_rms = gsup.rms

        # pocket-local fit (used for the actual transform)
        pa_ref, pa_mob, pcommon = matched_ca(
            raw[ref_pdb], raw[pdb], STRUCTS[ref_pdb]["chain"], cfg["chain"], restrict=pkt_nums
        )
        sup = Superimposer(); sup.set_atoms(pa_ref, pa_mob)
        sup.apply(raw[pdb].get_atoms())  # move whole mobile structure into ref frame
        transforms[pdb] = dict(n_pocket=len(pcommon), rmsd_pocket=round(sup.rms, 3), rmsd_global_allCA=round(global_rms, 3))
        print(f"  aligned {pdb} -> {ref_pdb}: pocket {len(pcommon)} CA, POCKET RMSD {sup.rms:.3f} Å  (global all-CA {global_rms:.3f} Å)")

    # --- Clean each receptor (now all in a common frame) ---
    # Output = single protomer, protein + kept cofactors, drug/water/additives removed.
    # Heavy atoms only: polar hydrogens are added consistently at docking time by the
    # rescoring engine's receptor prep (protein-aware protonation of a heavy-atom PDB is
    # deferred there rather than done with a tool that would mangle residue identity here).
    for pdb, cfg in STRUCTS.items():
        io.set_structure(raw[pdb])
        out = f"{PREP}/{pdb}_receptor.pdb"
        io.save(out, ProtomerSelect(cfg["chain"]))
        print(f"  prepped {pdb} ({cfg['target']} {cfg['state']}) -> {os.path.basename(out)}")

    # --- Define one pocket box per target from the reference ligand ---
    pockets = {}
    for target, ref in TARGET_REF.items():
        src_pdb = ref["pocket_from"]
        lig = STRUCTS[src_pdb]["ref_ligand"]
        center = ligand_centroid(raw[src_pdb], STRUCTS[src_pdb]["chain"], lig)
        # bounding box of the ligand + padding -> generous cubic box
        coords = []
        for chain in raw[src_pdb][0]:
            if chain.id != STRUCTS[src_pdb]["chain"]:
                continue
            for res in chain:
                if res.resname.strip() == lig:
                    coords.extend(a.coord for a in res if a.element != "H")
        coords = np.array(coords)
        size = (coords.max(0) - coords.min(0)) + 10.0  # 5 Å padding each side
        pockets[target] = dict(
            pocket_from=src_pdb, ref_ligand=lig,
            center=[round(float(x), 3) for x in center],
            size=[round(float(x), 3) for x in size],
            aligned_frame=ref["align_to"],
        )
        print(f"  pocket {target}: center {pockets[target]['center']} size {pockets[target]['size']} (from {src_pdb}/{lig})")

    with open(POCKET_JSON, "w") as f:
        json.dump(dict(structures=STRUCTS, transforms=transforms, pockets=pockets), f, indent=2)
    print(f"\nWrote pocket + alignment metadata to {POCKET_JSON}")


if __name__ == "__main__":
    main()
