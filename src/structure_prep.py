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

# --- Alignment landmarks: mutation-INDEPENDENT residues to superpose on ---
# Rationale (Claude Science structural audit, docs/scope.md §6.1): a radius-based pocket
# selection can include the mutated residue in the set used to *align* the structures —
# circular, since we'd partly be fitting on the very thing we're trying to measure. Instead
# fit on fixed anatomical landmarks that don't move with these mutations, and treat the
# mutated sidechain as a MEASURED quantity, never a fitting one.
#
# EGFR kinase invariants, verified against the deposited numbering of 3POZ/8A2B/4I24/5UGC
# (identical across all four; zero insertion codes). Residue 790 (the T790M gatekeeper) is
# DELIBERATELY EXCLUDED — it's the mutation itself, and 5UGC models it in two altLocs.
EGFR_LANDMARKS = frozenset(
    [745, 762]                       # β3 Lys – αC Glu salt bridge
    + list(range(791, 798))          # hinge backbone 791–797 (790 gatekeeper excluded)
    + [835, 836, 837]                # catalytic HRD motif
    + [855, 856, 857]                # DFG motif
)
# KRAS is a small rigid GTPase (no hinge-breathing), so it already aligns tightly. Fit on the
# rigid core but EXCLUDE the mutation (12) and the mobile/induced-fit switch regions
# (switch-I 30–38, switch-II 60–76) so those are measured, not fitted.
KRAS_ALIGN_EXCLUDE = frozenset({12} | set(range(30, 39)) | set(range(60, 77)))


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


def matched_ca(ref_struct, mob_struct, ref_chain, mob_chain, restrict=None, exclude=None):
    """CA atom pairs sharing the same residue number.
    `restrict`: keep only these resnums. `exclude`: drop these resnums."""
    ref_ca = ca_by_resnum(ref_struct, ref_chain)
    mob_ca = ca_by_resnum(mob_struct, mob_chain)
    common = sorted(set(ref_ca) & set(mob_ca))
    if restrict is not None:
        common = [i for i in common if i in restrict]
    if exclude is not None:
        common = [i for i in common if i not in exclude]
    return [ref_ca[i] for i in common], [mob_ca[i] for i in common], common


def ca_rmsd_over(ref_struct, mob_struct, ref_chain, mob_chain, resnums):
    """CA RMSD over specific residues in the CURRENT coordinates (no re-fit).
    Used as a pocket-agreement READOUT after superposing on the landmark set —
    i.e. 'given a mutation-independent fit, how well does the pocket line up?'"""
    ref_ca = ca_by_resnum(ref_struct, ref_chain)
    mob_ca = ca_by_resnum(mob_struct, mob_chain)
    common = [i for i in resnums if i in ref_ca and i in mob_ca]
    if not common:
        return None, 0
    d2 = [np.sum((ref_ca[i].coord - mob_ca[i].coord) ** 2) for i in common]
    return float(np.sqrt(np.mean(d2))), len(common)


def alignment_resnums(target, ref_struct, mob_struct, ref_chain, mob_chain):
    """The mutation-independent resnums to fit on, per target."""
    if target == "EGFR":
        return matched_ca(ref_struct, mob_struct, ref_chain, mob_chain, restrict=EGFR_LANDMARKS)
    return matched_ca(ref_struct, mob_struct, ref_chain, mob_chain, exclude=KRAS_ALIGN_EXCLUDE)


def main():
    os.makedirs(PREP, exist_ok=True)
    parser = PDBParser(QUIET=True)
    io = PDBIO()

    # Load all raw structures once.
    raw = {pdb: parser.get_structure(pdb, f"{RAW}/{pdb}.pdb") for pdb in STRUCTS}

    # --- Superpose every structure onto its target's reference frame, fitting on
    #     mutation-INDEPENDENT landmarks (EGFR kinase invariants / KRAS rigid core). ---
    transforms = {}
    for pdb, cfg in STRUCTS.items():
        target = cfg["target"]
        ref_pdb = TARGET_REF[target]["align_to"]
        if pdb == ref_pdb:
            transforms[pdb] = "reference"
            continue

        # global fit (all CA) — reported as a diagnostic only, never used for the transform
        ga_ref, ga_mob, _ = matched_ca(raw[ref_pdb], raw[pdb], STRUCTS[ref_pdb]["chain"], cfg["chain"])
        gsup = Superimposer(); gsup.set_atoms(ga_ref, ga_mob); global_rms = gsup.rms

        # landmark fit (the actual transform) — mutation-independent anchors only
        la_ref, la_mob, lcommon = alignment_resnums(
            target, raw[ref_pdb], raw[pdb], STRUCTS[ref_pdb]["chain"], cfg["chain"]
        )
        sup = Superimposer(); sup.set_atoms(la_ref, la_mob)
        sup.apply(raw[pdb].get_atoms())  # move whole mobile structure into ref frame
        transforms[pdb] = dict(
            fit="EGFR_landmarks" if target == "EGFR" else "KRAS_core",
            n_landmark_ca=len(lcommon),
            rmsd_landmark=round(sup.rms, 3),
            rmsd_global_allCA=round(global_rms, 3),
        )
        print(f"  aligned {pdb} -> {ref_pdb}: {len(lcommon)} landmark CA, LANDMARK RMSD {sup.rms:.3f} Å  (global all-CA {global_rms:.3f} Å)")

    # --- Pocket-agreement READOUT (after landmark fit; not used for fitting) ---
    # 'Given a mutation-independent alignment, how well does the pocket itself line up?'
    # Pocket residues picked on the reference (now in the aligned frame) near the pocket ligand.
    for target, ref in TARGET_REF.items():
        ref_pdb = ref["align_to"]
        center = ligand_centroid(raw[ref["pocket_from"]], STRUCTS[ref["pocket_from"]]["chain"],
                                 STRUCTS[ref["pocket_from"]]["ref_ligand"])  # aligned frame
        pkt_nums = pocket_resnums(raw[ref_pdb], STRUCTS[ref_pdb]["chain"], center, radius=12.0)
        for pdb, cfg in STRUCTS.items():
            if cfg["target"] != target or pdb == ref_pdb:
                continue
            rms, n = ca_rmsd_over(raw[ref_pdb], raw[pdb], STRUCTS[ref_pdb]["chain"], cfg["chain"], pkt_nums)
            transforms[pdb]["rmsd_pocket_readout"] = round(rms, 3) if rms is not None else None
            transforms[pdb]["n_pocket_readout"] = n
            print(f"  pocket readout {pdb}: {rms:.3f} Å over {n} pocket CA (post-landmark-fit)")

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
