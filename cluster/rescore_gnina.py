#!/usr/bin/env python3
"""
gnina rescore of every DiffDock rank1 pose -> the affinity proxy the four-bucket
classification actually rests on (DiffDock confidence is a pose-quality measure, not
affinity -- see docs/docking_score_notes.md).

For each of the 189 result folders (<drug>__<pdb>/), rescore rank1.sdf against its
receptor with `gnina --minimize` -- a LOCAL relaxation (small in-pocket nudges) then
score. This is NOT re-docking (no global search, no box); it relieves the minor steric
clashes DiffDock's raw poses carry. Confirmed necessary: `--score_only` on the raw pose
gave a spurious POSITIVE affinity (+0.27) for erlotinib vs its own target WT-EGFR; after
`--minimize` it's -7.2 kcal/mol, as expected. We also capture the minimization RMSD (how
far the pose moved) as a QC field -- a large RMSD means the raw pose needed a big fix.

Stdlib only. Run via rescore.sbatch (GPU, for CNN scoring).
"""
import csv
import glob
import os
import re
import subprocess

HOME = os.path.expanduser("~")
SWEEP = f"{HOME}/hackathon/results/full_sweep"
RECEPTORS = f"{HOME}/hackathon/data/structures/prepared"
GNINA = f"{HOME}/hackathon/bin/gnina"
DRUGS = f"{HOME}/hackathon/data/drugs.csv"
OUT = f"{HOME}/hackathon/results/gnina_scores.csv"

# pdb -> (target, state), mirrors docs/scope.md
PDB_META = {
    "3POZ": ("EGFR", "WT"),
    "8A2B": ("EGFR", "L858R"),
    "4I24": ("EGFR", "T790M"),
    "5UGC": ("EGFR", "L858R+T790M"),
    "8FMI": ("KRAS", "WT"),
    "4LDJ": ("KRAS", "G12C"),
    "6OIM": ("KRAS", "G12C+sotorasib"),
}


def load_drug_categories():
    cat = {}
    with open(DRUGS) as f:
        for row in csv.DictReader(f):
            cat[row["name"]] = row["category"]
    return cat


def parse_scores(text):
    def grab(pat):
        m = re.search(pat, text)
        return float(m.group(1)) if m else None
    # With --minimize the Affinity line is "Affinity: <affinity> <intramol> (kcal/mol)";
    # the first number is the binding affinity we want.
    return dict(
        gnina_affinity=grab(r"Affinity:\s*(-?\d+\.?\d*)"),        # kcal/mol, more negative = better
        gnina_minimize_rmsd=grab(r"RMSD:\s*(-?\d+\.?\d*)"),       # QC: how far --minimize moved the pose
        gnina_cnn_score=grab(r"CNNscore:\s*(-?\d+\.?\d*)"),       # 0-1 pose quality, higher = better
        gnina_cnn_affinity=grab(r"CNNaffinity:\s*(-?\d+\.?\d*)"), # predicted pK, higher = better
    )


def diffdock_confidence(folder_path):
    for g in glob.glob(f"{folder_path}/rank1_confidence*.sdf"):
        m = re.search(r"confidence(-?\d+\.?\d*)", os.path.basename(g))
        if m:
            return float(m.group(1))
    return None


def main():
    drug_cat = load_drug_categories()
    folders = sorted(d for d in os.listdir(SWEEP) if os.path.isdir(f"{SWEEP}/{d}"))
    rows, failures = [], []

    for i, folder in enumerate(folders, 1):
        path = f"{SWEEP}/{folder}"
        drug, pdb = folder.rsplit("__", 1)
        rank1 = f"{path}/rank1.sdf"
        rec = f"{RECEPTORS}/{pdb}_receptor.pdb"
        if not os.path.exists(rank1):
            print(f"[{i}/{len(folders)}] MISSING rank1: {folder}")
            failures.append(folder)
            continue

        res = subprocess.run(
            [GNINA, "-r", rec, "-l", rank1, "--minimize"],
            capture_output=True, text=True,
        )
        sc = parse_scores(res.stdout)
        if sc["gnina_affinity"] is None:
            print(f"[{i}/{len(folders)}] PARSE FAIL: {folder} (see stderr below)")
            print("   " + res.stderr.strip().replace("\n", "\n   ")[:500])
            failures.append(folder)

        target, state = PDB_META.get(pdb, ("?", "?"))
        rows.append(dict(
            drug=drug, category=drug_cat.get(drug, "?"),
            pdb=pdb, target=target, state=state,
            diffdock_confidence=diffdock_confidence(path),
            **sc,
        ))
        print(f"[{i}/{len(folders)}] {folder}: aff={sc['gnina_affinity']} "
              f"cnn_aff={sc['gnina_cnn_affinity']} cnn_score={sc['gnina_cnn_score']}")

    fields = ["drug", "category", "pdb", "target", "state", "diffdock_confidence",
              "gnina_affinity", "gnina_minimize_rmsd", "gnina_cnn_score", "gnina_cnn_affinity"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {len(rows)} rescored pairs to {OUT}")
    if failures:
        print(f"{len(failures)} problem pair(s): {failures}")


if __name__ == "__main__":
    main()
