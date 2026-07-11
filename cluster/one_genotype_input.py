#!/usr/bin/env python3
"""
Build a DiffDock input CSV for ONE receptor x all drugs — so a new genotype can be docked without
re-running the whole 8-structure sweep. Run on gandalf (stdlib only).

Usage:
    python cluster/one_genotype_input.py <PDB_ID> [out_csv]
    e.g. python cluster/one_genotype_input.py EGFRC797S ~/hackathon/data/EGFRC797S_input.csv

Requires ~/hackathon/data/structures/prepared/<PDB_ID>_receptor.pdb and ~/hackathon/data/drugs.csv.
"""
import csv
import os
import sys

HOME = os.path.expanduser("~")
DRUGS = f"{HOME}/hackathon/data/drugs.csv"
RECEPTOR_DIR = f"{HOME}/hackathon/data/structures/prepared"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pdb = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else f"{HOME}/hackathon/data/{pdb}_input.csv"
    receptor = f"{RECEPTOR_DIR}/{pdb}_receptor.pdb"
    if not os.path.exists(receptor):
        sys.exit(f"no receptor at {receptor} — model it first (cluster/model_mutant.py)")
    with open(DRUGS) as f:
        drugs = list(csv.DictReader(f))
    rows = [dict(complex_name=f"{d['name']}__{pdb}", protein_path=receptor,
                 ligand_description=d["smiles_canonical_rdkit"], protein_sequence="") for d in drugs]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["complex_name", "protein_path", "ligand_description", "protein_sequence"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows for {pdb} -> {out}")


if __name__ == "__main__":
    main()
